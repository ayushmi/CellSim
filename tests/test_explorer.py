from pathlib import Path

from cod.explorer import benchmark_task_counts, load_explorer_bundle, summarize_missingness


def test_explorer_bundle_loads_example_outputs() -> None:
    root = Path(__file__).resolve().parents[1]
    bundle = load_explorer_bundle(root, root / "examples" / "output")

    assert not bundle["events"].empty
    assert not bundle["benchmarks"].empty
    assert not bundle["action_ontology"].empty
    assert "output_space_report" in bundle


def test_summary_helpers_return_rows() -> None:
    root = Path(__file__).resolve().parents[1]
    bundle = load_explorer_bundle(root, root / "examples" / "output")

    missingness = summarize_missingness(bundle["events"])
    benchmark_counts = benchmark_task_counts(bundle["benchmarks"])

    assert len(missingness) > 0
    assert set(benchmark_counts["task"]) == {
        "state_to_action",
        "state_plus_intervention_to_output",
        "state_plus_intervention_to_outcome",
    }
