from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .action_mapping import infer_action
from .builds import create_build_manifest
from .contracts import load_action_ontology, load_benchmark_splits, load_source_contracts
from .enums import (
    ActionAssignmentMethod,
    InterventionDirection,
    InterventionType,
    StateRepresentationType,
    TimeAnchorType,
)
from .harmonization import assess_linkage, normalize_cell_type, normalize_disease, normalize_gene_id, normalize_tissue
from .io_utils import dump_models, write_jsonl, write_parquet
from .models import CellTransitionEvent, EvidenceTraceRecord, FeatureValue
from .reporting import (
    validate_build_consistency,
    write_action_space_report,
    write_build_summary,
    write_data_quality_report,
    write_outcome_space_report,
    write_output_space_report,
    write_plausibility_report,
    write_trajectory_report,
)
from .source_support import load_source_support, source_support_rows
from .source_registry import SOURCE_FAMILIES


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_raw_records(raw_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(raw_dir.glob("*.jsonl")):
        rows.extend(read_jsonl(path))
    return rows


def build_knowledge_indices(raw_records: list[dict[str, Any]]) -> dict[str, Any]:
    trrust_genes: set[str] = set()
    omnipath_genes: set[str] = set()
    reactome_terms: set[str] = set()
    depmap_target_scores: dict[str, list[float]] = {}
    encode_cell_types: set[str] = set()

    for record in raw_records:
        dataset = record.get("dataset")
        if dataset == "TRRUST":
            trrust_genes.update(item.get("feature_id") for item in record.get("signals", []) if item.get("feature_id"))
        elif dataset == "OmniPath":
            omnipath_genes.update(item.get("feature_id") for item in record.get("signals", []) if item.get("feature_id"))
        elif dataset == "Reactome":
            pathway = str(record.get("dominant_pathway", "") or "").strip().lower()
            if pathway:
                reactome_terms.add(pathway)
        elif dataset == "BioModels":
            pathway = str(record.get("dominant_pathway", "") or "").strip().lower()
            if pathway:
                reactome_terms.add(pathway)
        elif dataset == "DepMap" and record.get("intervention_target_entity") and record.get("viability_measure") is not None:
            try:
                depmap_target_scores.setdefault(str(record["intervention_target_entity"]), []).append(float(record["viability_measure"]))
            except (TypeError, ValueError):
                pass
        elif dataset == "ENCODE" and record.get("cell_type_label"):
            encode_cell_types.add(str(record["cell_type_label"]))

    depmap_target_mean = {
        gene: sum(values) / len(values)
        for gene, values in depmap_target_scores.items()
        if values
    }
    return {
        "trrust_genes": trrust_genes,
        "omnipath_genes": omnipath_genes,
        "reactome_terms": reactome_terms,
        "depmap_target_mean": depmap_target_mean,
        "encode_cell_types": encode_cell_types,
    }


def derive_outcome_fields(record: dict[str, Any], output_present_flag: bool) -> dict[str, Any]:
    dataset = record.get("dataset")
    outcome_fields: dict[str, Any] = {
        "outcome_present_flag": False,
        "outcome_ref": None,
        "long_horizon_outcome_ref": None,
        "outcome_horizon_type": "unavailable",
        "proxy_outcome_flag": False,
        "outcome_proxy_type": None,
        "outcome_confidence_score": 0.0,
        "therapy_response_label": record.get("therapy_response_label"),
        "disease_progression_label": record.get("disease_progression_label"),
        "survival_proxy": record.get("survival_proxy"),
        "outcome_time_horizon": record.get("outcome_time_horizon"),
    }

    if dataset == "DepMap" and record.get("intervention_present") and record.get("viability_measure") is not None:
        try:
            viability_score = float(record["viability_measure"])
        except (TypeError, ValueError):
            viability_score = None
        if viability_score is not None:
            if viability_score >= 0.2:
                label = "viability_resilient_proxy"
                confidence = 0.78
            else:
                label = "viability_sensitive_proxy"
                confidence = 0.72
            outcome_fields.update(
                {
                    "outcome_present_flag": True,
                    "outcome_ref": f"outcome:{record['record_id']}",
                    "long_horizon_outcome_ref": f"outcome:{record['record_id']}",
                    "outcome_horizon_type": "medium_horizon",
                    "proxy_outcome_flag": True,
                    "outcome_proxy_type": "viability_like_outcome",
                    "outcome_confidence_score": confidence,
                    "therapy_response_label": label,
                    "outcome_time_horizon": "post_dependency_assay",
                }
            )
    elif dataset == "TCGA" and any([record.get("therapy_response_label"), record.get("disease_progression_label"), record.get("survival_proxy")]):
        outcome_fields.update(
            {
                "outcome_present_flag": True,
                "outcome_ref": f"outcome:{record['record_id']}",
                "long_horizon_outcome_ref": f"outcome:{record['record_id']}",
                "outcome_horizon_type": "long_horizon",
                "proxy_outcome_flag": True,
                "outcome_proxy_type": "clinical_context_weak_outcome",
                "outcome_confidence_score": 0.45,
            }
        )

    output_horizon_type = "unavailable"
    if output_present_flag:
        if dataset in {"Perturb-seq", "LINCS"}:
            output_horizon_type = "short_horizon"
        elif dataset == "DepMap":
            output_horizon_type = "medium_horizon"
        else:
            output_horizon_type = "short_horizon"
    outcome_fields["output_horizon_type"] = output_horizon_type
    return outcome_fields


def derive_plausibility_fields(record: dict[str, Any], action_label: str, knowledge: dict[str, Any]) -> dict[str, Any]:
    transcriptome_genes = {str(item.get("feature_id")) for item in record.get("transcriptome", []) if item.get("feature_id")}
    intervention_target = str(record.get("intervention_target_entity", "") or "")
    pathway = str(record.get("dominant_pathway", "") or "").lower()
    cell_type = str(record.get("cell_type_label", "") or "")
    measurement_support = float(record.get("measurement_support_score", 0.5) or 0.5)
    direct_signal = bool(record.get("transcriptome") or record.get("signals") or record.get("viability_measure") is not None)

    regulatory_hits = 0
    if intervention_target and intervention_target in knowledge["trrust_genes"]:
        regulatory_hits += 1
    regulatory_hits += sum(1 for gene in transcriptome_genes if gene in knowledge["trrust_genes"])
    regulatory_support_score = min(1.0, (0.2 if direct_signal else 0.0) + 0.12 * regulatory_hits + (0.2 if cell_type in knowledge["encode_cell_types"] else 0.0))

    pathway_hits = 0
    if pathway and any(term in pathway or pathway in term for term in knowledge["reactome_terms"]):
        pathway_hits += 1
    if action_label == "activate_interferon_program" and any(gene in transcriptome_genes for gene in {"STAT1", "IFIT1", "ISG15", "IFIT3", "CXCL10"}):
        pathway_hits += 1
    if action_label == "activate_inflammatory_cytokine_program" and any(gene in transcriptome_genes for gene in {"IL6", "TNF", "NFKBIA", "CXCL8"}):
        pathway_hits += 1
    if action_label == "enter_cell_cycle_or_proliferation_program" and any(gene in transcriptome_genes for gene in {"MKI67", "TOP2A", "PCNA"}):
        pathway_hits += 1
    pathway_support_score = min(1.0, (0.2 if pathway and pathway not in {"perturbation_response", "lincs_chemical_response"} else 0.0) + 0.22 * pathway_hits)

    metabolic_hits = sum(1 for gene in transcriptome_genes if gene in {"LDHA", "SLC2A1", "PGK1", "ENO1"})
    metabolic_support_score = min(1.0, (0.1 if direct_signal else 0.0) + 0.18 * metabolic_hits + (0.25 if "glycolysis" in pathway else 0.0))

    depmap_mean = knowledge["depmap_target_mean"].get(intervention_target)
    if depmap_mean is not None:
        viability_constraint_score = min(1.0, max(0.0, 0.35 + (1.0 - depmap_mean) * 0.5))
    elif record.get("viability_measure") is not None:
        try:
            viability_constraint_score = min(1.0, max(0.0, 0.35 + (1.0 - float(record["viability_measure"])) * 0.5))
        except (TypeError, ValueError):
            viability_constraint_score = 0.0
    elif intervention_target:
        viability_constraint_score = 0.25
    else:
        viability_constraint_score = 0.0

    score_values = [regulatory_support_score, pathway_support_score, metabolic_support_score, viability_constraint_score, measurement_support]
    overall_plausibility_score = sum(score_values) / len(score_values)
    unsupported_action_flag = (
        bool(record.get("intervention_present"))
        and action_label not in {"no_confident_action_assignment", "maintain_homeostatic_program"}
        and overall_plausibility_score < 0.28
    )
    return {
        "regulatory_support_score": round(regulatory_support_score, 4),
        "pathway_support_score": round(pathway_support_score, 4),
        "metabolic_support_score": round(metabolic_support_score, 4),
        "viability_constraint_score": round(viability_constraint_score, 4),
        "overall_plausibility_score": round(overall_plausibility_score, 4),
        "plausibility_evidence_summary": (
            f"regulatory_hits={regulatory_hits}; pathway={pathway or 'none'}; "
            f"transcriptome_genes={sorted(list(transcriptome_genes))[:8]}; "
            f"depmap_target_mean={depmap_mean}"
        ),
        "unsupported_action_flag": unsupported_action_flag,
    }


def assign_trajectory_metadata(events: list[CellTransitionEvent]) -> None:
    grouped: dict[str, list[CellTransitionEvent]] = {}
    for event in events:
        if event.event_type == "transition_event" and event.pre_state_ref and event.short_horizon_output_ref:
            trajectory_id = f"traj:{event.source_dataset}:{event.cell_type_label}:{event.intervention_target_entity or 'none'}"
            event.trajectory_id = trajectory_id
            event.trajectory_group_id = trajectory_id
            event.trajectory_class = "pseudo_trajectory"
            event.exact_vs_inferred_trajectory_flag = False
            event.previous_event_ref = event.pre_state_ref
            event.next_event_ref = event.long_horizon_outcome_ref or event.short_horizon_output_ref
            grouped.setdefault(trajectory_id, []).append(event)
        elif event.event_type == "state_event":
            trajectory_id = f"traj:{event.source_dataset}:{event.cell_type_label}:baseline"
            event.trajectory_id = trajectory_id
            event.trajectory_group_id = trajectory_id
            event.trajectory_class = "single_step_transition"
            event.exact_vs_inferred_trajectory_flag = True
            grouped.setdefault(trajectory_id, []).append(event)
    for trajectory_id, members in grouped.items():
        members.sort(key=lambda item: (item.t0_timestamp, item.cod_event_id))
        length = len(members)
        for position, event in enumerate(members, start=1):
            event.trajectory_position = position
            event.trajectory_length = length
            if event.trajectory_class == "single_step_transition":
                event.previous_event_ref = None
                event.next_event_ref = None


def materialize_cod(root: Path, raw_dir: Path, output_dir: Path) -> dict[str, int]:
    source_contracts = load_source_contracts(root)
    load_action_ontology(root)
    split_spec = load_benchmark_splits(root)
    raw_records = load_raw_records(raw_dir)
    knowledge = build_knowledge_indices(raw_records)
    family_map = {row["source_name"]: row["source_family"] for row in source_support_rows(root)}

    events: list[CellTransitionEvent] = []
    traces: list[EvidenceTraceRecord] = []
    transcriptome: list[FeatureValue] = []
    metabolome: list[FeatureValue] = []
    signaling: list[FeatureValue] = []
    benchmark_rows: list[dict[str, Any]] = []

    for idx, record in enumerate(raw_records, start=1):
        linkage = assess_linkage(record)
        action, action_traces = infer_action(record)
        event_id = f"COD_CTE_{idx:05d}"
        transcriptome_ref = f"tx:{event_id}" if record.get("transcriptome") else None
        metabolome_ref = f"met:{event_id}" if record.get("metabolome") else None
        signaling_ref = f"sig:{event_id}" if record.get("signals") else None

        for item in record.get("transcriptome", []):
            transcriptome.append(
                FeatureValue(
                    profile_ref=transcriptome_ref,
                    feature_space_id="hgnc_gene_symbol",
                    feature_id=normalize_gene_id(item["feature_id"]),
                    feature_name=item["feature_id"],
                    value=item["value"],
                    value_type=item.get("value_type", "log_fc"),
                    support_score=item.get("support_score", 0.85),
                    provenance_ref=f"trace:{record['record_id']}:transcriptome:{item['feature_id']}",
                )
            )
            traces.append(
                EvidenceTraceRecord(
                    evidence_trace_id=f"trace:{record['record_id']}:transcriptome:{item['feature_id']}",
                    cod_event_id=event_id,
                    field_name="transcriptome_profile_ref",
                    source_dataset=record["dataset"],
                    source_record_pointer=record["source_record_pointer"],
                    transformation_step="gene_identifier_normalization",
                    rule_or_model="manual_registry_v0",
                    confidence=item.get("support_score", 0.85),
                )
            )

        for item in record.get("metabolome", []):
            metabolome.append(
                FeatureValue(
                    profile_ref=metabolome_ref,
                    feature_space_id="metabolite_symbol",
                    feature_id=item["feature_id"],
                    feature_name=item["feature_id"],
                    value=item["value"],
                    value_type=item.get("value_type", "score"),
                    support_score=item.get("support_score", 0.75),
                    provenance_ref=f"trace:{record['record_id']}:metabolome:{item['feature_id']}",
                )
            )

        for item in record.get("signals", []):
            signaling.append(
                FeatureValue(
                    profile_ref=signaling_ref,
                    feature_space_id="signaling_entity",
                    feature_id=item["feature_id"],
                    feature_name=item["feature_id"],
                    value=item["value"],
                    value_type=item.get("value_type", "score"),
                    support_score=item.get("support_score", 0.8),
                    provenance_ref=f"trace:{record['record_id']}:signals:{item['feature_id']}",
                )
            )

        traces.extend(action_traces)
        traces.append(
            EvidenceTraceRecord(
                evidence_trace_id=f"trace:{record['record_id']}:event",
                cod_event_id=event_id,
                field_name="cod_event",
                source_dataset=record["dataset"],
                source_record_pointer=record["source_record_pointer"],
                transformation_step="cte_assembly",
                rule_or_model="cod_reference_pipeline_v0.1",
                confidence=linkage.harmonization_confidence,
                notes=f"pairing_status={linkage.pairing_status.value}",
            )
        )

        has_expression_features = bool(record.get("transcriptome"))
        output_present_flag = bool(
            has_expression_features
            or record.get("short_horizon_output_ref")
            or record.get("viability_measure")
            or record.get("proliferation_measure")
            or record.get("secretome_signature_ref")
            or record.get("morphology_signature_ref")
        )
        outcome_fields = derive_outcome_fields(record, output_present_flag)
        outcome_present_flag = outcome_fields["outcome_present_flag"]
        state_representation_type = StateRepresentationType(record.get("state_representation_type", "harmonized"))
        if record["dataset"] in {"OmniPath", "Reactome", "TRRUST", "BioModels", "Recon3D", "KEGG"}:
            state_depth_category = "context_only"
            event_type = "knowledge_support_event"
        elif outcome_present_flag and not has_expression_features and not record.get("intervention_present"):
            state_depth_category = "outcome_bearing"
            event_type = "outcome_event"
        elif record.get("constraint_refs") and (record.get("signals") or has_expression_features):
            state_depth_category = "transition_bearing" if record.get("intervention_present") and has_expression_features else "context_only"
            event_type = "composite_event"
        elif record.get("intervention_present") and has_expression_features:
            state_depth_category = "outcome_bearing" if outcome_present_flag else "transition_bearing"
            event_type = "composite_event" if outcome_present_flag else "transition_event"
        elif has_expression_features:
            state_depth_category = "weak_state_bearing" if state_representation_type == StateRepresentationType.inferred else "state_bearing"
            event_type = "state_event"
        elif record.get("spatial_region_label") or record.get("microenvironment_label") or record.get("signals"):
            state_depth_category = "context_only"
            event_type = "context_event"
        else:
            state_depth_category = "metadata_only"
            event_type = "metadata_event"
        plausibility_fields = derive_plausibility_fields(record, action.action_level_2, knowledge)
        evaluation_ready_flag = bool(
            record.get("intervention_present")
            and (
                output_present_flag
                or outcome_present_flag
                or action.action_level_2 != "no_confident_action_assignment"
            )
        )

        event = CellTransitionEvent(
            cod_event_id=event_id,
            cod_subject_id=record["subject_id"],
            cod_cell_instance_id=record["cell_instance_id"],
            cod_parent_event_id=record.get("parent_event_id"),
            cod_batch_id="batch_v0_example",
            cod_release_version="0.1.0",
            source_dataset=record["dataset"],
            source_family=family_map.get(record["dataset"]),
            source_study_id=record["study_id"],
            source_sample_id=record["source_sample_id"],
            source_cell_id=record.get("source_cell_id"),
            source_assay_id=record["assay_id"],
            source_record_pointer=record["source_record_pointer"],
            source_accession=record.get("source_accession"),
            source_download_url=record.get("source_download_url"),
            source_downloaded_at=record.get("source_downloaded_at"),
            source_checksum=record.get("source_checksum"),
            source_release_info=record.get("source_release_info"),
            processing_pipeline_version="cod_ref_pipeline_0.1.0",
            evidence_trace_id=f"trace:{record['record_id']}:event",
            license_class=record.get("license_class", "research_restricted"),
            record_origin_type=record.get("record_origin_type", "public_upstream" if record.get("source_download_url") else "fixture"),
            species=record.get("species", "Homo sapiens"),
            donor_id_normalized=record.get("subject_id"),
            sex=record.get("sex"),
            age=record.get("age"),
            ancestry=record.get("ancestry"),
            health_status=record.get("health_status"),
            disease_state=record.get("disease_state"),
            disease_ontology_id=normalize_disease(record.get("disease_state")),
            tissue_label=record["tissue_label"],
            uberon_id=normalize_tissue(record["tissue_label"]),
            cell_type_label=record["cell_type_label"],
            cell_ontology_id=normalize_cell_type(record["cell_type_label"]),
            developmental_stage=record.get("developmental_stage"),
            microenvironment_label=record.get("microenvironment_label"),
            spatial_region_label=record.get("spatial_region_label"),
            time_anchor_type=TimeAnchorType(record.get("time_anchor_type", "baseline")),
            t0_timestamp=record["t0_timestamp"],
            t0_time_unit=record.get("t0_time_unit", "hours"),
            delta_t_to_output=record.get("delta_t_to_output"),
            delta_t_to_outcome=record.get("delta_t_to_outcome", outcome_fields.get("outcome_time_horizon")),
            trajectory_group_id=record.get("trajectory_group_id"),
            time_uncertainty_score=record.get("time_uncertainty_score", 0.1),
            intervention_present=record.get("intervention_present", False),
            intervention_type=InterventionType(record.get("intervention_type", "none")),
            intervention_target_entity=record.get("intervention_target_entity"),
            intervention_target_id=record.get("intervention_target_id"),
            intervention_direction=InterventionDirection(record.get("intervention_direction", "none")),
            intervention_dose=record.get("intervention_dose"),
            intervention_dose_unit=record.get("intervention_dose_unit"),
            intervention_duration=record.get("intervention_duration"),
            intervention_delivery_mode=record.get("intervention_delivery_mode"),
            intervention_combo_id=record.get("intervention_combo_id"),
            control_definition=record.get("control_definition"),
            has_genome_state=record.get("has_genome_state", False),
            has_epigenome_state=record.get("has_epigenome_state", False),
            has_transcriptome_state=bool(transcriptome_ref),
            has_proteome_state=record.get("has_proteome_state", False),
            has_phosphoproteome_state=record.get("has_phosphoproteome_state", False),
            has_metabolome_state=bool(metabolome_ref),
            has_spatial_state=bool(record.get("spatial_region_label")),
            has_neighbor_context=bool(record.get("neighbor_profile_ref")),
            has_clinical_context=bool(record.get("therapy_response_label") or record.get("disease_progression_label")),
            has_time_series_context=bool(record.get("delta_t_to_output") or record.get("delta_t_to_outcome")),
            genome_profile_ref=record.get("genome_profile_ref"),
            epigenome_profile_ref=record.get("epigenome_profile_ref"),
            transcriptome_profile_ref=transcriptome_ref,
            proteome_profile_ref=record.get("proteome_profile_ref"),
            phosphoproteome_profile_ref=record.get("phosphoproteome_profile_ref"),
            metabolome_profile_ref=metabolome_ref,
            spatial_profile_ref=record.get("spatial_profile_ref"),
            neighbor_profile_ref=record.get("neighbor_profile_ref"),
            state_embedding_ref=record.get("state_embedding_ref", f"embed:{event_id}"),
            state_summary_ref=record.get("state_summary_ref", f"summary:{event_id}"),
            external_signal_set_ref=signaling_ref,
            resource_state_ref=record.get("resource_state_ref"),
            stress_state_ref=record.get("stress_state_ref"),
            cell_cycle_state=record.get("cell_cycle_state"),
            mitochondrial_state=record.get("mitochondrial_state"),
            damage_response_state=record.get("damage_response_state"),
            senescence_state=record.get("senescence_state"),
            immune_context_ref=record.get("immune_context_ref"),
            constraint_profile_ref=record.get("constraint_profile_ref", f"constraint:{event_id}"),
            pre_state_ref=record.get("pre_state_ref", record.get("state_summary_ref", f"summary:{event_id}:pre")),
            post_state_ref=record.get("post_state_ref", f"output:{event_id}" if output_present_flag else None),
            intervention_ref=record.get("intervention_ref", f"intervention:{event_id}" if record.get("intervention_present") else None),
            constraint_refs=record.get("constraint_refs", [record.get("constraint_profile_ref", f"constraint:{event_id}")]),
            reward_context_ref=record.get("reward_context_ref"),
            measured_state_flag=state_representation_type in {StateRepresentationType.raw_measured, StateRepresentationType.normalized_measured},
            harmonized_state_flag=state_representation_type == StateRepresentationType.harmonized,
            inferred_state_flag=state_representation_type == StateRepresentationType.inferred,
            probabilistic_linkage_flag=linkage.pairing_status.value in {"probabilistic_context", "pseudo_cell", "unpaired"},
            action_level_0=action.action_level_0,
            action_level_1=action.action_level_1,
            action_level_2=action.action_level_2,
            action_label_set_ref=f"actionset:{event_id}",
            action_primary_label=action.action_level_2,
            action_intensity_score=action.intensity_score,
            action_directionality=action.directionality,
            action_zone=action.zone,
            action_confidence_score=action.confidence_score,
            action_assignment_method=ActionAssignmentMethod(action.assignment_method),
            short_horizon_output_ref=record.get("short_horizon_output_ref", f"output:{event_id}" if output_present_flag else None),
            output_ref=record.get("short_horizon_output_ref", f"output:{event_id}" if output_present_flag else None),
            differential_expression_signature_ref=transcriptome_ref if has_expression_features else None,
            differential_protein_signature_ref=record.get("proteome_signature_ref"),
            differential_metabolite_signature_ref=metabolome_ref if record.get("metabolome") else None,
            secretome_signature_ref=record.get("secretome_signature_ref"),
            morphology_signature_ref=record.get("morphology_signature_ref"),
            viability_measure=record.get("viability_measure"),
            proliferation_measure=record.get("proliferation_measure"),
            output_confidence_score=record.get("output_confidence_score", 0.75 if output_present_flag else 0.0),
            output_horizon_type=outcome_fields["output_horizon_type"],
            long_horizon_outcome_ref=outcome_fields["long_horizon_outcome_ref"] if outcome_present_flag else None,
            outcome_ref=outcome_fields["outcome_ref"] if outcome_present_flag else None,
            fate_outcome_label=record.get("fate_outcome_label"),
            tissue_outcome_label=record.get("tissue_outcome_label"),
            therapy_response_label=outcome_fields["therapy_response_label"],
            disease_progression_label=outcome_fields["disease_progression_label"],
            survival_proxy=outcome_fields["survival_proxy"],
            outcome_time_horizon=outcome_fields["outcome_time_horizon"],
            outcome_horizon_type=outcome_fields["outcome_horizon_type"],
            proxy_outcome_flag=outcome_fields["proxy_outcome_flag"],
            outcome_proxy_type=outcome_fields["outcome_proxy_type"],
            outcome_confidence_score=outcome_fields["outcome_confidence_score"],
            reward_context_label=record.get("reward_context_label"),
            candidate_reward_variables_ref=record.get("candidate_reward_variables_ref"),
            fitness_proxy_score=record.get("fitness_proxy_score"),
            homeostasis_proxy_score=record.get("homeostasis_proxy_score"),
            immune_function_proxy_score=record.get("immune_function_proxy_score"),
            reward_inference_method=record.get("reward_inference_method"),
            raw_qc_score=record.get("raw_qc_score", 0.9),
            harmonization_qc_score=record.get("harmonization_qc_score", linkage.harmonization_confidence),
            batch_correction_flag=record.get("batch_correction_flag", False),
            imputation_flag=record.get("imputation_flag", False),
            deconvolution_flag=record.get("deconvolution_flag", False),
            modality_conflict_flag=linkage.modality_conflict_flag,
            manual_review_flag=record.get("manual_review_flag", False),
            exclusion_reason=record.get("exclusion_reason"),
            state_representation_type=state_representation_type,
            assay_distortion_notes_ref=record.get("assay_distortion_notes_ref"),
            measurement_support_score=record.get("measurement_support_score", linkage.support_density_estimate),
            causal_evidence_tier=action.evidence_tier,
            causal_support_ref=record.get("causal_support_ref", f"support:{event_id}"),
            replication_count=record.get("replication_count", 0),
            mechanistic_support_score=record.get("mechanistic_support_score", 0.5 if record["dataset"] in {"ENCODE", "OmniPath"} else 0.3),
            prediction_support_score=record.get("prediction_support_score", linkage.support_density_estimate),
            ood_flag=record.get("ood_flag", False),
            abstention_recommended_flag=record.get("abstention_recommended_flag", linkage.harmonization_confidence < 0.65),
            uncertainty_vector_ref=record.get("uncertainty_vector_ref"),
            measurement_pairing_status=linkage.pairing_status,
            temporal_completeness_flag=bool(record.get("delta_t_to_output") or record.get("delta_t_to_outcome")),
            intervention_completeness_flag=bool(record.get("intervention_present") == False or (record.get("intervention_target_entity") and record.get("intervention_direction"))),
            support_density_estimate=linkage.support_density_estimate,
            support_domain_tag=linkage.support_domain_tag,
            harmonization_confidence=linkage.harmonization_confidence,
            action_label_provenance_ref=action.provenance_ref,
            state_depth_category=state_depth_category,
            event_type=event_type,
            has_expression_features=has_expression_features,
            expression_feature_count=len(record.get("transcriptome", [])),
            outcome_present_flag=outcome_present_flag,
            output_present_flag=output_present_flag,
            output_type=(
                "transcriptomic_response" if has_expression_features and record.get("intervention_present")
                else "bulk_state_summary" if has_expression_features
                else "viability_response" if record.get("viability_measure")
                else "contextual_support" if record.get("signals")
                else None
            ),
            output_evidence_summary=record.get("output_evidence_summary"),
            action_derivation_version="rule_based_program_scoring_v3",
            action_candidate_labels=record.get("_action_candidates", [action.action_level_2]),
            action_evidence_summary=record.get("_action_evidence_summary"),
            regulatory_support_score=plausibility_fields["regulatory_support_score"],
            pathway_support_score=plausibility_fields["pathway_support_score"],
            metabolic_support_score=plausibility_fields["metabolic_support_score"],
            viability_constraint_score=plausibility_fields["viability_constraint_score"],
            overall_plausibility_score=plausibility_fields["overall_plausibility_score"],
            plausibility_support_ref=f"plausibility:{event_id}",
            plausibility_evidence_summary=plausibility_fields["plausibility_evidence_summary"],
            unsupported_action_flag=plausibility_fields["unsupported_action_flag"],
            evaluation_ready_flag=evaluation_ready_flag,
        )
        events.append(event)
        traces.append(
            EvidenceTraceRecord(
                evidence_trace_id=f"trace:{record['record_id']}:plausibility",
                cod_event_id=event_id,
                field_name="overall_plausibility_score",
                source_dataset=record["dataset"],
                source_record_pointer=record["source_record_pointer"],
                transformation_step="plausibility_scoring",
                rule_or_model="cod_plausibility_rules_v1",
                confidence=max(0.4, plausibility_fields["overall_plausibility_score"]),
                notes=plausibility_fields["plausibility_evidence_summary"],
            )
        )

        benchmark_rows.append(
            {
                "cod_event_id": event_id,
                "task_state_to_action": event.action_level_2 if event.action_level_2 and event.action_level_2 != "no_confident_action_assignment" else None,
                "task_state_intervention_to_output": event.short_horizon_output_ref if event.output_present_flag and event.intervention_present else None,
                "task_state_intervention_to_outcome": event.long_horizon_outcome_ref if event.outcome_present_flag and event.intervention_present else None,
                "task_next_step_transition": event.post_state_ref if event.output_present_flag and event.intervention_present else None,
                "task_trajectory_step_prediction": event.next_event_ref if event.trajectory_id else None,
                "task_plausibility_classification": not event.unsupported_action_flag,
                "task_action_supported_vs_unsupported": "supported" if not event.unsupported_action_flag else "unsupported",
                "held_out_cell_type_bucket": event.cell_type_label in split_spec["splits"]["held_out_cell_types"]["values"],
                "held_out_intervention_bucket": (event.intervention_target_entity or "none") in split_spec["splits"]["held_out_interventions"]["values"],
                "benchmark_state_eligible": event.has_expression_features,
                "benchmark_action_eligible": bool(event.action_level_2 and event.action_level_2 != "no_confident_action_assignment"),
                "benchmark_output_eligible": bool(event.output_present_flag and event.intervention_present),
                "benchmark_outcome_eligible": bool(event.outcome_present_flag and event.intervention_present),
                "benchmark_trajectory_eligible": bool(event.trajectory_id and event.next_event_ref),
                "benchmark_plausibility_eligible": event.overall_plausibility_score is not None,
                "state_depth_category": event.state_depth_category,
                "event_type": event.event_type,
                "evidence_tier": int(event.causal_evidence_tier),
                "source_family": event.source_family,
                "source_dataset": event.source_dataset,
                "cell_type_label": event.cell_type_label,
                "intervention_target_entity": event.intervention_target_entity,
                "measurement_pairing_status": event.measurement_pairing_status.value,
            }
        )

    assign_trajectory_metadata(events)
    for benchmark_row, event in zip(benchmark_rows, events, strict=True):
        benchmark_row["task_trajectory_step_prediction"] = event.next_event_ref if event.trajectory_id else None
        benchmark_row["benchmark_trajectory_eligible"] = bool(event.trajectory_id and event.next_event_ref)

    output_dir.mkdir(parents=True, exist_ok=True)
    dump_models(output_dir / "cod_events.jsonl", events)
    dump_models(output_dir / "evidence_trace.jsonl", traces)
    dump_models(output_dir / "transcriptome_profiles.jsonl", transcriptome)
    dump_models(output_dir / "metabolome_profiles.jsonl", metabolome)
    dump_models(output_dir / "signaling_profiles.jsonl", signaling)
    write_parquet(output_dir / "cod_events.parquet", [item.model_dump(mode="json") for item in events])
    write_parquet(output_dir / "evidence_trace.parquet", [item.model_dump(mode="json") for item in traces])
    write_jsonl(output_dir / "benchmark_rows.jsonl", benchmark_rows)
    write_jsonl(output_dir / "source_registry.jsonl", SOURCE_FAMILIES)
    write_jsonl(output_dir / "source_contracts_snapshot.jsonl", source_contracts["sources"])
    (output_dir / "source_support_matrix.json").write_text(json.dumps(load_source_support(root), indent=2, sort_keys=True), encoding="utf-8")
    summary = write_build_summary(output_dir, output_dir / "summary_stats.json")
    write_action_space_report(output_dir, output_dir / "action_space_report.json")
    write_output_space_report(output_dir, output_dir / "output_space_report.json")
    write_outcome_space_report(output_dir, output_dir / "outcome_space_report.json")
    write_trajectory_report(output_dir, output_dir / "trajectory_report.json")
    write_plausibility_report(output_dir, output_dir / "plausibility_report.json")
    write_data_quality_report(output_dir, output_dir / "data_quality_report.json")
    validate_build_consistency(output_dir, summary)
    source_manifest_bundle: list[dict[str, Any]] = []
    aggregate_artifacts: list[dict[str, Any]] = []
    raw_root = raw_dir.parent if raw_dir.name == "normalized_all" else raw_dir
    if raw_root.exists():
        for manifest_path in sorted(raw_root.glob("*/downloads/manifest.json")):
            manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            source_manifest_bundle.append(manifest_payload)
            normalized_files = sorted((manifest_path.parent.parent / "normalized").glob("*.jsonl"))
            normalized_count = 0
            for normalized_file in normalized_files:
                with normalized_file.open("r", encoding="utf-8") as handle:
                    normalized_count += sum(1 for line in handle if line.strip())
            aggregate_artifacts.append(
                {
                    "source_name": manifest_payload.get("source"),
                    "download_url": manifest_payload.get("download_url"),
                    "downloaded_at": manifest_payload.get("downloaded_at"),
                    "checksum_sha256": manifest_payload.get("checksum_sha256"),
                    "release_info": manifest_payload.get("release_info"),
                    "normalized_count": normalized_count,
                    "raw_path": str(manifest_path.parent),
                    "records_path": str(manifest_path.parent.parent / "normalized"),
                }
            )
    fetch_manifest_candidates = [
        raw_dir / "fetch_manifest.json",
        raw_dir.parent / "fetch_manifest.json",
        raw_dir.parent.parent / "fetch_manifest.json",
    ]
    for candidate in fetch_manifest_candidates:
        if candidate.exists():
            manifest_payload = json.loads(candidate.read_text(encoding="utf-8"))
            source_manifest_bundle.append(manifest_payload)
            for artifact in manifest_payload.get("artifacts", []):
                if not any(existing.get("source_name") == artifact.get("source_name") for existing in aggregate_artifacts):
                    aggregate_artifacts.append(artifact)
    if aggregate_artifacts:
        write_jsonl(output_dir / "source_manifest.jsonl", aggregate_artifacts)
        (output_dir / "source_manifest.json").write_text(
            json.dumps({"artifacts": aggregate_artifacts, "source_manifests": source_manifest_bundle}, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    create_build_manifest(
        root=root,
        output_dir=output_dir,
        source_manifests=source_manifest_bundle,
        counts={
            "events": len(events),
            "evidence_traces": len(traces),
            "transcriptome_values": len(transcriptome),
            "metabolome_values": len(metabolome),
            "signaling_values": len(signaling),
        },
        summary_stats=summary,
        fixture_or_real="fixture" if raw_dir.as_posix().startswith((root / "examples").as_posix()) else "public_subset_or_custom",
    )

    return {
        "events": len(events),
        "evidence_traces": len(traces),
        "transcriptome_values": len(transcriptome),
        "metabolome_values": len(metabolome),
        "signaling_values": len(signaling),
    }
