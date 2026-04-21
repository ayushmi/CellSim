from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def load_jsonl(path: Path) -> pd.DataFrame:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


def load_yaml_table(path: Path, key: str) -> pd.DataFrame:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return pd.DataFrame(payload[key])


def _load_optional_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def load_explorer_bundle(root: Path, data_dir: Path) -> dict[str, pd.DataFrame]:
    events = load_jsonl(data_dir / "cod_events.jsonl")
    evidence = load_jsonl(data_dir / "evidence_trace.jsonl")
    benchmarks = load_jsonl(data_dir / "benchmark_rows.jsonl")
    action_ontology = load_yaml_table(root / "schemas" / "ontology" / "action_ontology.yaml", "actions")
    evidence_tiers = load_yaml_table(root / "schemas" / "ontology" / "evidence_tiers.yaml", "tiers")
    source_support = load_yaml_table(root / "configs" / "source_support_matrix.yaml", "sources")
    source_registry = load_jsonl(data_dir / "source_registry.jsonl") if (data_dir / "source_registry.jsonl").exists() else pd.DataFrame()
    build_manifest = _load_optional_json(data_dir / "build_manifest.json")
    summary_stats = _load_optional_json(data_dir / "summary_stats.json")
    action_space_report = _load_optional_json(data_dir / "action_space_report.json")
    output_space_report = _load_optional_json(data_dir / "output_space_report.json")
    outcome_space_report = _load_optional_json(data_dir / "outcome_space_report.json")
    trajectory_report = _load_optional_json(data_dir / "trajectory_report.json")
    plausibility_report = _load_optional_json(data_dir / "plausibility_report.json")
    data_quality_report = _load_optional_json(data_dir / "data_quality_report.json")
    benchmark_dir_name = data_dir.name
    if benchmark_dir_name == "materialized_real":
        benchmark_dir_name = "real_public"
    elif benchmark_dir_name == "materialized_real_large":
        benchmark_dir_name = "real_public_large"
    elif benchmark_dir_name.startswith("materialized_"):
        benchmark_dir_name = benchmark_dir_name.replace("materialized_", "", 1)
    benchmark_dir = root / "benchmarks" / benchmark_dir_name
    benchmark_report = _load_optional_json(benchmark_dir / "benchmark_report.json")
    benchmark_audit_report = _load_optional_json(benchmark_dir / "benchmark_audit_report.json")
    baseline_report = _load_optional_json(benchmark_dir / "baseline_report.json")
    evaluation_dir = benchmark_dir / "evaluation_latest"
    evaluation_report = _load_optional_json(evaluation_dir / "evaluation_report.json")
    source_contracts = load_jsonl(data_dir / "source_contracts_snapshot.jsonl") if (data_dir / "source_contracts_snapshot.jsonl").exists() else pd.DataFrame()

    if not source_registry.empty:
        dataset_to_family = dict(zip(source_registry["dataset"], source_registry["family"]))
        events["source_family"] = events.get("source_family", events["source_dataset"].map(dataset_to_family)).fillna("unknown")
    else:
        if "source_family" not in events.columns:
            events["source_family"] = "unknown"

    return {
        "events": events,
        "evidence": evidence,
        "benchmarks": benchmarks,
        "action_ontology": action_ontology,
        "evidence_tiers": evidence_tiers,
        "source_support": source_support,
        "build_manifest": build_manifest,
        "summary_stats": summary_stats,
        "action_space_report": action_space_report,
        "output_space_report": output_space_report,
        "outcome_space_report": outcome_space_report,
        "trajectory_report": trajectory_report,
        "plausibility_report": plausibility_report,
        "data_quality_report": data_quality_report,
        "benchmark_report": benchmark_report,
        "benchmark_audit_report": benchmark_audit_report,
        "baseline_report": baseline_report,
        "evaluation_report": evaluation_report,
        "source_contracts": source_contracts,
    }


def summarize_missingness(events: pd.DataFrame) -> pd.DataFrame:
    cols = [col for col in events.columns if col.startswith("has_")]
    rows: list[dict[str, Any]] = []
    for col in cols:
        rows.append(
            {
                "field": col,
                "present_count": int(events[col].fillna(False).sum()),
                "missing_count": int((~events[col].fillna(False)).sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("field")


def benchmark_task_counts(benchmarks: pd.DataFrame) -> pd.DataFrame:
    task_map = {
        "state_to_action": "task_state_to_action",
        "state_plus_intervention_to_output": "task_state_intervention_to_output",
        "state_plus_intervention_to_outcome": "task_state_intervention_to_outcome",
        "next_step_transition": "task_next_step_transition",
        "trajectory_step_prediction": "task_trajectory_step_prediction",
        "plausibility_classification": "task_plausibility_classification",
        "action_supported_vs_unsupported": "task_action_supported_vs_unsupported",
    }
    rows = []
    for task, column in task_map.items():
        rows.append({"task": task, "count": int(benchmarks[column].notna().sum()) if column in benchmarks.columns else 0})
    return pd.DataFrame(rows)


def filter_events(
    events: pd.DataFrame,
    source: list[str],
    cell_type: list[str],
    tissue: list[str],
    action: list[str],
    pairing_status: list[str],
    evidence_tiers: list[int],
    min_confidence: float,
    benchmark_only: bool,
    benchmark_ids: set[str],
) -> pd.DataFrame:
    filtered = events.copy()
    if source:
        filtered = filtered[filtered["source_dataset"].isin(source)]
    if cell_type:
        filtered = filtered[filtered["cell_type_label"].isin(cell_type)]
    if tissue:
        filtered = filtered[filtered["tissue_label"].isin(tissue)]
    if action:
        filtered = filtered[filtered["action_level_2"].isin(action)]
    if pairing_status:
        filtered = filtered[filtered["measurement_pairing_status"].isin(pairing_status)]
    if evidence_tiers:
        filtered = filtered[filtered["causal_evidence_tier"].isin(evidence_tiers)]
    filtered = filtered[filtered["action_confidence_score"] >= min_confidence]
    if benchmark_only:
        filtered = filtered[filtered["cod_event_id"].isin(benchmark_ids)]
    return filtered
