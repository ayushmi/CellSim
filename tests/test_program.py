from pathlib import Path

import pytest

from cod.benchmarks import prepare_benchmarks
from cod.materialize import materialize_cod
from cod.reporting import summarize_build, validate_build_consistency, write_output_space_report
from cod.source_support import generate_support_matrix_markdown, load_source_support


def test_source_support_matrix_contains_all_19_families() -> None:
    root = Path(__file__).resolve().parents[1]
    payload = load_source_support(root)
    assert len(payload["sources"]) == 19
    markdown = generate_support_matrix_markdown(root)
    assert "Human Cell Atlas" in markdown
    assert "OmniPath" in markdown


def test_benchmark_prep_generates_report(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    materialized = tmp_path / "materialized"
    materialize_cod(root=root, raw_dir=root / "examples" / "raw", output_dir=materialized)
    report = prepare_benchmarks(
        input_dir=materialized,
        output_dir=tmp_path / "benchmarks",
        config_path=root / "configs" / "benchmark_prep.yaml",
    )
    assert report["counts"]["rows"] > 0
    assert report["task_counts"]["state_plus_intervention_to_outcome"] == 0
    assert (tmp_path / "benchmarks" / "benchmark_dataset.jsonl").exists()
    assert (tmp_path / "benchmarks" / "benchmark_audit_report.json").exists()


def test_benchmark_prep_rejects_invalid_outcome_task_config(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    materialized = tmp_path / "materialized"
    materialize_cod(root=root, raw_dir=root / "examples" / "raw", output_dir=materialized)
    invalid_config = tmp_path / "benchmark_invalid.yaml"
    invalid_config.write_text(
        "\n".join(
            [
                "version: 0.1.0",
                "random_seed: 7",
                "splits:",
                "  train_fraction: 0.7",
                "  val_fraction: 0.15",
                "  test_fraction: 0.15",
                "tasks:",
                "  - state_plus_intervention_to_outcome",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Configured benchmark tasks lack valid labels"):
        prepare_benchmarks(
            input_dir=materialized,
            output_dir=tmp_path / "benchmarks_invalid",
            config_path=invalid_config,
        )


def test_summary_and_consistency_checks_agree(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    materialized = tmp_path / "materialized"
    materialize_cod(root=root, raw_dir=root / "examples" / "raw", output_dir=materialized)
    summary = summarize_build(materialized)
    validation = validate_build_consistency(materialized, summary)
    assert summary["events"] == 8
    assert summary["source_family_coverage"] >= 1
    assert validation["checks"]["event_count_matches_summary"]


def test_output_space_report_serializes_missing_output_evidence_cleanly(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    materialized = tmp_path / "materialized"
    materialize_cod(root=root, raw_dir=root / "examples" / "raw", output_dir=materialized)
    report = write_output_space_report(materialized, tmp_path / "output_space_report.json")
    assert "output_evidence_summary_examples" in report
    assert all("NaN" not in str(example) for example in report["output_evidence_summary_examples"])
