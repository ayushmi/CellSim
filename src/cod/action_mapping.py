from __future__ import annotations

from typing import Any

from .enums import ActionAssignmentMethod, ActionDirectionality, CausalEvidenceTier
from .models import ActionLabel, EvidenceTraceRecord


ACTION_RULE_VERSION = "rule_based_program_scoring_v3"


def _sum_markers(values: dict[str, float], genes: list[str]) -> float:
    return sum(float(values.get(gene, 0.0)) for gene in genes)


def _candidate_catalog(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    transcriptome = {item["feature_id"]: item["value"] for item in record.get("transcriptome", [])}
    secretome = {item["feature_id"]: item["value"] for item in record.get("secretome", [])}
    metabolome = {item["feature_id"]: item["value"] for item in record.get("metabolome", [])}
    pathway = str(record.get("dominant_pathway", "") or "")
    intervention_target = str(record.get("intervention_target_entity", "") or "")
    microenvironment = str(record.get("microenvironment_label", "") or "")
    cell_cycle_state = str(record.get("cell_cycle_state", "") or "")
    stress_state = str(record.get("stress_state_ref", "") or "")
    damage_state = str(record.get("damage_response_state", "") or "")
    senescence_state = str(record.get("senescence_state", "") or "")
    viability = str(record.get("viability_measure", "") or "").lower()
    proliferation = str(record.get("proliferation_measure", "") or "").lower()

    interferon_score = _sum_markers(transcriptome, ["ISG15", "STAT1", "IFIT1", "IFIT3", "CXCL10"])
    inflammatory_score = _sum_markers(transcriptome, ["IL6", "TNF", "NFKBIA", "CXCL8"])
    proliferation_score = _sum_markers(transcriptome, ["MKI67", "TOP2A", "PCNA"])
    stress_score = _sum_markers(transcriptome, ["DDIT3", "ATF4", "HSPA1A", "HSPB1", "JUN"])
    apoptosis_score = _sum_markers(transcriptome, ["BAX", "BBC3", "CASP3", "CASP8", "FAS"])
    dna_damage_score = _sum_markers(transcriptome, ["GADD45A", "CDKN1A", "RAD51", "DDB2", "ATM"])
    metabolic_shift_score = _sum_markers(transcriptome, ["LDHA", "SLC2A1", "PGK1", "ENO1"])
    differentiation_score = _sum_markers(transcriptome, ["ALB", "KRT19", "EPCAM", "COL1A1", "DCN"])
    migration_score = _sum_markers(transcriptome, ["VIM", "ITGB1", "CXCR4", "MMP9", "COL1A1"])
    quiescence_score = _sum_markers(transcriptome, ["CDKN1B", "TXNIP", "FOXO1", "KLF2"])

    return {
        "activate_interferon_program": {
            "score": interferon_score + (0.7 if "ifn" in pathway.lower() else 0.0),
            "action_id": "ACT_SIGNALING_IFN_RESPONSE",
            "level_0": "signaling",
            "level_1": "cytokine_response",
            "directionality": ActionDirectionality.activate,
            "zone": "B",
            "confidence_floor": 0.72,
            "evidence_tier": CausalEvidenceTier.perturbational_causal if record.get("intervention_present") else CausalEvidenceTier.association,
        },
        "activate_inflammatory_cytokine_program": {
            "score": inflammatory_score + float(secretome.get("IL6", 0.0)) + (0.6 if "nfkb" in pathway.lower() else 0.0),
            "action_id": "ACT_SIGNALING_NFKB_IL6",
            "level_0": "signaling",
            "level_1": "inflammatory_program",
            "directionality": ActionDirectionality.activate,
            "zone": "B",
            "confidence_floor": 0.7,
            "evidence_tier": CausalEvidenceTier.perturbational_causal if record.get("intervention_present") else CausalEvidenceTier.association,
        },
        "enter_cell_cycle_or_proliferation_program": {
            "score": proliferation_score + (0.4 if "cycling" in cell_cycle_state.lower() else 0.0) + (0.3 if "prolif" in proliferation else 0.0),
            "action_id": "ACT_FATE_PROLIFERATION",
            "level_0": "fate",
            "level_1": "cell_cycle",
            "directionality": ActionDirectionality.enter,
            "zone": "F",
            "confidence_floor": 0.68,
            "evidence_tier": CausalEvidenceTier.association,
        },
        "activate_stress_response_program": {
            "score": stress_score + (0.6 if stress_state else 0.0),
            "action_id": "ACT_MAINTENANCE_STRESS",
            "level_0": "maintenance",
            "level_1": "stress_response",
            "directionality": ActionDirectionality.activate,
            "zone": "G",
            "confidence_floor": 0.66,
            "evidence_tier": CausalEvidenceTier.association,
        },
        "activate_apoptosis_or_cell_death_program": {
            "score": apoptosis_score + (0.5 if any(token in viability for token in ["death", "apopt", "low"]) else 0.0),
            "action_id": "ACT_MAINTENANCE_APOPTOSIS",
            "level_0": "maintenance",
            "level_1": "quality_control",
            "directionality": ActionDirectionality.activate,
            "zone": "G",
            "confidence_floor": 0.7,
            "evidence_tier": CausalEvidenceTier.association,
        },
        "activate_dna_damage_or_repair_program": {
            "score": dna_damage_score + (0.6 if damage_state else 0.0),
            "action_id": "ACT_MAINTENANCE_DNA_REPAIR",
            "level_0": "maintenance",
            "level_1": "genome_integrity",
            "directionality": ActionDirectionality.activate,
            "zone": "G",
            "confidence_floor": 0.67,
            "evidence_tier": CausalEvidenceTier.association,
        },
        "activate_metabolic_shift_program": {
            "score": metabolic_shift_score + float(metabolome.get("lactate", 0.0)) + (0.6 if "glycolysis" in pathway.lower() else 0.0),
            "action_id": "ACT_METABOLIC_SHIFT",
            "level_0": "metabolic",
            "level_1": "energy_program",
            "directionality": ActionDirectionality.switch,
            "zone": "C",
            "confidence_floor": 0.67,
            "evidence_tier": CausalEvidenceTier.association,
        },
        "activate_differentiation_or_lineage_commitment_program": {
            "score": differentiation_score + (0.4 if intervention_target in {"CEBPA", "GATA3", "STAT3"} else 0.0),
            "action_id": "ACT_FATE_DIFFERENTIATION",
            "level_0": "fate",
            "level_1": "lineage_commitment",
            "directionality": ActionDirectionality.switch,
            "zone": "F",
            "confidence_floor": 0.65,
            "evidence_tier": CausalEvidenceTier.association,
        },
        "activate_migration_or_adhesion_program": {
            "score": migration_score + (0.4 if any(token in microenvironment.lower() for token in ["strom", "matrix", "vascular"]) else 0.0),
            "action_id": "ACT_BEHAVIOR_MIGRATION",
            "level_0": "behavior",
            "level_1": "motility",
            "directionality": ActionDirectionality.activate,
            "zone": "D",
            "confidence_floor": 0.64,
            "evidence_tier": CausalEvidenceTier.association,
        },
        "enter_quiescence_program": {
            "score": quiescence_score + (0.5 if senescence_state else 0.0) + (0.3 if "quies" in cell_cycle_state.lower() else 0.0),
            "action_id": "ACT_FATE_QUIESCENCE",
            "level_0": "fate",
            "level_1": "dormancy",
            "directionality": ActionDirectionality.enter,
            "zone": "F",
            "confidence_floor": 0.63,
            "evidence_tier": CausalEvidenceTier.association,
        },
        "maintain_homeostatic_program": {
            "score": 0.55,
            "action_id": "ACT_REGULATORY_HOMEOSTASIS",
            "level_0": "regulatory",
            "level_1": "homeostatic_control",
            "directionality": ActionDirectionality.maintain,
            "zone": "A",
            "confidence_floor": 0.58,
            "evidence_tier": CausalEvidenceTier.descriptive_observation,
        },
    }


def infer_action_candidates(record: dict[str, Any], scored_candidates: list[tuple[str, float]]) -> list[str]:
    supported = [label for label, score in scored_candidates if score >= 1.0]
    if not supported:
        return ["no_confident_action_assignment", "maintain_homeostatic_program"]
    return supported[:4]


def infer_action(record: dict[str, Any]) -> tuple[ActionLabel, list[EvidenceTraceRecord]]:
    dataset = record["dataset"]
    base_id = record["record_id"]
    pathway = str(record.get("dominant_pathway", "") or "")
    transcriptome = {item["feature_id"]: item["value"] for item in record.get("transcriptome", [])}

    catalog = _candidate_catalog(record)
    scored_candidates = sorted(
        ((label, round(float(payload["score"]), 4)) for label, payload in catalog.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    has_direct_signal = bool(record.get("transcriptome") or record.get("metabolome") or record.get("secretome"))
    if not has_direct_signal and record.get("dataset") in {"OmniPath", "ENCODE", "Reactome", "TRRUST", "BioModels", "Recon3D", "KEGG"}:
        scored_candidates.insert(0, ("no_confident_action_assignment", 1.2))
    best_label, best_score = scored_candidates[0]
    if best_label == "maintain_homeostatic_program" and len(scored_candidates) > 1 and scored_candidates[1][1] >= 0.9:
        best_label, best_score = scored_candidates[1]
    candidates = infer_action_candidates(record, scored_candidates)

    if best_label == "no_confident_action_assignment":
        action = ActionLabel(
            action_id="ACT_NO_CONFIDENT_ASSIGNMENT",
            action_level_0="abstain",
            action_level_1="insufficient_direct_state",
            action_level_2="no_confident_action_assignment",
            action_primary=True,
            intensity_score=0.0,
            directionality=ActionDirectionality.maintain,
            zone="Z",
            confidence_score=0.35,
            assignment_method=ActionAssignmentMethod.weak_supervision,
            evidence_tier=CausalEvidenceTier.descriptive_observation,
            provenance_ref=f"trace:{base_id}:action",
        )
    else:
        best_payload = catalog[best_label]
        confidence = min(0.95, max(best_payload["confidence_floor"], 0.48 + 0.12 * best_score))
        action = ActionLabel(
            action_id=best_payload["action_id"],
            action_level_0=best_payload["level_0"],
            action_level_1=best_payload["level_1"],
            action_level_2=best_label,
            action_primary=True,
            intensity_score=min(0.95, 0.45 + 0.1 * best_score),
            directionality=best_payload["directionality"],
            zone=best_payload["zone"],
            confidence_score=confidence,
            assignment_method=ActionAssignmentMethod.weak_supervision,
            evidence_tier=best_payload["evidence_tier"],
            provenance_ref=f"trace:{base_id}:action",
        )

    transcriptome_markers = sorted([feature_id for feature_id, value in transcriptome.items() if float(value) > 0.0])
    score_summary = ", ".join(f"{label}={score:.2f}" for label, score in scored_candidates[:5])
    traces = [
        EvidenceTraceRecord(
            evidence_trace_id=f"trace:{base_id}:action",
            field_name="action_level_2",
            source_dataset=dataset,
            source_record_pointer=record["source_record_pointer"],
            transformation_step="action_mapping",
            rule_or_model=ACTION_RULE_VERSION,
            confidence=action.confidence_score,
            notes=f"pathway={pathway}; top_scores={score_summary}; candidates={candidates}",
        )
    ]
    record["_action_candidates"] = candidates
    record["_action_evidence_summary"] = (
        f"weak_label_rule_version={ACTION_RULE_VERSION}; pathway={pathway}; "
        f"transcriptome_markers={transcriptome_markers}; top_scores={score_summary}"
    )
    return action, traces
