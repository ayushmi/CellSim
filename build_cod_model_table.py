#!/usr/bin/env python3
"""
Build model-ready tables from a materialized COD directory.

This version follows the actual COD 2.0 artifact layout and canonical field ids:

- events: `cod_events.parquet` / `cod_events.jsonl`
- transcriptome features: `transcriptome_profiles.jsonl`
- signaling features: `signaling_profiles.jsonl`
- evidence traces: `evidence_trace.parquet` / `evidence_trace.jsonl`
- benchmark labels and eligibility: `benchmark_rows.jsonl`

It joins feature tables through COD profile references, not by pretending the
feature rows are keyed directly by event id.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd


CANONICAL_FILES = {
    "events": ["cod_events.parquet", "cod_events.jsonl"],
    "benchmarks": ["benchmark_rows.jsonl"],
    "transcriptome": ["transcriptome_profiles.jsonl", "transcriptome_profiles.parquet"],
    "signaling": ["signaling_profiles.jsonl", "signaling_profiles.parquet"],
    "evidence": ["evidence_trace.parquet", "evidence_trace.jsonl"],
}

FEATURE_NAME_CANDIDATES = ["feature_name", "feature_id"]
FEATURE_VALUE_CANDIDATES = ["value", "score"]
OUTPUT_NAMES = {
    "full": "cod_model_full",
    "strict": "cod_model_training_strict",
}


def resolve_existing_file(root: Path, names: Sequence[str]) -> Optional[Path]:
    for name in names:
        candidate = root / name
        if candidate.exists():
            return candidate
    return None


def read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".jsonl":
        return pd.read_json(path, lines=True)
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return pd.DataFrame(payload)
        if isinstance(payload, dict):
            for value in payload.values():
                if isinstance(value, list):
                    return pd.DataFrame(value)
            return pd.DataFrame([payload])
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".tsv":
        return pd.read_csv(path, sep="\t")
    raise ValueError(f"Unsupported file type: {path}")


def stringify_if_listlike(value):
    if isinstance(value, (list, tuple, set)):
        return "|".join(map(str, value))
    return value


def choose_col(df: pd.DataFrame, candidates: Sequence[str]) -> Optional[str]:
    lowered = {column.lower(): column for column in df.columns}
    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    return None


def normalize_cod_event_id(df: pd.DataFrame) -> pd.DataFrame:
    candidates = ["cod_event_id", "event_id", "cte_id", "id", "record_id"]
    source_col = choose_col(df, candidates)
    if source_col is None:
        raise KeyError(f"Could not find COD event id column in columns: {list(df.columns)[:40]}")
    if source_col != "cod_event_id":
        df = df.rename(columns={source_col: "cod_event_id"})
    df["cod_event_id"] = df["cod_event_id"].astype(str)
    return df


def normalize_profile_ref(df: pd.DataFrame) -> pd.DataFrame:
    candidates = ["profile_ref", "state_ref", "feature_profile_ref"]
    source_col = choose_col(df, candidates)
    if source_col is None:
        raise KeyError(f"Could not find profile ref column in columns: {list(df.columns)[:40]}")
    if source_col != "profile_ref":
        df = df.rename(columns={source_col: "profile_ref"})
    df["profile_ref"] = df["profile_ref"].astype(str)
    return df


def pivot_profile_features(df: pd.DataFrame, prefix: str, max_features: int) -> pd.DataFrame:
    df = normalize_profile_ref(df)
    feature_col = choose_col(df, FEATURE_NAME_CANDIDATES)
    value_col = choose_col(df, FEATURE_VALUE_CANDIDATES)
    if feature_col is None or value_col is None:
        raise KeyError(f"Could not identify feature/value columns in {list(df.columns)[:40]}")

    work = df[["profile_ref", feature_col, value_col]].copy()
    work[feature_col] = work[feature_col].astype(str)
    work[value_col] = pd.to_numeric(work[value_col], errors="coerce")
    work = work.dropna(subset=[value_col])

    if max_features > 0:
        top_features = work[feature_col].value_counts().head(max_features).index
        work = work[work[feature_col].isin(top_features)]

    pivoted = work.pivot_table(index="profile_ref", columns=feature_col, values=value_col, aggfunc="mean")
    pivoted.columns = [f"{prefix}{column}" for column in pivoted.columns]
    return pivoted.reset_index()


def add_list_stringification(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in out.columns:
        out[column] = out[column].map(stringify_if_listlike)
    return out


def build_full_table(
    materialized_dir: Path,
    max_transcriptome_features: int,
    max_signal_features: int,
) -> Tuple[pd.DataFrame, Dict[str, Optional[str]]]:
    files = {name: resolve_existing_file(materialized_dir, candidates) for name, candidates in CANONICAL_FILES.items()}
    if files["events"] is None:
        raise FileNotFoundError(f"Could not find canonical COD event table in {materialized_dir}")

    events = normalize_cod_event_id(read_table(files["events"]))
    events = add_list_stringification(events)
    full = events.copy()

    if files["benchmarks"] is not None:
        benchmarks = normalize_cod_event_id(read_table(files["benchmarks"]))
        full = full.merge(benchmarks, on="cod_event_id", how="left", suffixes=("", "__benchmark"))

    if files["transcriptome"] is not None and "transcriptome_profile_ref" in full.columns:
        transcriptome = pivot_profile_features(read_table(files["transcriptome"]), "tx__", max_transcriptome_features)
        full = full.merge(
            transcriptome,
            left_on="transcriptome_profile_ref",
            right_on="profile_ref",
            how="left",
        ).drop(columns=["profile_ref"], errors="ignore")

    if files["signaling"] is not None:
        signaling = pivot_profile_features(read_table(files["signaling"]), "sig__", max_signal_features)
        signal_ref_col = choose_col(full, ["external_signal_set_ref", "signaling_profile_ref"])
        if signal_ref_col is not None:
            full = full.merge(
                signaling,
                left_on=signal_ref_col,
                right_on="profile_ref",
                how="left",
            ).drop(columns=["profile_ref"], errors="ignore")

    if files["evidence"] is not None:
        evidence = normalize_cod_event_id(read_table(files["evidence"]))
        evidence_count = evidence.groupby("cod_event_id").size().rename("evidence_trace_count").reset_index()
        full = full.merge(evidence_count, on="cod_event_id", how="left")
        full["evidence_trace_count"] = full["evidence_trace_count"].fillna(0).astype(int)
    else:
        full["evidence_trace_count"] = 0

    if "target_action" not in full.columns and "action_primary_label" in full.columns:
        full["target_action"] = full["action_primary_label"]
    if "output_target_ref" not in full.columns and "task_state_intervention_to_output" in full.columns:
        full["output_target_ref"] = full["task_state_intervention_to_output"]

    if "benchmark_action_eligible" not in full.columns:
        full["benchmark_action_eligible"] = full["action_primary_label"].notna() if "action_primary_label" in full.columns else False
    if "benchmark_output_eligible" not in full.columns:
        full["benchmark_output_eligible"] = full["output_present_flag"].fillna(False) if "output_present_flag" in full.columns else False
    if "benchmark_outcome_eligible" not in full.columns:
        full["benchmark_outcome_eligible"] = full["outcome_present_flag"].fillna(False) if "outcome_present_flag" in full.columns else False

    full["eligible_state_to_action"] = full["benchmark_action_eligible"].fillna(False).astype(bool)
    full["eligible_state_intervention_to_output"] = full["benchmark_output_eligible"].fillna(False).astype(bool)
    full["eligible_strict_action_training"] = (
        full["eligible_state_to_action"]
        & full["eligible_state_intervention_to_output"]
        & full.get("event_type", pd.Series("", index=full.index)).astype(str).eq("transition_event")
        & full.get("state_depth_category", pd.Series("", index=full.index)).astype(str).eq("transition_bearing")
    )
    if "measurement_pairing_status" in full.columns:
        full["eligible_strict_action_training"] &= full["measurement_pairing_status"].astype(str).isin(["exact_cell", "exact_sample"])

    return full, {name: str(path) if path is not None else None for name, path in files.items()}


def build_strict_table(full: pd.DataFrame, min_evidence_tiers: Sequence[str]) -> pd.DataFrame:
    mask = full["eligible_strict_action_training"].fillna(False).astype(bool)
    if min_evidence_tiers:
        evidence_col = choose_col(full, ["causal_evidence_tier", "evidence_tier"])
        if evidence_col is not None:
            mask &= full[evidence_col].astype(str).isin(list(min_evidence_tiers))
    strict = full[mask].copy()
    drop_cols = [
        column
        for column in ["eligible_state_to_action", "eligible_state_intervention_to_output", "eligible_strict_action_training"]
        if column in strict.columns
    ]
    if drop_cols:
        strict = strict.drop(columns=drop_cols)
    return strict


def write_table(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        df.to_parquet(path, index=False)
        return
    if suffix == ".csv":
        df.to_csv(path, index=False)
        return
    if suffix == ".jsonl":
        df.to_json(path, orient="records", lines=True)
        return
    raise ValueError(f"Unsupported output format for {path}. Use .parquet, .csv, or .jsonl")


def resolve_output_paths(
    output_dir: Optional[Path],
    full_output: Optional[str],
    strict_output: Optional[str],
    output_format: str,
) -> tuple[Path, Path]:
    if output_dir is not None:
        suffix = f".{output_format.lstrip('.')}"
        return output_dir / f"{OUTPUT_NAMES['full']}{suffix}", output_dir / f"{OUTPUT_NAMES['strict']}{suffix}"
    if not full_output or not strict_output:
        raise ValueError("Provide either --output-dir or both --full-output and --strict-output")
    return Path(full_output), Path(strict_output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build model-ready tables from a materialized COD directory")
    parser.add_argument("--materialized-dir", required=True, help="Path to materialized COD directory")
    parser.add_argument("--output-dir", help="Directory for canonical output names")
    parser.add_argument("--output-format", default="parquet", choices=["parquet", "csv", "jsonl"], help="Format used with --output-dir")
    parser.add_argument("--full-output", help="Explicit path for full unified table (.parquet/.csv/.jsonl)")
    parser.add_argument("--strict-output", help="Explicit path for strict training slice (.parquet/.csv/.jsonl)")
    parser.add_argument("--max-transcriptome-features", type=int, default=512, help="Maximum transcriptome features to pivot wide")
    parser.add_argument("--max-signal-features", type=int, default=128, help="Maximum signaling features to pivot wide")
    parser.add_argument("--min-evidence-tier", nargs="*", default=[], help="Optional evidence tiers to keep in strict table, e.g. 1 3")
    args = parser.parse_args()

    materialized_dir = Path(args.materialized_dir)
    output_dir = Path(args.output_dir) if args.output_dir else None
    full_output, strict_output = resolve_output_paths(output_dir, args.full_output, args.strict_output, args.output_format)

    full, files_used = build_full_table(materialized_dir, args.max_transcriptome_features, args.max_signal_features)
    strict = build_strict_table(full, args.min_evidence_tier)

    write_table(full, full_output)
    write_table(strict, strict_output)

    summary = {
        "materialized_dir": str(materialized_dir),
        "files_used": files_used,
        "full_output": str(full_output),
        "strict_output": str(strict_output),
        "full_rows": int(len(full)),
        "strict_rows": int(len(strict)),
        "full_cols": int(len(full.columns)),
        "strict_cols": int(len(strict.columns)),
        "strict_action_distribution": strict["action_primary_label"].value_counts().to_dict() if "action_primary_label" in strict.columns else {},
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
