from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ConfigDict, model_validator

from .enums import (
    ActionAssignmentMethod,
    ActionDirectionality,
    CausalEvidenceTier,
    InterventionDirection,
    InterventionType,
    PairingStatus,
    StateRepresentationType,
    SupportDomainTag,
    TimeAnchorType,
)


class EvidenceTraceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_trace_id: str
    cod_event_id: str | None = None
    field_name: str
    source_dataset: str
    source_record_pointer: str
    transformation_step: str
    rule_or_model: str
    reviewer: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str | None = None


class ActionLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str
    action_level_0: str
    action_level_1: str
    action_level_2: str
    action_primary: bool = False
    intensity_score: float = Field(ge=0.0, le=1.0)
    directionality: ActionDirectionality
    zone: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    assignment_method: ActionAssignmentMethod
    evidence_tier: CausalEvidenceTier
    provenance_ref: str


class FeatureValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_ref: str
    feature_space_id: str
    feature_id: str
    feature_name: str | None = None
    value: float
    unit: str | None = None
    value_type: Literal["abundance", "activity", "score", "log_fc", "binary", "probability"] = "abundance"
    support_score: float = Field(default=1.0, ge=0.0, le=1.0)
    provenance_ref: str


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_family: str
    dataset_name: str
    raw_id_field: str
    required_fields: list[str]
    optional_fields: list[str]
    output_entities: list[str]
    granularity: str
    time_support: str
    intervention_support: str
    pairing_support: str
    implemented: bool


class CellTransitionEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cod_event_id: str
    cod_subject_id: str
    cod_cell_instance_id: str
    cod_parent_event_id: str | None = None
    cod_batch_id: str
    cod_release_version: str

    source_dataset: str
    source_family: str | None = None
    source_study_id: str
    source_sample_id: str
    source_cell_id: str | None = None
    source_assay_id: str
    source_record_pointer: str
    source_accession: str | None = None
    source_download_url: str | None = None
    source_downloaded_at: str | None = None
    source_checksum: str | None = None
    source_release_info: str | None = None
    processing_pipeline_version: str
    evidence_trace_id: str
    license_class: str
    record_origin_type: str = "fixture"

    species: str
    donor_id_normalized: str | None = None
    sex: str | None = None
    age: str | None = None
    ancestry: str | None = None
    health_status: str | None = None
    disease_state: str | None = None
    disease_ontology_id: str | None = None
    tissue_label: str
    uberon_id: str | None = None
    cell_type_label: str
    cell_ontology_id: str | None = None
    developmental_stage: str | None = None
    microenvironment_label: str | None = None
    spatial_region_label: str | None = None

    time_anchor_type: TimeAnchorType
    t0_timestamp: str
    t0_time_unit: str
    delta_t_to_output: str | None = None
    delta_t_to_outcome: str | None = None
    trajectory_group_id: str | None = None
    previous_event_ref: str | None = None
    next_event_ref: str | None = None
    trajectory_id: str | None = None
    trajectory_position: int | None = Field(default=None, ge=0)
    trajectory_length: int | None = Field(default=None, ge=1)
    trajectory_class: Literal["none", "single_step_transition", "short_chain", "longitudinal_chain", "pseudo_trajectory"] = "none"
    exact_vs_inferred_trajectory_flag: bool | None = None
    time_uncertainty_score: float = Field(default=0.0, ge=0.0, le=1.0)

    intervention_present: bool
    intervention_type: InterventionType
    intervention_target_entity: str | None = None
    intervention_target_id: str | None = None
    intervention_direction: InterventionDirection = InterventionDirection.none
    intervention_dose: str | None = None
    intervention_dose_unit: str | None = None
    intervention_duration: str | None = None
    intervention_delivery_mode: str | None = None
    intervention_combo_id: str | None = None
    control_definition: str | None = None

    has_genome_state: bool = False
    has_epigenome_state: bool = False
    has_transcriptome_state: bool = False
    has_proteome_state: bool = False
    has_phosphoproteome_state: bool = False
    has_metabolome_state: bool = False
    has_spatial_state: bool = False
    has_neighbor_context: bool = False
    has_clinical_context: bool = False
    has_time_series_context: bool = False

    genome_profile_ref: str | None = None
    epigenome_profile_ref: str | None = None
    transcriptome_profile_ref: str | None = None
    proteome_profile_ref: str | None = None
    phosphoproteome_profile_ref: str | None = None
    metabolome_profile_ref: str | None = None
    spatial_profile_ref: str | None = None
    neighbor_profile_ref: str | None = None
    state_embedding_ref: str | None = None
    state_summary_ref: str | None = None

    external_signal_set_ref: str | None = None
    resource_state_ref: str | None = None
    stress_state_ref: str | None = None
    cell_cycle_state: str | None = None
    mitochondrial_state: str | None = None
    damage_response_state: str | None = None
    senescence_state: str | None = None
    immune_context_ref: str | None = None
    constraint_profile_ref: str | None = None
    pre_state_ref: str | None = None
    post_state_ref: str | None = None
    intervention_ref: str | None = None
    constraint_refs: list[str] = Field(default_factory=list)
    reward_context_ref: str | None = None
    measured_state_flag: bool = False
    harmonized_state_flag: bool = False
    inferred_state_flag: bool = False
    probabilistic_linkage_flag: bool = False

    action_level_0: str
    action_level_1: str
    action_level_2: str
    action_label_set_ref: str
    action_primary_label: str
    action_intensity_score: float = Field(ge=0.0, le=1.0)
    action_directionality: ActionDirectionality
    action_zone: str
    action_confidence_score: float = Field(ge=0.0, le=1.0)
    action_assignment_method: ActionAssignmentMethod

    short_horizon_output_ref: str | None = None
    differential_expression_signature_ref: str | None = None
    differential_protein_signature_ref: str | None = None
    differential_metabolite_signature_ref: str | None = None
    secretome_signature_ref: str | None = None
    morphology_signature_ref: str | None = None
    viability_measure: str | None = None
    proliferation_measure: str | None = None
    output_confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    output_ref: str | None = None
    output_horizon_type: Literal["short_horizon", "medium_horizon", "long_horizon", "unavailable"] = "unavailable"

    long_horizon_outcome_ref: str | None = None
    outcome_ref: str | None = None
    fate_outcome_label: str | None = None
    tissue_outcome_label: str | None = None
    therapy_response_label: str | None = None
    disease_progression_label: str | None = None
    survival_proxy: str | None = None
    outcome_time_horizon: str | None = None
    outcome_horizon_type: Literal["short_horizon", "medium_horizon", "long_horizon", "unavailable"] = "unavailable"
    proxy_outcome_flag: bool = False
    outcome_proxy_type: str | None = None
    outcome_confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)

    reward_context_label: str | None = None
    candidate_reward_variables_ref: str | None = None
    fitness_proxy_score: float | None = Field(default=None, ge=0.0, le=1.0)
    homeostasis_proxy_score: float | None = Field(default=None, ge=0.0, le=1.0)
    immune_function_proxy_score: float | None = Field(default=None, ge=0.0, le=1.0)
    reward_inference_method: str | None = None

    raw_qc_score: float = Field(default=1.0, ge=0.0, le=1.0)
    harmonization_qc_score: float = Field(default=1.0, ge=0.0, le=1.0)
    batch_correction_flag: bool = False
    imputation_flag: bool = False
    deconvolution_flag: bool = False
    modality_conflict_flag: bool = False
    manual_review_flag: bool = False
    exclusion_reason: str | None = None

    state_representation_type: StateRepresentationType = StateRepresentationType.harmonized
    assay_distortion_notes_ref: str | None = None
    measurement_support_score: float = Field(default=1.0, ge=0.0, le=1.0)

    causal_evidence_tier: CausalEvidenceTier = CausalEvidenceTier.descriptive_observation
    causal_support_ref: str | None = None
    replication_count: int = Field(default=0, ge=0)
    mechanistic_support_score: float = Field(default=0.0, ge=0.0, le=1.0)

    prediction_support_score: float = Field(default=1.0, ge=0.0, le=1.0)
    ood_flag: bool = False
    abstention_recommended_flag: bool = False
    uncertainty_vector_ref: str | None = None

    measurement_pairing_status: PairingStatus = PairingStatus.unpaired
    temporal_completeness_flag: bool = False
    intervention_completeness_flag: bool = False
    support_density_estimate: float = Field(default=0.0, ge=0.0, le=1.0)
    support_domain_tag: SupportDomainTag = SupportDomainTag.in_domain
    harmonization_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    action_label_provenance_ref: str | None = None
    state_depth_category: Literal[
        "metadata_only",
        "context_only",
        "weak_state_bearing",
        "state_bearing",
        "transition_bearing",
        "outcome_bearing",
    ] = "metadata_only"
    event_type: Literal[
        "metadata_event",
        "context_event",
        "state_event",
        "transition_event",
        "knowledge_support_event",
        "outcome_event",
        "outcome_support_event",
        "composite_event",
    ] = "metadata_event"
    has_expression_features: bool = False
    expression_feature_count: int = Field(default=0, ge=0)
    outcome_present_flag: bool = False
    output_present_flag: bool = False
    output_type: str | None = None
    output_evidence_summary: str | None = None
    action_derivation_version: str | None = None
    action_candidate_labels: list[str] = Field(default_factory=list)
    action_evidence_summary: str | None = None
    regulatory_support_score: float | None = Field(default=None, ge=0.0, le=1.0)
    pathway_support_score: float | None = Field(default=None, ge=0.0, le=1.0)
    metabolic_support_score: float | None = Field(default=None, ge=0.0, le=1.0)
    viability_constraint_score: float | None = Field(default=None, ge=0.0, le=1.0)
    overall_plausibility_score: float | None = Field(default=None, ge=0.0, le=1.0)
    plausibility_support_ref: str | None = None
    plausibility_evidence_summary: str | None = None
    unsupported_action_flag: bool = False
    evaluation_ready_flag: bool = False

    @model_validator(mode="after")
    def validate_internal_consistency(self) -> "CellTransitionEvent":
        if self.has_expression_features and self.expression_feature_count <= 0:
            raise ValueError("has_expression_features=True requires expression_feature_count > 0")
        if not self.has_expression_features and self.expression_feature_count != 0:
            raise ValueError("expression_feature_count must be 0 when has_expression_features=False")
        if self.outcome_present_flag and not any(
            [
                self.fate_outcome_label,
                self.tissue_outcome_label,
                self.therapy_response_label,
                self.disease_progression_label,
                self.survival_proxy,
                self.long_horizon_outcome_ref,
                self.outcome_ref,
            ]
        ):
            raise ValueError("outcome_present_flag=True requires at least one outcome field")
        if not self.outcome_present_flag and self.long_horizon_outcome_ref is not None:
            raise ValueError("long_horizon_outcome_ref requires outcome_present_flag=True")
        if self.output_present_flag and not any(
            [
                self.short_horizon_output_ref,
                self.output_ref,
                self.differential_expression_signature_ref,
                self.differential_protein_signature_ref,
                self.differential_metabolite_signature_ref,
                self.secretome_signature_ref,
                self.morphology_signature_ref,
                self.viability_measure,
                self.proliferation_measure,
            ]
        ):
            raise ValueError("output_present_flag=True requires at least one output field")
        if self.state_representation_type == StateRepresentationType.inferred and self.measurement_pairing_status.value == "exact_cell":
            raise ValueError("inferred state representations cannot claim exact_cell pairing")
        if self.measured_state_flag and self.inferred_state_flag:
            raise ValueError("measured_state_flag and inferred_state_flag cannot both be true")
        if self.event_type == "transition_event" and self.state_depth_category != "transition_bearing":
            raise ValueError("transition_event requires transition_bearing state depth")
        if self.event_type == "state_event" and self.state_depth_category not in {"weak_state_bearing", "state_bearing"}:
            raise ValueError("state_event requires weak_state_bearing or state_bearing depth")
        if self.event_type == "knowledge_support_event" and self.state_depth_category != "context_only":
            raise ValueError("knowledge_support_event requires context_only state depth")
        if self.event_type in {"outcome_event", "outcome_support_event"} and self.state_depth_category != "outcome_bearing":
            raise ValueError("outcome_event requires outcome_bearing state depth")
        if self.event_type == "composite_event" and not any([self.constraint_refs, self.external_signal_set_ref, self.resource_state_ref]):
            raise ValueError("composite_event requires fused or contextual support refs")
        if self.proxy_outcome_flag and not self.outcome_present_flag:
            raise ValueError("proxy_outcome_flag requires outcome_present_flag=True")
        if self.trajectory_class != "none" and (self.trajectory_id is None or self.trajectory_length is None):
            raise ValueError("trajectory metadata requires trajectory_id and trajectory_length")
        if self.output_present_flag and self.output_horizon_type == "unavailable":
            raise ValueError("output_present_flag=True requires output_horizon_type")
        if self.outcome_present_flag and self.outcome_horizon_type == "unavailable":
            raise ValueError("outcome_present_flag=True requires outcome_horizon_type")
        return self
