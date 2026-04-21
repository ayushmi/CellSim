from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from cod.explorer import benchmark_task_counts, filter_events, load_explorer_bundle, summarize_missingness


def dataframe_download(df: pd.DataFrame, stem: str) -> None:
    csv_data = df.to_csv(index=False).encode("utf-8")
    json_data = df.to_json(orient="records", indent=2).encode("utf-8")
    st.download_button("Download CSV", csv_data, file_name=f"{stem}.csv", mime="text/csv")
    st.download_button("Download JSON", json_data, file_name=f"{stem}.json", mime="application/json")


def render_overview(bundle: dict[str, pd.DataFrame]) -> None:
    events = bundle["events"]
    benchmarks = bundle["benchmarks"]
    build_manifest = bundle["build_manifest"]
    summary_stats = bundle.get("summary_stats", {})
    output_space_report = bundle.get("output_space_report", {})
    st.header("Overview")
    a, b, c, d = st.columns(4)
    a.metric("Total events", len(events))
    b.metric("Source datasets", events["source_dataset"].nunique())
    c.metric("Action labels", events["action_level_2"].nunique())
    d.metric("Benchmark rows", len(benchmarks))
    e, f, g, h = st.columns(4)
    e.metric("Output-present events", int(events["output_present_flag"].sum()) if "output_present_flag" in events.columns else 0)
    f.metric("Outcome-present events", int(events["outcome_present_flag"].sum()) if "outcome_present_flag" in events.columns else 0)
    g.metric("Expression-feature fraction", f"{summary_stats.get('fraction_with_expression_features', 0.0):.1%}")
    h.metric("Perturbation-evidence fraction", f"{summary_stats.get('fraction_with_perturbation_evidence', 0.0):.1%}")

    st.subheader("Source family coverage")
    st.dataframe(events.groupby(["source_family", "source_dataset"]).size().reset_index(name="count"), use_container_width=True)
    if build_manifest:
        st.subheader("Build manifest")
        st.json(build_manifest, expanded=False)
    if bundle.get("benchmark_report"):
        st.subheader("Benchmark quality flags")
        st.json(bundle["benchmark_report"].get("task_quality_flags", {}), expanded=False)

    left, right = st.columns(2)
    with left:
        st.subheader("Action distribution")
        st.bar_chart(events["action_level_2"].value_counts())
        if output_space_report:
            st.subheader("Output type distribution")
            output_types = pd.Series(output_space_report.get("output_type_distribution", {}))
            if not output_types.empty:
                st.bar_chart(output_types)
        st.subheader("Evidence tier distribution")
        st.bar_chart(events["causal_evidence_tier"].value_counts().sort_index())
        st.subheader("State-depth distribution")
        st.bar_chart(events["state_depth_category"].value_counts())
    with right:
        st.subheader("Benchmark split counts")
        split_rows = pd.DataFrame(
            [
                {"split": "held_out_cell_type_bucket", "count": int(benchmarks["held_out_cell_type_bucket"].sum())},
                {"split": "held_out_intervention_bucket", "count": int(benchmarks["held_out_intervention_bucket"].sum())},
            ]
        )
        st.dataframe(split_rows, use_container_width=True)
        st.subheader("Pairing status summary")
        st.dataframe(events["measurement_pairing_status"].value_counts().reset_index(name="count"), use_container_width=True)
        st.subheader("Real vs Fixture vs Custom")
        st.dataframe(events["record_origin_type"].value_counts().reset_index(name="count"), use_container_width=True)
        st.subheader("Event types")
        st.dataframe(events["event_type"].value_counts().reset_index(name="count"), use_container_width=True)

    st.subheader("Missingness summary")
    st.dataframe(summarize_missingness(events), use_container_width=True)


def render_event_explorer(bundle: dict[str, pd.DataFrame]) -> None:
    events = bundle["events"]
    benchmarks = bundle["benchmarks"]
    benchmark_ids = set(benchmarks["cod_event_id"].tolist())

    st.header("Event Explorer")
    source_family = st.multiselect("Source family", sorted(events["source_family"].dropna().unique()))
    source = st.multiselect("Source", sorted(events["source_dataset"].dropna().unique()))
    cell_type = st.multiselect("Cell type", sorted(events["cell_type_label"].dropna().unique()))
    tissue = st.multiselect("Tissue", sorted(events["tissue_label"].dropna().unique()))
    action = st.multiselect("Action", sorted(events["action_level_2"].dropna().unique()))
    state_depth = st.multiselect("State depth", sorted(events["state_depth_category"].dropna().unique()))
    event_type = st.multiselect("Event type", sorted(events["event_type"].dropna().unique()))
    pairing = st.multiselect("Pairing status", sorted(events["measurement_pairing_status"].dropna().unique()))
    state_repr = st.multiselect("State representation", sorted(events["state_representation_type"].dropna().unique()))
    evidence_tiers = st.multiselect("Evidence tier", sorted(events["causal_evidence_tier"].dropna().unique()))
    min_confidence = st.slider("Minimum action confidence", 0.0, 1.0, 0.0, 0.05)
    benchmark_only = st.checkbox("Benchmark rows only", value=False)

    filtered = filter_events(events, source, cell_type, tissue, action, pairing, evidence_tiers, min_confidence, benchmark_only, benchmark_ids)
    if source_family:
        filtered = filtered[filtered["source_family"].isin(source_family)]
    if state_depth:
        filtered = filtered[filtered["state_depth_category"].isin(state_depth)]
    if event_type:
        filtered = filtered[filtered["event_type"].isin(event_type)]
    if state_repr:
        filtered = filtered[filtered["state_representation_type"].isin(state_repr)]
    st.dataframe(
        filtered[
            [
                "cod_event_id",
                "source_family",
                "source_dataset",
                "event_type",
                "cell_type_label",
                "tissue_label",
                "state_depth_category",
                "intervention_target_entity",
                "action_level_2",
                "causal_evidence_tier",
                "action_confidence_score",
                "measurement_pairing_status",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )
    dataframe_download(filtered, "cod_events_filtered")


def render_event_detail(bundle: dict[str, pd.DataFrame]) -> None:
    events = bundle["events"]
    st.header("Event Detail")
    event_id = st.selectbox("Select event", events["cod_event_id"].tolist())
    row = events.loc[events["cod_event_id"] == event_id].iloc[0].to_dict()

    sections = {
        "Identity / Provenance": [
            "cod_event_id", "cod_subject_id", "cod_cell_instance_id", "source_dataset", "source_study_id", "source_sample_id",
            "source_assay_id", "source_record_pointer", "source_accession", "source_download_url", "source_downloaded_at",
            "source_checksum", "source_release_info", "license_class",
        ],
        "Biological Context": [
            "species", "sex", "age", "health_status", "disease_state", "tissue_label", "uberon_id",
            "cell_type_label", "cell_ontology_id", "developmental_stage", "microenvironment_label", "spatial_region_label",
        ],
        "Intervention / Input": [
            "time_anchor_type", "t0_timestamp", "delta_t_to_output", "delta_t_to_outcome",
            "intervention_present", "intervention_type", "intervention_target_entity", "intervention_direction",
            "intervention_dose", "intervention_duration", "control_definition", "intervention_ref",
        ],
        "Constraints": [
            "constraint_profile_ref", "resource_state_ref", "stress_state_ref", "cell_cycle_state",
            "mitochondrial_state", "damage_response_state", "senescence_state", "constraint_refs",
        ],
        "Pre / Post State": [
            "pre_state_ref", "post_state_ref", "state_representation_type", "measured_state_flag",
            "harmonized_state_flag", "inferred_state_flag", "probabilistic_linkage_flag",
        ],
        "Action": [
            "action_level_0", "action_level_1", "action_level_2", "action_primary_label", "action_directionality",
            "action_zone", "action_assignment_method", "action_derivation_version", "action_confidence_score", "action_candidate_labels", "action_evidence_summary",
        ],
        "Short-Horizon Outputs": [
            "short_horizon_output_ref", "differential_expression_signature_ref", "differential_protein_signature_ref",
            "differential_metabolite_signature_ref", "secretome_signature_ref", "morphology_signature_ref",
            "viability_measure", "proliferation_measure", "output_type", "output_evidence_summary", "output_confidence_score",
        ],
        "Long-Horizon Outcomes": [
            "long_horizon_outcome_ref", "fate_outcome_label", "tissue_outcome_label", "therapy_response_label",
            "disease_progression_label", "survival_proxy", "outcome_time_horizon", "outcome_confidence_score",
        ],
        "Reward Context": [
            "reward_context_label", "candidate_reward_variables_ref", "fitness_proxy_score",
            "homeostasis_proxy_score", "immune_function_proxy_score", "reward_inference_method", "reward_context_ref",
        ],
        "Uncertainty / Evidence": [
            "causal_evidence_tier", "mechanistic_support_score", "measurement_pairing_status", "temporal_completeness_flag",
            "intervention_completeness_flag", "support_density_estimate", "support_domain_tag", "state_depth_category", "event_type",
            "harmonization_confidence", "measurement_support_score", "abstention_recommended_flag", "assay_distortion_notes_ref",
        ],
    }

    for title, keys in sections.items():
        st.subheader(title)
        section_rows = [{"field": key, "value": row.get(key)} for key in keys]
        st.table(pd.DataFrame(section_rows))

    st.subheader("Evidence Trace")
    evidence = bundle["evidence"]
    trace_rows = evidence[evidence["cod_event_id"] == event_id]
    st.dataframe(trace_rows, use_container_width=True, hide_index=True)


def render_ontology_browser(bundle: dict[str, pd.DataFrame]) -> None:
    st.header("Ontology Browser")
    st.subheader("Action ontology")
    st.dataframe(bundle["action_ontology"], use_container_width=True)
    st.subheader("Evidence tiers")
    st.dataframe(bundle["evidence_tiers"], use_container_width=True)
    st.subheader("Action mapping engine")
    st.code(
        "Weak supervision maps marker and pathway programs into action families such as interferon, inflammatory, "
        "proliferation, stress, apoptosis, DNA-repair, metabolic shift, differentiation, migration, quiescence, "
        "or homeostasis with candidate labels and confidence.",
        language="text",
    )


def render_benchmark_explorer(bundle: dict[str, pd.DataFrame]) -> None:
    benchmarks = bundle["benchmarks"]
    st.header("Benchmark Explorer")
    st.dataframe(benchmark_task_counts(benchmarks), use_container_width=True)
    if bundle.get("benchmark_report"):
        st.subheader("Benchmark report")
        st.json(bundle["benchmark_report"], expanded=False)
    if bundle.get("benchmark_audit_report"):
        st.subheader("Leakage audit")
        st.json(bundle["benchmark_audit_report"], expanded=False)
    if bundle.get("baseline_report"):
        st.subheader("Baseline results")
        st.json(bundle["baseline_report"], expanded=False)
    st.subheader("Split counts")
    split_df = pd.DataFrame(
        [
            {"split": "held_out_cell_type_bucket", "count": int(benchmarks["held_out_cell_type_bucket"].sum())},
            {"split": "held_out_intervention_bucket", "count": int(benchmarks["held_out_intervention_bucket"].sum())},
            {"split": "held_out_source_family_flag", "count": int(benchmarks["held_out_source_family_flag"].sum()) if "held_out_source_family_flag" in benchmarks.columns else 0},
            {"split": "held_out_state_depth_flag", "count": int(benchmarks["held_out_state_depth_flag"].sum()) if "held_out_state_depth_flag" in benchmarks.columns else 0},
        ]
    )
    st.dataframe(split_df, use_container_width=True)
    selected_split = st.selectbox("Filter split", ["all", "held_out_cell_type_bucket", "held_out_intervention_bucket"])
    filtered = benchmarks
    if selected_split != "all":
        filtered = benchmarks[benchmarks[selected_split]]
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    dataframe_download(filtered, "benchmark_rows_filtered")


def render_source_support(bundle: dict[str, pd.DataFrame]) -> None:
    st.header("Source Browser")
    support = bundle["source_support"]
    st.dataframe(support, use_container_width=True, hide_index=True)
    if not bundle["source_contracts"].empty:
        st.subheader("Source contracts")
        st.dataframe(bundle["source_contracts"], use_container_width=True, hide_index=True)
    dataframe_download(support, "source_support_matrix")


def render_build_info(bundle: dict[str, pd.DataFrame]) -> None:
    st.header("Build / Version")
    st.subheader("Build manifest")
    st.json(bundle["build_manifest"], expanded=False)
    st.subheader("Summary stats")
    st.json(bundle["summary_stats"], expanded=False)
    if bundle.get("action_space_report"):
        st.subheader("Action-space report")
        st.json(bundle["action_space_report"], expanded=False)
    if bundle.get("output_space_report"):
        st.subheader("Output-space report")
        st.json(bundle["output_space_report"], expanded=False)
    if bundle.get("data_quality_report"):
        st.subheader("Data-quality report")
        st.json(bundle["data_quality_report"], expanded=False)


def render_build_comparison(bundle: dict[str, pd.DataFrame]) -> None:
    st.header("Build Comparison")
    default_compare = ROOT / "data" / "materialized_cod10_public"
    compare_dir = Path(st.text_input("Comparison build directory", str(default_compare)))
    if not compare_dir.exists():
        st.info("Comparison directory not found.")
        return
    compare_bundle = load_explorer_bundle(ROOT, compare_dir)
    current = bundle["summary_stats"]
    previous = compare_bundle["summary_stats"]
    rows = []
    for key in [
        "events",
        "source_family_coverage",
        "benchmark_action_rows",
        "benchmark_output_rows",
        "benchmark_outcome_rows",
        "fraction_with_expression_features",
        "fraction_with_outputs",
    ]:
        rows.append({"metric": key, "current": current.get(key), "comparison": previous.get(key)})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_data_quality(bundle: dict[str, pd.DataFrame]) -> None:
    events = bundle["events"]
    st.header("Data Quality")
    left, right = st.columns(2)
    with left:
        st.subheader("Missingness distributions")
        st.dataframe(summarize_missingness(events), use_container_width=True)
        st.subheader("State representation counts")
        st.bar_chart(events["state_representation_type"].value_counts())
    with right:
        st.subheader("Harmonization confidence")
        st.bar_chart(events["harmonization_confidence"].round(1).value_counts().sort_index())
        st.subheader("Evidence support")
        support = events[["cod_event_id", "measurement_support_score", "prediction_support_score", "mechanistic_support_score"]]
        st.dataframe(support, use_container_width=True, hide_index=True)
        if "output_confidence_score" in events.columns:
            st.subheader("Output confidence")
            st.bar_chart(events["output_confidence_score"].dropna().round(1).value_counts().sort_index())
        st.subheader("Record origin distribution")
        st.bar_chart(events["record_origin_type"].value_counts())


def main() -> None:
    st.set_page_config(page_title="COD Explorer", layout="wide")
    st.title("COD Explorer")
    st.caption("Read-only local explorer for materialized Cell Operating Dataset outputs.")

    cli_default = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    default_data_dir = cli_default if cli_default else ROOT / "examples" / "output"
    data_dir = Path(st.sidebar.text_input("Materialized output directory", str(default_data_dir)))
    bundle = load_explorer_bundle(ROOT, data_dir)

    page = st.sidebar.radio(
        "View",
        ["Overview", "Event Explorer", "Event Detail", "Source Browser", "Ontology Browser", "Benchmark Explorer", "Data Quality", "Build / Version", "Build Comparison"],
    )

    if page == "Overview":
        render_overview(bundle)
    elif page == "Event Explorer":
        render_event_explorer(bundle)
    elif page == "Event Detail":
        render_event_detail(bundle)
    elif page == "Source Browser":
        render_source_support(bundle)
    elif page == "Ontology Browser":
        render_ontology_browser(bundle)
    elif page == "Benchmark Explorer":
        render_benchmark_explorer(bundle)
    elif page == "Data Quality":
        render_data_quality(bundle)
    elif page == "Build / Version":
        render_build_info(bundle)
    elif page == "Build Comparison":
        render_build_comparison(bundle)


if __name__ == "__main__":
    main()
