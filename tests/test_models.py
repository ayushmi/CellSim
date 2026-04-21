import pytest

from cod.enums import CausalEvidenceTier, PairingStatus
from cod.models import CellTransitionEvent


def test_cte_model_requires_core_fields() -> None:
    event = CellTransitionEvent(
        cod_event_id="COD_CTE_TEST",
        cod_subject_id="SUBJ-TEST",
        cod_cell_instance_id="CELL-TEST",
        cod_batch_id="batch",
        cod_release_version="0.1.0",
        source_dataset="Human Cell Atlas",
        source_study_id="STUDY",
        source_sample_id="SAMPLE",
        source_assay_id="scRNA-seq",
        source_record_pointer="raw#1",
        processing_pipeline_version="v1",
        evidence_trace_id="trace:1",
        license_class="research_restricted",
        species="Homo sapiens",
        tissue_label="lung",
        cell_type_label="CD8 T cell",
        time_anchor_type="baseline",
        t0_timestamp="0",
        t0_time_unit="hours",
        intervention_present=False,
        intervention_type="none",
        action_level_0="regulatory",
        action_level_1="homeostatic_control",
        action_level_2="maintain_homeostatic_program",
        action_label_set_ref="actionset:1",
        action_primary_label="maintain_homeostatic_program",
        action_intensity_score=0.5,
        action_directionality="maintain",
        action_zone="A",
        action_confidence_score=0.6,
        action_assignment_method="weak_supervision",
    )

    assert event.causal_evidence_tier == CausalEvidenceTier.descriptive_observation
    assert event.measurement_pairing_status == PairingStatus.unpaired


def test_cte_model_rejects_outcome_flag_without_outcome_fields() -> None:
    with pytest.raises(ValueError, match="outcome_present_flag=True"):
        CellTransitionEvent(
            cod_event_id="COD_CTE_BAD",
            cod_subject_id="SUBJ-TEST",
            cod_cell_instance_id="CELL-TEST",
            cod_batch_id="batch",
            cod_release_version="0.1.0",
            source_dataset="Human Cell Atlas",
            source_study_id="STUDY",
            source_sample_id="SAMPLE",
            source_assay_id="scRNA-seq",
            source_record_pointer="raw#1",
            processing_pipeline_version="v1",
            evidence_trace_id="trace:1",
            license_class="research_restricted",
            species="Homo sapiens",
            tissue_label="lung",
            cell_type_label="CD8 T cell",
            time_anchor_type="baseline",
            t0_timestamp="0",
            t0_time_unit="hours",
            intervention_present=False,
            intervention_type="none",
            action_level_0="regulatory",
            action_level_1="homeostatic_control",
            action_level_2="maintain_homeostatic_program",
            action_label_set_ref="actionset:1",
            action_primary_label="maintain_homeostatic_program",
            action_intensity_score=0.5,
            action_directionality="maintain",
            action_zone="A",
            action_confidence_score=0.6,
            action_assignment_method="weak_supervision",
            outcome_present_flag=True,
        )
