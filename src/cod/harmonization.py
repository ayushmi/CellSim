from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .enums import PairingStatus, SupportDomainTag


GENE_MAP = {
    "STAT1": ("HGNC:11362", "ENSG00000115415"),
    "ISG15": ("HGNC:4053", "ENSG00000187608"),
    "IL6": ("HGNC:6018", "ENSG00000136244"),
    "MKI67": ("HGNC:6204", "ENSG00000148773"),
    "LDHA": ("HGNC:6541", "ENSG00000134333"),
}

CELL_TYPE_MAP = {
    "CD8 T cell": "CL:0000625",
    "Tumor-associated macrophage": "CL:0000860",
    "Epithelial tumor cell": "CL:0000066",
}

TISSUE_MAP = {
    "lung": "UBERON:0002048",
    "blood": "UBERON:0000178",
    "colon": "UBERON:0001155",
}

DISEASE_MAP = {
    "healthy": "MONDO:0000001",
    "lung adenocarcinoma": "MONDO:0005061",
    "colorectal cancer": "MONDO:0005575",
}


@dataclass
class LinkageDecision:
    pairing_status: PairingStatus
    harmonization_confidence: float
    support_density_estimate: float
    support_domain_tag: SupportDomainTag
    modality_conflict_flag: bool


def normalize_gene_id(symbol: str) -> str:
    ids = GENE_MAP.get(symbol)
    return ids[0] if ids else f"UNMAPPED_GENE:{symbol}"


def normalize_cell_type(label: str) -> str | None:
    return CELL_TYPE_MAP.get(label)


def normalize_tissue(label: str) -> str | None:
    return TISSUE_MAP.get(label)


def normalize_disease(label: str | None) -> str | None:
    if label is None:
        return None
    return DISEASE_MAP.get(label)


def assess_linkage(record: dict[str, Any]) -> LinkageDecision:
    if record.get("source_cell_id"):
        return LinkageDecision(
            pairing_status=PairingStatus.exact_cell,
            harmonization_confidence=0.93,
            support_density_estimate=0.85,
            support_domain_tag=SupportDomainTag.in_domain,
            modality_conflict_flag=False,
        )
    if record.get("source_sample_id") and record.get("matched_modalities", 0) >= 2:
        return LinkageDecision(
            pairing_status=PairingStatus.exact_sample,
            harmonization_confidence=0.82,
            support_density_estimate=0.74,
            support_domain_tag=SupportDomainTag.in_domain,
            modality_conflict_flag=False,
        )
    return LinkageDecision(
        pairing_status=PairingStatus.probabilistic_context,
        harmonization_confidence=0.61,
        support_density_estimate=0.48,
        support_domain_tag=SupportDomainTag.near_domain,
        modality_conflict_flag=True,
    )
