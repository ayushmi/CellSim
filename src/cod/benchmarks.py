from __future__ import annotations

import json
import math
import random
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .explorer import load_jsonl
from .baselines import write_baseline_report
from .reporting import write_release_notes


def load_benchmark_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _split_ids(ids: list[str], seed: int, train_fraction: float, val_fraction: float) -> dict[str, set[str]]:
    rng = random.Random(seed)
    ids = list(ids)
    rng.shuffle(ids)
    n = len(ids)
    train_end = int(n * train_fraction)
    val_end = train_end + int(n * val_fraction)
    return {
        "train": set(ids[:train_end]),
        "val": set(ids[train_end:val_end]),
        "test": set(ids[val_end:]),
    }


def _normalized_distribution(frame: pd.DataFrame, group_col: str, label_col: str) -> dict[str, dict[str, float]]:
    if group_col not in frame.columns or label_col not in frame.columns:
        return {}
    result: dict[str, dict[str, float]] = {}
    for group_value, group_frame in frame.groupby(group_col):
        counts = group_frame[label_col].dropna().value_counts(normalize=True).sort_index()
        result[str(group_value)] = {str(label): float(value) for label, value in counts.items()}
    return result


def _majority_accuracy(eval_frame: pd.DataFrame, prediction_col: str, label_col: str) -> float | None:
    if eval_frame.empty:
        return None
    return float((eval_frame[prediction_col] == eval_frame[label_col]).mean())


def _group_majority_predictions(train_frame: pd.DataFrame, eval_frame: pd.DataFrame, group_col: str, label_col: str, fallback: str) -> tuple[pd.Series, float | None]:
    if group_col not in train_frame.columns or group_col not in eval_frame.columns:
        predictions = pd.Series([fallback] * len(eval_frame), index=eval_frame.index)
        return predictions, _majority_accuracy(eval_frame.assign(_pred=predictions), "_pred", label_col)
    per_group: dict[str, str] = {}
    for group_value, group_frame in train_frame.groupby(group_col):
        mode = group_frame[label_col].mode()
        if not mode.empty:
            per_group[str(group_value)] = str(mode.iloc[0])
    predictions = eval_frame[group_col].astype(str).map(per_group).fillna(fallback)
    return predictions, _majority_accuracy(eval_frame.assign(_pred=predictions), "_pred", label_col)


def _predictiveness_score(frame: pd.DataFrame, feature_col: str, label_col: str) -> float | None:
    valid = frame[[feature_col, label_col]].dropna()
    if valid.empty or valid[feature_col].nunique() <= 1:
        return None
    total = len(valid)
    conditional_entropy = 0.0
    for _, group in valid.groupby(feature_col):
        weight = len(group) / total
        probs = group[label_col].value_counts(normalize=True)
        entropy = -sum(float(p) * math.log2(float(p)) for p in probs if p > 0)
        conditional_entropy += weight * entropy
    label_probs = valid[label_col].value_counts(normalize=True)
    base_entropy = -sum(float(p) * math.log2(float(p)) for p in label_probs if p > 0)
    if base_entropy == 0:
        return 1.0
    return float(max(0.0, 1.0 - (conditional_entropy / base_entropy)))


def _task_quality_flags(
    merged: pd.DataFrame,
    task_counts: dict[str, int],
    baselines: dict[str, float | None],
    leakage_scores: dict[str, float | None],
) -> dict[str, dict[str, Any]]:
    quality: dict[str, dict[str, Any]] = {}
    plausibility_classes = set(merged["task_plausibility_classification"].dropna().tolist()) if "task_plausibility_classification" in merged.columns else set()
    supported_classes = set(merged["task_action_supported_vs_unsupported"].dropna().tolist()) if "task_action_supported_vs_unsupported" in merged.columns else set()
    action_rows = task_counts["state_to_action"]
    source_majority = baselines.get("source_family_majority_action_accuracy")
    source_predictiveness = leakage_scores.get("source_family_predictiveness")
    quality["state_to_action"] = {
        "status": "meaningful"
        if action_rows >= 100 and (source_majority is None or source_majority < 0.85) and (source_predictiveness is None or source_predictiveness < 0.8)
        else "weak_or_source_dominated",
        "reasons": [
            reason
            for reason, active in [
                ("too_few_rows", action_rows < 100),
                ("source_family_shortcut_risk", source_majority is not None and source_majority >= 0.85),
                ("high_source_predictiveness", source_predictiveness is not None and source_predictiveness >= 0.8),
            ]
            if active
        ],
    }
    quality["state_plus_intervention_to_output"] = {
        "status": "meaningful" if task_counts["state_plus_intervention_to_output"] >= 50 else "low_coverage",
        "reasons": ["insufficient_output_rows"] if task_counts["state_plus_intervention_to_output"] < 50 else [],
    }
    proxy_only_outcomes = bool(
        task_counts["state_plus_intervention_to_outcome"] > 0
        and "proxy_outcome_flag" in merged.columns
        and merged.loc[merged["task_state_intervention_to_outcome"].notna(), "proxy_outcome_flag"].fillna(False).all()
    )
    quality["state_plus_intervention_to_outcome"] = {
        "status": "unavailable" if task_counts["state_plus_intervention_to_outcome"] == 0 else "proxy_only" if proxy_only_outcomes else "meaningful",
        "reasons": ["no_valid_outcome_labels"] if task_counts["state_plus_intervention_to_outcome"] == 0 else ["proxy_outcomes_only"] if proxy_only_outcomes else [],
    }
    quality["next_step_transition"] = {
        "status": "meaningful" if task_counts.get("next_step_transition", 0) >= 50 else "limited",
        "reasons": ["insufficient_transition_rows"] if task_counts.get("next_step_transition", 0) < 50 else [],
    }
    quality["trajectory_step_prediction"] = {
        "status": "meaningful" if task_counts.get("trajectory_step_prediction", 0) >= 50 else "limited",
        "reasons": ["insufficient_trajectory_rows"] if task_counts.get("trajectory_step_prediction", 0) < 50 else [],
    }
    quality["plausibility_classification"] = {
        "status": "meaningful" if task_counts.get("plausibility_classification", 0) >= 100 and len(plausibility_classes) > 1 else "limited",
        "reasons": [
            reason
            for reason, active in [
                ("insufficient_plausibility_rows", task_counts.get("plausibility_classification", 0) < 100),
                ("single_class_labels", len(plausibility_classes) <= 1),
            ]
            if active
        ],
    }
    quality["action_supported_vs_unsupported_classification"] = {
        "status": "meaningful" if task_counts.get("action_supported_vs_unsupported", 0) >= 100 and len(supported_classes) > 1 else "limited",
        "reasons": [
            reason
            for reason, active in [
                ("insufficient_support_rows", task_counts.get("action_supported_vs_unsupported", 0) < 100),
                ("single_class_labels", len(supported_classes) <= 1),
            ]
            if active
        ],
    }
    return quality


def _validate_benchmark_consistency(merged: pd.DataFrame, events: pd.DataFrame) -> None:
    if len(merged) != len(events):
        raise ValueError("Benchmark rows must match event count one-to-one")
    if "benchmark_outcome_eligible" in merged.columns and merged["benchmark_outcome_eligible"].sum() == 0:
        if merged["task_state_intervention_to_outcome"].notna().any():
            raise ValueError("Outcome benchmark rows exist despite zero valid outcome eligibility")
    if "benchmark_output_eligible" in merged.columns:
        invalid_output = merged.loc[~merged["benchmark_output_eligible"].fillna(False), "task_state_intervention_to_output"].notna().any()
        if invalid_output:
            raise ValueError("Output benchmark rows exist outside valid output eligibility")
    if "benchmark_action_eligible" in merged.columns:
        invalid_action = merged.loc[~merged["benchmark_action_eligible"].fillna(False), "task_state_to_action"].notna().any()
        if invalid_action:
            raise ValueError("Action benchmark rows exist outside valid action eligibility")
    if "benchmark_trajectory_eligible" in merged.columns:
        invalid_trajectory = merged.loc[~merged["benchmark_trajectory_eligible"].fillna(False), "task_trajectory_step_prediction"].notna().any()
        if invalid_trajectory:
            raise ValueError("Trajectory benchmark rows exist outside valid trajectory eligibility")


def prepare_benchmarks(input_dir: Path, output_dir: Path, config_path: Path) -> dict[str, Any]:
    cfg = load_benchmark_config(config_path)
    events = load_jsonl(input_dir / "cod_events.jsonl")
    benchmarks = load_jsonl(input_dir / "benchmark_rows.jsonl")

    event_columns = [
        "cod_event_id",
        "source_family",
        "source_dataset",
        "cell_type_label",
        "state_representation_type",
        "action_level_2",
        "action_confidence_score",
        "measurement_pairing_status",
        "overall_plausibility_score",
        "unsupported_action_flag",
        "proxy_outcome_flag",
        "trajectory_id",
        "trajectory_class",
        "causal_evidence_tier",
        "state_depth_category",
        "event_type",
        "intervention_target_entity",
        "intervention_present",
        "output_present_flag",
        "outcome_present_flag",
        "record_origin_type",
    ]
    available_event_columns = [column for column in event_columns if column in events.columns]
    merged = benchmarks.merge(events[available_event_columns], on="cod_event_id", how="left", suffixes=("", "_event"))
    _validate_benchmark_consistency(merged, events)

    output_dir.mkdir(parents=True, exist_ok=True)
    split_membership = _split_ids(
        ids=merged["cod_event_id"].tolist(),
        seed=cfg["random_seed"],
        train_fraction=cfg["splits"]["train_fraction"],
        val_fraction=cfg["splits"]["val_fraction"],
    )
    merged["split"] = merged["cod_event_id"].map(
        lambda event_id: "train" if event_id in split_membership["train"] else "val" if event_id in split_membership["val"] else "test"
    )
    eval_views = cfg.get("evaluation_views", {})
    merged["held_out_source_family_flag"] = merged["source_family"].astype(str).isin(eval_views.get("held_out_source_families", []))
    merged["held_out_cell_type_flag"] = merged["held_out_cell_type_bucket"].fillna(False) if "held_out_cell_type_bucket" in merged.columns else False
    merged["held_out_perturbation_flag"] = merged["held_out_intervention_bucket"].fillna(False) if "held_out_intervention_bucket" in merged.columns else False
    merged["held_out_state_depth_flag"] = merged["state_depth_category"].astype(str).isin(eval_views.get("held_out_state_depths", []))
    merged["measured_state_flag"] = merged["state_representation_type"].isin(["raw_measured", "normalized_measured"])
    merged["inferred_state_flag"] = merged["state_representation_type"] == "inferred"
    merged["high_evidence_flag"] = merged["causal_evidence_tier"] >= 3
    merged["held_out_evidence_tier_flag"] = merged["evidence_tier"].isin(
        merged.loc[merged["split"] == "test", "evidence_tier"].dropna().unique().tolist()
    ) if "evidence_tier" in merged.columns else False

    train_rows = merged[merged["split"] == "train"].copy()
    eval_rows = merged[merged["split"] == "test"].copy()
    if train_rows.empty:
        raise ValueError("Benchmark train split is empty")

    action_mode = train_rows["task_state_to_action"].dropna().mode()
    majority_action = str(action_mode.iloc[0]) if not action_mode.empty else None
    if majority_action is None:
        raise ValueError("state_to_action benchmark has no valid labels")

    eval_rows["majority_prediction"] = majority_action
    eval_rows["majority_correct"] = eval_rows["task_state_to_action"] == eval_rows["majority_prediction"]

    source_predictions, source_accuracy = _group_majority_predictions(
        train_rows, eval_rows, "source_family", "task_state_to_action", majority_action
    )
    eval_rows["source_family_majority_prediction"] = source_predictions
    eval_rows["source_family_majority_correct"] = eval_rows["task_state_to_action"] == eval_rows["source_family_majority_prediction"]

    state_depth_predictions, state_depth_accuracy = _group_majority_predictions(
        train_rows, eval_rows, "state_depth_category", "task_state_to_action", majority_action
    )
    eval_rows["state_depth_majority_prediction"] = state_depth_predictions
    eval_rows["state_depth_majority_correct"] = eval_rows["task_state_to_action"] == eval_rows["state_depth_majority_prediction"]

    evidence_predictions, evidence_accuracy = _group_majority_predictions(
        train_rows, eval_rows, "evidence_tier", "task_state_to_action", majority_action
    )
    eval_rows["evidence_tier_majority_prediction"] = evidence_predictions
    eval_rows["evidence_tier_majority_correct"] = eval_rows["task_state_to_action"] == eval_rows["evidence_tier_majority_prediction"]

    merged.to_json(output_dir / "benchmark_dataset.jsonl", orient="records", lines=True)
    eval_rows.to_json(output_dir / "benchmark_eval_rows.jsonl", orient="records", lines=True)
    write_baseline_report(output_dir / "benchmark_dataset.jsonl", output_dir / "baseline_report.json")

    task_counts = {
        "state_to_action": int(merged["task_state_to_action"].notna().sum()),
        "state_plus_intervention_to_output": int(merged["task_state_intervention_to_output"].notna().sum()),
        "state_plus_intervention_to_outcome": int(merged["task_state_intervention_to_outcome"].notna().sum()),
        "next_step_transition": int(merged["task_next_step_transition"].notna().sum()) if "task_next_step_transition" in merged.columns else 0,
        "trajectory_step_prediction": int(merged["task_trajectory_step_prediction"].notna().sum()) if "task_trajectory_step_prediction" in merged.columns else 0,
        "plausibility_classification": int(merged["task_plausibility_classification"].notna().sum()) if "task_plausibility_classification" in merged.columns else 0,
        "action_supported_vs_unsupported": int(merged["task_action_supported_vs_unsupported"].notna().sum()) if "task_action_supported_vs_unsupported" in merged.columns else 0,
    }
    requested_tasks = set(cfg.get("tasks", []))
    task_requirements = {
        "state_to_action": task_counts["state_to_action"] > 0,
        "state_plus_intervention_to_output": task_counts["state_plus_intervention_to_output"] > 0,
        "state_plus_intervention_to_outcome": task_counts["state_plus_intervention_to_outcome"] > 0,
        "next_step_transition": task_counts["next_step_transition"] > 0,
        "trajectory_step_prediction": task_counts["trajectory_step_prediction"] > 0,
        "plausibility_classification": task_counts["plausibility_classification"] > 0,
        "action_supported_vs_unsupported_classification": task_counts["action_supported_vs_unsupported"] > 0,
    }
    invalid_requested_tasks = sorted(
        task_name for task_name, is_available in task_requirements.items() if task_name in requested_tasks and not is_available
    )
    if invalid_requested_tasks:
        raise ValueError(f"Configured benchmark tasks lack valid labels: {invalid_requested_tasks}")
    baselines = {
        "majority_action_accuracy": _majority_accuracy(eval_rows, "majority_prediction", "task_state_to_action"),
        "source_family_majority_action_accuracy": source_accuracy,
        "state_depth_majority_action_accuracy": state_depth_accuracy,
        "evidence_tier_majority_action_accuracy": evidence_accuracy,
    }
    leakage_scores = {
        "source_family_predictiveness": _predictiveness_score(merged, "source_family", "task_state_to_action"),
        "state_depth_predictiveness": _predictiveness_score(merged, "state_depth_category", "task_state_to_action"),
        "event_type_predictiveness": _predictiveness_score(merged, "event_type", "task_state_to_action"),
        "evidence_tier_predictiveness": _predictiveness_score(merged, "evidence_tier", "task_state_to_action"),
    }
    quality_flags = _task_quality_flags(merged, task_counts, baselines, leakage_scores)

    audit_report = {
        "label_distribution_by_source_family": _normalized_distribution(merged, "source_family", "task_state_to_action"),
        "label_distribution_by_split": _normalized_distribution(merged, "split", "task_state_to_action"),
        "label_distribution_by_state_depth": _normalized_distribution(merged, "state_depth_category", "task_state_to_action"),
        "label_distribution_by_event_type": _normalized_distribution(merged, "event_type", "task_state_to_action"),
        "predictiveness": leakage_scores,
        "shortcut_baselines": baselines,
        "quality_flags": quality_flags,
    }
    (output_dir / "benchmark_audit_report.json").write_text(json.dumps(audit_report, indent=2, sort_keys=True), encoding="utf-8")

    report = {
        "counts": {
            "rows": int(len(merged)),
            "train": int((merged["split"] == "train").sum()),
            "val": int((merged["split"] == "val").sum()),
            "test": int((merged["split"] == "test").sum()),
        },
        "baselines": baselines,
        "task_counts": task_counts,
        "task_quality_flags": quality_flags,
        "analysis_views": {
            "source_family_distribution": merged["source_family"].value_counts().to_dict(),
            "state_representation_distribution": merged["state_representation_type"].value_counts().to_dict(),
            "state_depth_distribution": merged["state_depth_category"].value_counts().to_dict(),
            "event_type_distribution": merged["event_type"].value_counts().to_dict(),
            "high_evidence_rows": int(merged["high_evidence_flag"].sum()),
            "held_out_flags": {
                "source_family": int(merged["held_out_source_family_flag"].sum()),
                "cell_type": int(merged["held_out_cell_type_flag"].sum()),
                "perturbation": int(merged["held_out_perturbation_flag"].sum()),
                "state_depth": int(merged["held_out_state_depth_flag"].sum()),
                "evidence_tier": int(merged["held_out_evidence_tier_flag"].sum()),
            },
        },
    }
    (output_dir / "benchmark_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    write_release_notes(
        input_dir,
        input_dir / "release_notes.md",
        benchmark_report=report,
        benchmark_audit_report=audit_report,
    )
    return report
