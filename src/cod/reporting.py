from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .explorer import load_jsonl


def _optional_jsonl(path: Path):
    return load_jsonl(path) if path.exists() else load_jsonl((path.parent / "cod_events.jsonl").resolve()).iloc[0:0]


def summarize_build(input_dir: Path) -> dict[str, Any]:
    events = load_jsonl(input_dir / "cod_events.jsonl")
    evidence = _optional_jsonl(input_dir / "evidence_trace.jsonl")
    benchmarks = _optional_jsonl(input_dir / "benchmark_rows.jsonl")
    transcriptome = _optional_jsonl(input_dir / "transcriptome_profiles.jsonl")
    metabolome = _optional_jsonl(input_dir / "metabolome_profiles.jsonl")
    signaling = _optional_jsonl(input_dir / "signaling_profiles.jsonl")
    source_family_distribution = events["source_family"].fillna("unknown").value_counts().to_dict() if "source_family" in events.columns else {}
    output_events = events[events["output_present_flag"].fillna(False)].copy() if "output_present_flag" in events.columns else events.iloc[0:0]
    outcome_events = events[events["outcome_present_flag"].fillna(False)].copy() if "outcome_present_flag" in events.columns else events.iloc[0:0]
    trajectory_events = events[events.get("trajectory_id", "").notna()].copy() if "trajectory_id" in events.columns else events.iloc[0:0]
    summary = {
        "events": int(len(events)),
        "sources": events["source_dataset"].value_counts().to_dict(),
        "source_family_distribution": source_family_distribution,
        "source_family_coverage": int(len(source_family_distribution)) if source_family_distribution else int(events["source_dataset"].nunique()),
        "action_label_coverage": int(events["action_level_2"].notna().sum()),
        "action_distribution": events["action_level_2"].value_counts().to_dict(),
        "evidence_tier_distribution": events["causal_evidence_tier"].value_counts().sort_index().to_dict(),
        "benchmark_rows": int(len(benchmarks)),
        "benchmark_action_rows": int(benchmarks["task_state_to_action"].notna().sum()) if "task_state_to_action" in benchmarks.columns else 0,
        "benchmark_output_rows": int(benchmarks["task_state_intervention_to_output"].notna().sum()) if "task_state_intervention_to_output" in benchmarks.columns else 0,
        "benchmark_outcome_rows": int(benchmarks["task_state_intervention_to_outcome"].notna().sum()) if "task_state_intervention_to_outcome" in benchmarks.columns else 0,
        "pairing_status_distribution": events["measurement_pairing_status"].value_counts().to_dict(),
        "state_representation_distribution": events["state_representation_type"].value_counts().to_dict(),
        "record_origin_distribution": events["record_origin_type"].value_counts().to_dict() if "record_origin_type" in events.columns else {},
        "state_depth_distribution": events["state_depth_category"].value_counts().to_dict() if "state_depth_category" in events.columns else {},
        "event_type_distribution": events["event_type"].value_counts().to_dict() if "event_type" in events.columns else {},
        "fraction_with_expression_features": float(events["has_expression_features"].mean()) if "has_expression_features" in events.columns and len(events) else 0.0,
        "fraction_with_perturbation_evidence": float(events["intervention_present"].mean()) if "intervention_present" in events.columns and len(events) else 0.0,
        "fraction_with_outcomes": float(events["outcome_present_flag"].mean()) if "outcome_present_flag" in events.columns and len(events) else 0.0,
        "fraction_with_outputs": float(events["output_present_flag"].mean()) if "output_present_flag" in events.columns and len(events) else 0.0,
        "output_type_distribution": output_events["output_type"].value_counts().to_dict() if "output_type" in output_events.columns else {},
        "outcome_type_distribution": outcome_events["outcome_proxy_type"].fillna("observed_or_unspecified").value_counts().to_dict() if "outcome_proxy_type" in outcome_events.columns else {},
        "trajectory_class_distribution": trajectory_events["trajectory_class"].value_counts().to_dict() if "trajectory_class" in trajectory_events.columns else {},
        "trajectory_event_count": int(len(trajectory_events)),
        "proxy_outcome_fraction": float(events["proxy_outcome_flag"].mean()) if "proxy_outcome_flag" in events.columns and len(events) else 0.0,
        "evidence_trace_rows": int(len(evidence)),
        "transcriptome_feature_rows": int(len(transcriptome)),
        "metabolome_feature_rows": int(len(metabolome)),
        "signaling_feature_rows": int(len(signaling)),
    }
    return summary


def validate_build_consistency(input_dir: Path, summary: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = summary or summarize_build(input_dir)
    events = load_jsonl(input_dir / "cod_events.jsonl")
    evidence = _optional_jsonl(input_dir / "evidence_trace.jsonl")
    benchmarks = _optional_jsonl(input_dir / "benchmark_rows.jsonl")
    transcriptome = _optional_jsonl(input_dir / "transcriptome_profiles.jsonl")
    metabolome = _optional_jsonl(input_dir / "metabolome_profiles.jsonl")
    signaling = _optional_jsonl(input_dir / "signaling_profiles.jsonl")

    expected_source_family_coverage = int(events["source_family"].fillna("unknown").nunique()) if "source_family" in events.columns else int(events["source_dataset"].nunique())
    checks = {
        "event_count_matches_summary": summary["events"] == int(len(events)),
        "evidence_count_matches_summary": summary["evidence_trace_rows"] == int(len(evidence)),
        "benchmark_count_matches_summary": summary["benchmark_rows"] == int(len(benchmarks)),
        "transcriptome_count_matches_summary": summary["transcriptome_feature_rows"] == int(len(transcriptome)),
        "metabolome_count_matches_summary": summary["metabolome_feature_rows"] == int(len(metabolome)),
        "signaling_count_matches_summary": summary["signaling_feature_rows"] == int(len(signaling)),
        "source_family_coverage_matches_summary": summary["source_family_coverage"] == expected_source_family_coverage,
        "per_source_counts_sum_to_events": sum(summary["sources"].values()) == summary["events"],
        "per_source_family_counts_sum_to_events": sum(summary["source_family_distribution"].values()) == summary["events"],
        "outcome_fraction_matches_rows": summary["benchmark_outcome_rows"] == int(benchmarks["task_state_intervention_to_outcome"].notna().sum()) if "task_state_intervention_to_outcome" in benchmarks.columns else True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"Build consistency validation failed: {failed}")
    return {"checks": checks}


def write_build_summary(input_dir: Path, output_path: Path) -> dict[str, Any]:
    summary = summarize_build(input_dir)
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def write_data_quality_report(input_dir: Path, output_path: Path) -> dict[str, Any]:
    events = load_jsonl(input_dir / "cod_events.jsonl")
    report = {
        "state_depth_distribution": events["state_depth_category"].value_counts().to_dict(),
        "event_type_distribution": events["event_type"].value_counts().to_dict(),
        "state_representation_distribution": events["state_representation_type"].value_counts().to_dict(),
        "pairing_status_distribution": events["measurement_pairing_status"].value_counts().to_dict(),
        "action_confidence_distribution": events["action_confidence_score"].round(1).value_counts().sort_index().to_dict(),
        "expression_feature_count_distribution": events["expression_feature_count"].value_counts().sort_index().to_dict(),
        "output_confidence_distribution": events["output_confidence_score"].round(1).value_counts().sort_index().to_dict() if "output_confidence_score" in events.columns else {},
        "outcome_confidence_distribution": events["outcome_confidence_score"].round(1).value_counts().sort_index().to_dict() if "outcome_confidence_score" in events.columns else {},
        "overall_plausibility_distribution": events["overall_plausibility_score"].dropna().round(1).value_counts().sort_index().to_dict() if "overall_plausibility_score" in events.columns else {},
        "missingness": {
            "outcome_present_fraction": float(events["outcome_present_flag"].mean()) if "outcome_present_flag" in events.columns else 0.0,
            "output_present_fraction": float(events["output_present_flag"].mean()) if "output_present_flag" in events.columns else 0.0,
            "expression_present_fraction": float(events["has_expression_features"].mean()) if "has_expression_features" in events.columns else 0.0,
        },
    }
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def write_action_space_report(input_dir: Path, output_path: Path) -> dict[str, Any]:
    events = load_jsonl(input_dir / "cod_events.jsonl")
    per_source_action = (
        events.groupby(["source_dataset", "action_level_2"]).size().reset_index(name="count").to_dict(orient="records")
        if len(events)
        else []
    )
    report = {
        "action_distribution": events["action_level_2"].value_counts().to_dict(),
        "action_confidence_distribution": events["action_confidence_score"].round(1).value_counts().sort_index().to_dict(),
        "action_assignment_method_distribution": events["action_assignment_method"].value_counts().to_dict(),
        "candidate_action_set_size_distribution": events["action_candidate_labels"].apply(len).value_counts().sort_index().to_dict(),
        "per_source_action_counts": per_source_action,
        "per_state_depth_action_counts": events.groupby(["state_depth_category", "action_level_2"]).size().reset_index(name="count").to_dict(orient="records"),
        "per_event_type_action_counts": events.groupby(["event_type", "action_level_2"]).size().reset_index(name="count").to_dict(orient="records"),
        "low_confidence_fraction": float((events["action_confidence_score"] < 0.7).mean()) if len(events) else 0.0,
    }
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def write_output_space_report(input_dir: Path, output_path: Path) -> dict[str, Any]:
    events = load_jsonl(input_dir / "cod_events.jsonl")
    output_events = events[events["output_present_flag"].fillna(False)].copy() if "output_present_flag" in events.columns else events.iloc[0:0]
    if "output_evidence_summary" in output_events.columns:
        example_rows = output_events[["cod_event_id", "output_type", "output_evidence_summary"]].copy()
        example_rows = example_rows.astype({"output_evidence_summary": "object"})
        example_rows["output_evidence_summary"] = example_rows["output_evidence_summary"].where(
            example_rows["output_evidence_summary"].notna(),
            None,
        )
        output_examples = example_rows.head(25).to_dict(orient="records")
    else:
        output_examples = []
    report = {
        "output_event_count": int(len(output_events)),
        "output_type_distribution": output_events["output_type"].value_counts().to_dict() if "output_type" in output_events.columns else {},
        "output_confidence_distribution": output_events["output_confidence_score"].round(1).value_counts().sort_index().to_dict() if "output_confidence_score" in output_events.columns else {},
        "per_source_output_counts": output_events.groupby(["source_dataset", "output_type"]).size().reset_index(name="count").to_dict(orient="records") if len(output_events) else [],
        "per_state_depth_output_counts": output_events.groupby(["state_depth_category", "output_type"]).size().reset_index(name="count").to_dict(orient="records") if len(output_events) else [],
        "output_evidence_summary_examples": output_examples,
    }
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def write_outcome_space_report(input_dir: Path, output_path: Path) -> dict[str, Any]:
    events = load_jsonl(input_dir / "cod_events.jsonl")
    outcome_events = events[events["outcome_present_flag"].fillna(False)].copy() if "outcome_present_flag" in events.columns else events.iloc[0:0]
    report = {
        "outcome_event_count": int(len(outcome_events)),
        "proxy_outcome_fraction": float(outcome_events["proxy_outcome_flag"].mean()) if len(outcome_events) and "proxy_outcome_flag" in outcome_events.columns else 0.0,
        "outcome_horizon_distribution": outcome_events["outcome_horizon_type"].value_counts().to_dict() if "outcome_horizon_type" in outcome_events.columns else {},
        "outcome_type_distribution": outcome_events["outcome_proxy_type"].fillna("observed_or_unspecified").value_counts().to_dict() if "outcome_proxy_type" in outcome_events.columns else {},
        "per_source_outcome_counts": outcome_events.groupby(["source_dataset", "outcome_horizon_type"]).size().reset_index(name="count").to_dict(orient="records") if len(outcome_events) else [],
        "per_state_depth_outcome_counts": outcome_events.groupby(["state_depth_category", "outcome_horizon_type"]).size().reset_index(name="count").to_dict(orient="records") if len(outcome_events) else [],
    }
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def write_trajectory_report(input_dir: Path, output_path: Path) -> dict[str, Any]:
    events = load_jsonl(input_dir / "cod_events.jsonl")
    trajectory_events = events[events["trajectory_id"].notna()].copy() if "trajectory_id" in events.columns else events.iloc[0:0]
    report = {
        "trajectory_event_count": int(len(trajectory_events)),
        "trajectory_count": int(trajectory_events["trajectory_id"].nunique()) if len(trajectory_events) else 0,
        "trajectory_class_distribution": trajectory_events["trajectory_class"].value_counts().to_dict() if "trajectory_class" in trajectory_events.columns else {},
        "exact_vs_inferred_distribution": trajectory_events["exact_vs_inferred_trajectory_flag"].fillna(False).astype(str).value_counts().to_dict() if "exact_vs_inferred_trajectory_flag" in trajectory_events.columns else {},
        "source_trajectory_counts": trajectory_events.groupby(["source_dataset", "trajectory_class"]).size().reset_index(name="count").to_dict(orient="records") if len(trajectory_events) else [],
        "trajectory_examples": trajectory_events[["cod_event_id", "trajectory_id", "trajectory_position", "trajectory_length", "previous_event_ref", "next_event_ref"]].head(25).to_dict(orient="records") if len(trajectory_events) else [],
    }
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def write_plausibility_report(input_dir: Path, output_path: Path) -> dict[str, Any]:
    events = load_jsonl(input_dir / "cod_events.jsonl")
    score_cols = [
        "regulatory_support_score",
        "pathway_support_score",
        "metabolic_support_score",
        "viability_constraint_score",
        "overall_plausibility_score",
    ]
    report = {
        "unsupported_action_fraction": float(events["unsupported_action_flag"].mean()) if "unsupported_action_flag" in events.columns and len(events) else 0.0,
        "evaluation_ready_fraction": float(events["evaluation_ready_flag"].mean()) if "evaluation_ready_flag" in events.columns and len(events) else 0.0,
        "score_summary": {
            column: {
                "mean": float(events[column].dropna().mean()),
                "count": int(events[column].dropna().shape[0]),
            }
            for column in score_cols
            if column in events.columns and not events[column].dropna().empty
        },
        "unsupported_by_source": events.groupby("source_dataset")["unsupported_action_flag"].mean().round(4).to_dict() if "unsupported_action_flag" in events.columns and len(events) else {},
        "plausibility_examples": events[["cod_event_id", "action_primary_label", "overall_plausibility_score", "unsupported_action_flag", "plausibility_evidence_summary"]].head(25).to_dict(orient="records") if len(events) else [],
    }
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def write_release_notes(
    input_dir: Path,
    output_path: Path,
    *,
    benchmark_report: dict[str, Any] | None = None,
    benchmark_audit_report: dict[str, Any] | None = None,
) -> Path:
    summary = summarize_build(input_dir)
    lines = [
        "# COD Release Notes",
        "",
        f"- Events: `{summary['events']}`",
        f"- Source-family coverage: `{summary['source_family_coverage']}`",
        f"- Expression-feature fraction: `{summary['fraction_with_expression_features']:.3f}`",
        f"- Benchmark action rows: `{summary['benchmark_action_rows']}`",
        f"- Benchmark output rows: `{summary['benchmark_output_rows']}`",
        f"- Benchmark outcome rows: `{summary['benchmark_outcome_rows']}`",
        "",
        "## Source Counts",
        "",
    ]
    for source, count in summary["sources"].items():
        lines.append(f"- `{source}`: `{count}`")
    if benchmark_report:
        lines.extend(
            [
                "",
                "## Benchmark Quality",
                "",
            ]
        )
        for task_name, payload in benchmark_report.get("task_quality_flags", {}).items():
            lines.append(f"- `{task_name}`: `{payload.get('status')}` ({', '.join(payload.get('reasons', [])) or 'no major warnings'})")
    if benchmark_audit_report:
        lines.extend(
            [
                "",
                "## Leakage Audit",
                "",
                f"- Source-family predictiveness: `{benchmark_audit_report.get('predictiveness', {}).get('source_family_predictiveness')}`",
                f"- State-depth predictiveness: `{benchmark_audit_report.get('predictiveness', {}).get('state_depth_predictiveness')}`",
            ]
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path
