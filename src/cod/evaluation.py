from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .explorer import load_jsonl


PREDICTION_ID_CANDIDATES = ["cod_event_id", "event_id", "state_id"]
ACTION_CANDIDATES = ["proposed_action", "action", "predicted_action"]
CONFIDENCE_CANDIDATES = ["confidence", "predicted_confidence", "action_confidence"]
OUTPUT_TYPE_CANDIDATES = ["proposed_output_type", "predicted_output_type", "output_type"]
CANDIDATE_ACTIONS_CANDIDATES = ["candidate_actions", "proposed_candidate_actions"]


def _choose_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lowered = {column.lower(): column for column in df.columns}
    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    return None


def _load_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return pd.read_json(path, lines=True)
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return pd.DataFrame(payload)
        return pd.DataFrame([payload])
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported predictions file type: {path}")


def load_prediction_frame(path: Path) -> pd.DataFrame:
    frame = _load_table(path)
    id_col = _choose_column(frame, PREDICTION_ID_CANDIDATES)
    action_col = _choose_column(frame, ACTION_CANDIDATES)
    if id_col is None or action_col is None:
        raise ValueError("Prediction file must contain an event id column and proposed action column")
    rename_map = {id_col: "cod_event_id", action_col: "proposed_action"}
    confidence_col = _choose_column(frame, CONFIDENCE_CANDIDATES)
    if confidence_col:
        rename_map[confidence_col] = "confidence"
    output_type_col = _choose_column(frame, OUTPUT_TYPE_CANDIDATES)
    if output_type_col:
        rename_map[output_type_col] = "proposed_output_type"
    candidate_action_col = _choose_column(frame, CANDIDATE_ACTIONS_CANDIDATES)
    if candidate_action_col:
        rename_map[candidate_action_col] = "candidate_actions"
    frame = frame.rename(columns=rename_map)
    frame["cod_event_id"] = frame["cod_event_id"].astype(str)
    if "confidence" not in frame.columns:
        frame["confidence"] = 0.5
    if "candidate_actions" in frame.columns:
        frame["candidate_actions"] = frame["candidate_actions"].apply(
            lambda value: value if isinstance(value, list) else [item for item in str(value).split("|") if item] if pd.notna(value) else []
        )
    else:
        frame["candidate_actions"] = frame["proposed_action"].apply(lambda value: [value] if pd.notna(value) else [])
    return frame


def _normalized_distribution(frame: pd.DataFrame, group_col: str, value_col: str) -> dict[str, dict[str, float]]:
    if group_col not in frame.columns or value_col not in frame.columns:
        return {}
    result: dict[str, dict[str, float]] = {}
    for group_value, group_frame in frame.groupby(group_col):
        counts = group_frame[value_col].value_counts(normalize=True, dropna=False)
        result[str(group_value)] = {str(key): float(value) for key, value in counts.items()}
    return result


def _confidence_calibration(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    work = frame.copy()
    work["confidence_bin"] = work["confidence"].clip(0, 0.999).apply(lambda value: round(float(value), 1))
    rows = []
    for confidence_bin, bin_frame in work.groupby("confidence_bin"):
        rows.append(
            {
                "confidence_bin": float(confidence_bin),
                "count": int(len(bin_frame)),
                "action_agreement": float(bin_frame["action_agreement"].mean()) if len(bin_frame) else 0.0,
                "candidate_agreement": float(bin_frame["candidate_agreement"].mean()) if len(bin_frame) else 0.0,
            }
        )
    return rows


def evaluate_predictions(input_dir: Path, predictions_path: Path, output_dir: Path) -> dict[str, Any]:
    events = load_jsonl(input_dir / "cod_events.jsonl")
    benchmarks = load_jsonl(input_dir / "benchmark_rows.jsonl")
    predictions = load_prediction_frame(predictions_path)
    merged = predictions.merge(events, on="cod_event_id", how="left", suffixes=("", "_event"))
    merged = merged.merge(benchmarks, on="cod_event_id", how="left", suffixes=("", "_benchmark"))

    missing_events = int(merged["source_dataset"].isna().sum())
    if missing_events:
        raise ValueError(f"Predictions contain {missing_events} unknown cod_event_id values")

    merged["candidate_agreement"] = merged.apply(
        lambda row: str(row["proposed_action"]) in (row["action_candidate_labels"] or []),
        axis=1,
    )
    merged["action_agreement"] = merged["proposed_action"].astype(str) == merged["action_primary_label"].astype(str)
    merged["output_agreement"] = (
        merged["proposed_output_type"].astype(str) == merged["output_type"].astype(str)
        if "proposed_output_type" in merged.columns
        else False
    )
    merged["plausibility_penalty"] = (
        merged["unsupported_action_flag"].fillna(False)
        | ((~merged["candidate_agreement"]) & (merged["overall_plausibility_score"].fillna(0.0) < 0.3))
    )
    merged["failure_taxonomy"] = merged.apply(_classify_failure, axis=1)

    output_dir.mkdir(parents=True, exist_ok=True)
    merged.to_json(output_dir / "evaluation_rows.jsonl", orient="records", lines=True)
    merged.to_csv(output_dir / "evaluation_rows.csv", index=False)

    report = {
        "prediction_contract": {
            "required_fields": ["cod_event_id", "proposed_action"],
            "optional_fields": ["candidate_actions", "confidence", "proposed_output_type"],
        },
        "counts": {
            "predictions": int(len(merged)),
            "action_agreement_rows": int(merged["action_agreement"].notna().sum()),
            "output_agreement_rows": int(merged["output_present_flag"].fillna(False).sum()),
            "outcome_rows": int(merged["outcome_present_flag"].fillna(False).sum()),
        },
        "metrics": {
            "action_exact_match": float(merged["action_agreement"].mean()) if len(merged) else 0.0,
            "action_candidate_match": float(merged["candidate_agreement"].mean()) if len(merged) else 0.0,
            "output_type_match": float(merged.loc[merged["output_present_flag"].fillna(False), "output_agreement"].mean()) if len(merged.loc[merged["output_present_flag"].fillna(False)]) else 0.0,
            "mean_plausibility_score": float(merged["overall_plausibility_score"].fillna(0.0).mean()) if len(merged) else 0.0,
            "unsupported_action_rate": float(merged["plausibility_penalty"].mean()) if len(merged) else 0.0,
            "abstention_rate": float((merged["proposed_action"] == "no_confident_action_assignment").mean()) if len(merged) else 0.0,
        },
        "stratified_action_agreement": {
            "by_source_family": merged.groupby("source_family")["action_agreement"].mean().round(4).to_dict(),
            "by_event_type": merged.groupby("event_type")["action_agreement"].mean().round(4).to_dict(),
            "by_state_depth": merged.groupby("state_depth_category")["action_agreement"].mean().round(4).to_dict(),
            "by_evidence_tier": merged.groupby("causal_evidence_tier")["action_agreement"].mean().round(4).to_dict(),
            "by_linkage_type": merged.groupby("measurement_pairing_status")["action_agreement"].mean().round(4).to_dict(),
        },
        "held_out_robustness": {
            "cell_type": float(merged.loc[merged["held_out_cell_type_bucket"].fillna(False), "action_agreement"].mean()) if len(merged.loc[merged["held_out_cell_type_bucket"].fillna(False)]) else None,
            "perturbation": float(merged.loc[merged["held_out_intervention_bucket"].fillna(False), "action_agreement"].mean()) if len(merged.loc[merged["held_out_intervention_bucket"].fillna(False)]) else None,
            "source_family": float(merged.loc[merged["source_family"] == "signaling_graph", "action_agreement"].mean()) if len(merged.loc[merged["source_family"] == "signaling_graph"]) else None,
            "state_depth": float(merged.loc[merged["state_depth_category"] == "transition_bearing", "action_agreement"].mean()) if len(merged.loc[merged["state_depth_category"] == "transition_bearing"]) else None,
        },
        "confidence_calibration": _confidence_calibration(merged),
        "failure_taxonomy_distribution": merged["failure_taxonomy"].value_counts().to_dict(),
        "label_distribution_by_source_family": _normalized_distribution(merged, "source_family", "proposed_action"),
    }
    (output_dir / "evaluation_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def _classify_failure(row: pd.Series) -> str:
    if bool(row.get("ood_flag")) or str(row.get("support_domain_tag", "")) == "out_of_domain":
        return "off_distribution_state"
    if bool(row.get("plausibility_penalty")):
        return "unsupported_action"
    if pd.notna(row.get("proposed_output_type")) and bool(row.get("output_present_flag")) and not bool(row.get("output_agreement")):
        return "output_mismatch"
    if int(row.get("causal_evidence_tier", 0)) <= 1 and not bool(row.get("action_agreement")):
        return "low_evidence_action"
    if float(row.get("confidence", 0.0)) < 0.5 and not bool(row.get("action_agreement")):
        return "low_confidence_disagreement"
    if str(row.get("proposed_action")) == str(row.get("source_family_majority_prediction", "")):
        return "source_specific_shortcut"
    return "agreement_or_unclassified"
