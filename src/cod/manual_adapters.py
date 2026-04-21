from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pandas as pd

from .acquisition import (
    FetchArtifact,
    normalize_cellxgene_row,
    sparse_row_marker_values,
)
from .io_utils import write_jsonl


def adapt_tabula_sapiens_h5ad(
    input_h5ad: Path,
    output_path: Path,
    *,
    dataset_id: str,
    marker_genes: list[str] | None = None,
    size: int = 100,
) -> int:
    marker_genes = marker_genes or ["ALB", "KRT19", "EPCAM", "COL1A1", "DCN", "VWF", "STAT1", "IFIT1", "MKI67"]
    artifact = FetchArtifact(
        source_name="Tabula Sapiens",
        download_url=str(input_h5ad),
        downloaded_at="manual_local",
        checksum_sha256="manual_local",
        release_info=dataset_id,
        records_path=output_path,
        raw_path=input_h5ad,
        normalized_count=0,
    )
    rows = sparse_row_marker_values(input_h5ad, marker_genes, size)
    records = []
    for idx, row in enumerate(rows, start=1):
        record = normalize_cellxgene_row(row, artifact, idx, "Tabula Sapiens local adapter", dataset_id)
        record["dataset"] = "Tabula Sapiens"
        record["study_id"] = "Tabula Sapiens local adapter"
        records.append(record)
    write_jsonl(output_path, records)
    return len(records)


def adapt_roadmap_metadata(input_tsv: Path, output_path: Path, *, size: int = 100) -> int:
    df = pd.read_csv(input_tsv, sep="\t").head(size)
    records = []
    for idx, row in enumerate(df.to_dict(orient="records"), start=1):
        records.append(
            {
                "record_id": f"roadmap_local_{idx:04d}",
                "dataset": "Roadmap Epigenomics",
                "study_id": str(row.get("EID", "Roadmap_local")),
                "source_sample_id": str(row.get("EID", f"roadmap_{idx}")),
                "assay_id": str(row.get("MARK", row.get("ANATOMY", "epigenome_state"))),
                "source_record_pointer": f"{input_tsv}#row={idx}",
                "subject_id": str(row.get("EID", f"roadmap_{idx}")),
                "cell_instance_id": str(row.get("EID", f"roadmap_{idx}")),
                "species": "Homo sapiens",
                "health_status": "reference_epigenome",
                "disease_state": str(row.get("TYPE", "unknown")),
                "tissue_label": str(row.get("ANATOMY", "unknown_tissue")),
                "cell_type_label": str(row.get("SAMPLE_NAME", "unknown_cell_type")),
                "time_anchor_type": "baseline",
                "t0_timestamp": "reference_release",
                "t0_time_unit": "release",
                "has_epigenome_state": True,
                "state_representation_type": "normalized_measured",
                "measurement_support_score": 0.72,
                "signals": [{"feature_id": str(row.get("MARK", "chromatin_state")), "value": 1.0, "value_type": "binary", "support_score": 0.75}],
                "dominant_pathway": "epigenomic_reference",
            }
        )
    write_jsonl(output_path, records)
    return len(records)


def adapt_recon3d_sbml(input_sbml: Path, output_path: Path, *, size: int = 100) -> int:
    text = input_sbml.read_text(encoding="utf-8", errors="ignore")
    reaction_ids = re.findall(r'id="([^"]+)"', text)
    records = []
    for idx, reaction_id in enumerate(reaction_ids[:size], start=1):
        records.append(
            {
                "record_id": f"recon3d_local_{idx:05d}",
                "dataset": "Recon3D",
                "study_id": "Recon3D_local_adapter",
                "source_sample_id": reaction_id,
                "assay_id": "metabolic_network_model",
                "source_record_pointer": f"{input_sbml}#reaction={reaction_id}",
                "subject_id": reaction_id,
                "cell_instance_id": reaction_id,
                "species": "Homo sapiens",
                "health_status": "knowledge_model",
                "disease_state": "unknown",
                "tissue_label": "unknown_tissue",
                "cell_type_label": "unknown_cell_type",
                "time_anchor_type": "inferred",
                "t0_timestamp": "knowledge_graph",
                "t0_time_unit": "knowledge_graph",
                "state_representation_type": "inferred",
                "measurement_support_score": 0.65,
                "signals": [{"feature_id": reaction_id, "value": 1.0, "value_type": "binary", "support_score": 0.7}],
                "dominant_pathway": "metabolic_constraint_model",
            }
        )
    write_jsonl(output_path, records)
    return len(records)


def adapt_hmdb_metabolites_xml(input_xml: Path, output_path: Path, *, size: int = 100) -> int:
    records = []
    count = 0
    for _, elem in ET.iterparse(input_xml, events=("end",)):
        tag = elem.tag.split("}")[-1]
        if tag != "metabolite":
            continue
        hmdb_id = elem.findtext(".//{*}accession")
        name = elem.findtext(".//{*}name")
        if not hmdb_id or not name:
            elem.clear()
            continue
        count += 1
        records.append(
            {
                "record_id": f"hmdb_local_{count:05d}",
                "dataset": "HMDB",
                "study_id": "HMDB_local_adapter",
                "source_sample_id": hmdb_id,
                "assay_id": "metabolite_registry",
                "source_record_pointer": f"{input_xml}#metabolite={hmdb_id}",
                "subject_id": hmdb_id,
                "cell_instance_id": hmdb_id,
                "species": "Homo sapiens",
                "health_status": "registry",
                "disease_state": "unknown",
                "tissue_label": "unknown_tissue",
                "cell_type_label": "unknown_cell_type",
                "time_anchor_type": "inferred",
                "t0_timestamp": "registry_snapshot",
                "t0_time_unit": "registry_snapshot",
                "state_representation_type": "inferred",
                "measurement_support_score": 0.6,
                "signals": [{"feature_id": name, "value": 1.0, "value_type": "binary", "support_score": 0.72}],
                "dominant_pathway": "metabolite_registry_context",
            }
        )
        elem.clear()
        if count >= size:
            break
    write_jsonl(output_path, records)
    return len(records)


def adapt_kegg_local_tsv(input_tsv: Path, output_path: Path, *, size: int = 100) -> int:
    df = pd.read_csv(input_tsv, sep="\t").head(size)
    records = []
    for idx, row in enumerate(df.to_dict(orient="records"), start=1):
        pathway_id = str(row.get("pathway_id", row.get("pathway", f"kegg_{idx}")))
        pathway_name = str(row.get("pathway_name", row.get("name", pathway_id)))
        records.append(
            {
                "record_id": f"kegg_local_{idx:05d}",
                "dataset": "KEGG",
                "study_id": "KEGG_local_adapter",
                "source_sample_id": pathway_id,
                "assay_id": "pathway_registry",
                "source_record_pointer": f"{input_tsv}#row={idx}",
                "subject_id": pathway_id,
                "cell_instance_id": pathway_id,
                "species": "Homo sapiens",
                "health_status": "knowledge_graph",
                "disease_state": "unknown",
                "tissue_label": "unknown_tissue",
                "cell_type_label": "unknown_cell_type",
                "time_anchor_type": "inferred",
                "t0_timestamp": "registry_snapshot",
                "t0_time_unit": "registry_snapshot",
                "state_representation_type": "inferred",
                "measurement_support_score": 0.62,
                "signals": [{"feature_id": pathway_id, "value": 1.0, "value_type": "binary", "support_score": 0.7}],
                "dominant_pathway": pathway_name,
            }
        )
    write_jsonl(output_path, records)
    return len(records)


def adapt_ukb_tabular(input_tsv: Path, output_path: Path, *, size: int = 100) -> int:
    df = pd.read_csv(input_tsv, sep="\t").head(size)
    records = []
    for idx, row in enumerate(df.to_dict(orient="records"), start=1):
        participant_id = str(row.get("participant_id", row.get("eid", f"ukb_{idx}")))
        records.append(
            {
                "record_id": f"ukb_local_{idx:05d}",
                "dataset": "UK Biobank",
                "study_id": "UKB_local_adapter",
                "source_sample_id": participant_id,
                "assay_id": "participant_outcome",
                "source_record_pointer": f"{input_tsv}#row={idx}",
                "subject_id": participant_id,
                "cell_instance_id": participant_id,
                "species": "Homo sapiens",
                "sex": row.get("sex"),
                "age": str(row.get("age", "")) or None,
                "health_status": "observational_cohort",
                "disease_state": str(row.get("disease_state", row.get("phenotype", "unknown"))),
                "tissue_label": "whole organism",
                "cell_type_label": "participant context",
                "time_anchor_type": "diagnosis",
                "t0_timestamp": "cohort_snapshot",
                "t0_time_unit": "cohort_snapshot",
                "state_representation_type": "inferred",
                "measurement_support_score": 0.55,
                "therapy_response_label": str(row.get("therapy_response_label", "")) or None,
                "survival_proxy": str(row.get("survival_proxy", "")) or None,
                "outcome_time_horizon": str(row.get("outcome_time_horizon", "longitudinal")),
                "dominant_pathway": "cohort_outcome_adapter",
            }
        )
    write_jsonl(output_path, records)
    return len(records)


ADAPTER_FUNCTIONS: dict[str, Any] = {
    "tabula_sapiens_h5ad": adapt_tabula_sapiens_h5ad,
    "roadmap_metadata": adapt_roadmap_metadata,
    "recon3d_sbml": adapt_recon3d_sbml,
    "hmdb_metabolites_xml": adapt_hmdb_metabolites_xml,
    "kegg_local_tsv": adapt_kegg_local_tsv,
    "ukb_tabular": adapt_ukb_tabular,
}
