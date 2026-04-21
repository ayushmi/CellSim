from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import re
import shutil
import tarfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd
import h5py
import yaml

from .io_utils import write_jsonl


UNKNOWN_CELL_TYPE = "unknown_cell_type"
UNKNOWN_TISSUE = "unknown_tissue"


@dataclass
class FetchArtifact:
    source_name: str
    download_url: str
    downloaded_at: str
    checksum_sha256: str
    release_info: str | None
    records_path: Path
    raw_path: Path
    normalized_count: int


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_get_bytes(url: str, headers: dict[str, str] | None = None) -> bytes:
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=60) as response:
        return response.read()


def fetch_post_bytes(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> bytes:
    merged_headers = {"Content-Type": "application/json"}
    merged_headers.update(headers or {})
    request = Request(url, data=json.dumps(payload).encode("utf-8"), headers=merged_headers)
    with urlopen(request, timeout=60) as response:
        return response.read()


def download_to_path(url: str, path: Path, headers: dict[str, str] | None = None) -> str:
    request = Request(url, headers=headers or {})
    hasher = hashlib.sha256()
    with urlopen(request, timeout=120) as response, path.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
            handle.write(chunk)
    return hasher.hexdigest()


def ensure_dirs(base_dir: Path, name: str) -> tuple[Path, Path]:
    raw_dir = base_dir / name / "downloads"
    normalized_dir = base_dir / name / "normalized"
    raw_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir.mkdir(parents=True, exist_ok=True)
    return raw_dir, normalized_dir


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def base_manifest(
    *,
    source: str,
    source_family: str,
    download_url: str,
    downloaded_at: str,
    checksum_sha256: str,
    release_info: str | None,
    access_notes: str,
    payload_type: str,
    transformation_manifest: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": "0.2.0",
        "source": source,
        "source_family": source_family,
        "download_url": download_url,
        "downloaded_at": downloaded_at,
        "checksum_sha256": checksum_sha256,
        "release_info": release_info,
        "payload_type": payload_type,
        "access_notes": access_notes,
        "transformation_manifest": transformation_manifest,
    }


def normalize_hca_record(hit: dict[str, Any], artifact: FetchArtifact, idx: int) -> dict[str, Any]:
    project = hit["projects"][0]
    sample = hit["samples"][0]
    donor = hit.get("donorOrganisms", [{}])[0]
    age = donor.get("organismAge", [{}])[0]
    cell_suspension = hit.get("cellSuspensions", [{}])[0]
    selected_cell_type = cell_suspension.get("selectedCellType", [None])[0]
    return {
        "record_id": f"hca_real_{idx:03d}",
        "dataset": "Human Cell Atlas",
        "study_id": project["projectId"][0],
        "source_sample_id": sample["id"],
        "source_cell_id": None,
        "assay_id": hit.get("protocols", [{}])[1].get("libraryConstructionApproach", ["unknown_assay"])[0] if len(hit.get("protocols", [])) > 1 else "unknown_assay",
        "source_record_pointer": f"{artifact.download_url}#entryId={hit['entryId']}",
        "source_accession": project["projectId"][0],
        "source_download_url": artifact.download_url,
        "source_downloaded_at": artifact.downloaded_at,
        "source_checksum": artifact.checksum_sha256,
        "source_release_info": artifact.release_info,
        "subject_id": donor.get("id", ["unknown_donor"])[0],
        "cell_instance_id": hit["entryId"],
        "species": donor.get("genusSpecies", ["Homo sapiens"])[0],
        "sex": donor.get("biologicalSex", [None])[0],
        "age": f"{age.get('value')} {age.get('unit')}" if age else None,
        "health_status": "healthy" if donor.get("disease", ["normal"])[0] == "normal" else "diseased",
        "disease_state": donor.get("disease", ["unknown"])[0],
        "tissue_label": sample.get("effectiveOrgan") or sample.get("organ") or UNKNOWN_TISSUE,
        "cell_type_label": selected_cell_type or UNKNOWN_CELL_TYPE,
        "developmental_stage": donor.get("developmentStage", [None])[0],
        "time_anchor_type": "baseline",
        "t0_timestamp": hit.get("dates", [{}])[0].get("submissionDate", "unknown"),
        "t0_time_unit": "timestamp",
        "state_representation_type": "normalized_measured",
        "matched_modalities": 1,
        "license_class": "cc_by_4_0",
        "measurement_support_score": 0.72,
    }


def fetch_hca_subset(base_dir: Path, cfg: dict[str, Any]) -> FetchArtifact:
    raw_dir, normalized_dir = ensure_dirs(base_dir, "hca")
    filters = json.dumps({"organ": {"is": [cfg["organ"]]}})
    url = f"https://service.azul.data.humancellatlas.org/index/samples?{urlencode({'catalog': cfg['catalog'], 'size': cfg['size'], 'filters': filters})}"
    payload_bytes = fetch_get_bytes(url)
    checksum = sha256_bytes(payload_bytes)
    downloaded_at = now_iso()
    raw_path = raw_dir / "samples_response.json"
    raw_path.write_bytes(payload_bytes)
    obj = json.loads(payload_bytes.decode("utf-8"))
    artifact = FetchArtifact("Human Cell Atlas", url, downloaded_at, checksum, f"catalog={cfg['catalog']}", normalized_dir / "hca_real_records.jsonl", raw_path, 0)
    records = [normalize_hca_record(hit, artifact, idx) for idx, hit in enumerate(obj["hits"][: cfg["size"]], start=1)]
    write_jsonl(artifact.records_path, records)
    artifact.normalized_count = len(records)
    write_manifest(
        raw_dir / "manifest.json",
        base_manifest(
            source=artifact.source_name,
            source_family="baseline_state",
            download_url=artifact.download_url,
            downloaded_at=artifact.downloaded_at,
            checksum_sha256=artifact.checksum_sha256,
            release_info=artifact.release_info,
            access_notes="Public HCA metadata API access. This path does not yet fetch full matrices.",
            payload_type="sample_metadata",
            transformation_manifest=["fetch_hca_subset", "normalize_hca_record"],
        )
        | {"notes": "HCA sample-level metadata only; cell type may be unavailable and remains unknown where not exposed by API."},
    )
    return artifact


def read_h5ad_categorical(group: h5py.Group) -> list[str]:
    categories = [x.decode("utf-8") if isinstance(x, bytes) else str(x) for x in group["categories"][:]]
    codes = group["codes"][:]
    return [categories[code] if code >= 0 else "unknown" for code in codes]


def read_h5ad_vector(node: h5py.Dataset | h5py.Group) -> list[str]:
    if isinstance(node, h5py.Group):
        return read_h5ad_categorical(node)
    return [x.decode("utf-8") if isinstance(x, bytes) else str(x) for x in node[:]]


def sparse_row_marker_values(h5_path: Path, marker_genes: list[str], limit: int) -> list[dict[str, Any]]:
    with h5py.File(h5_path, "r") as f:
        obs = f["obs"]
        var = f["var"]
        obs_index = read_h5ad_vector(obs["_index"])
        cell_type = read_h5ad_vector(obs["cell_type"]) if "cell_type" in obs else ["unknown"] * len(obs_index)
        tissue = read_h5ad_vector(obs["tissue"]) if "tissue" in obs else ["unknown"] * len(obs_index)
        disease = read_h5ad_vector(obs["disease"]) if "disease" in obs else ["unknown"] * len(obs_index)
        assay = read_h5ad_vector(obs["assay"]) if "assay" in obs else ["unknown"] * len(obs_index)
        feature_names = read_h5ad_vector(var["feature_name"])
        X = f["X"]
        data = X["data"][:]
        indices = X["indices"][:]
        indptr = X["indptr"][:]
        spatial = f["obsm"]["spatial"][:] if "obsm" in f and "spatial" in f["obsm"] else None

        rows: list[dict[str, Any]] = []
        for i in range(min(limit, len(obs_index))):
            start = indptr[i]
            end = indptr[i + 1]
            row_indices = indices[start:end]
            row_data = data[start:end]
            value_map = {feature_names[idx]: float(val) for idx, val in zip(row_indices, row_data) if feature_names[idx] in marker_genes}
            transcriptome = [
                {"feature_id": gene, "value": round(value, 4), "value_type": "abundance", "support_score": 0.94}
                for gene, value in value_map.items()
                if value > 0
            ]
            row = {
                "barcode": obs_index[i],
                "cell_type": cell_type[i],
                "tissue": tissue[i],
                "disease": disease[i],
                "assay": assay[i],
                "transcriptome": transcriptome,
            }
            if spatial is not None:
                row["spatial"] = [float(spatial[i][0]), float(spatial[i][1])]
            rows.append(row)
        return rows


def infer_cellxgene_pathway(transcriptome: list[dict[str, Any]]) -> str:
    values = {row["feature_id"]: row["value"] for row in transcriptome}
    inflammatory = sum(values.get(g, 0.0) for g in ["IL6", "CXCL8", "TNF", "NFKBIA"])
    epithelial = sum(values.get(g, 0.0) for g in ["EPCAM", "KRT19", "KRT8"])
    stromal = sum(values.get(g, 0.0) for g in ["COL1A1", "COL1A2", "DCN"])
    endothelial = sum(values.get(g, 0.0) for g in ["VWF", "KDR", "EMCN"])
    if inflammatory > max(epithelial, stromal, endothelial) and inflammatory > 0:
        return "NFkB_IL6"
    if endothelial > 0:
        return "vascular_homeostasis"
    if stromal > 0:
        return "matrix_program"
    if epithelial > 0:
        return "epithelial_secretory"
    return "atlas_baseline_state"


def normalize_cellxgene_row(
    row: dict[str, Any],
    artifact: FetchArtifact,
    idx: int,
    collection_name: str,
    dataset_id: str,
) -> dict[str, Any]:
    payload = {
        "record_id": f"cellxgene_real_{idx:05d}",
        "dataset": "CELLxGENE",
        "study_id": collection_name,
        "source_sample_id": dataset_id,
        "source_cell_id": row["barcode"],
        "assay_id": row["assay"],
        "source_record_pointer": f"{artifact.download_url}#cell={row['barcode']}",
        "source_accession": dataset_id,
        "source_download_url": artifact.download_url,
        "source_downloaded_at": artifact.downloaded_at,
        "source_checksum": artifact.checksum_sha256,
        "source_release_info": artifact.release_info,
        "subject_id": dataset_id,
        "cell_instance_id": row["barcode"],
        "species": "Homo sapiens",
        "health_status": "healthy" if row["disease"] == "normal" else "diseased",
        "disease_state": row["disease"],
        "tissue_label": row["tissue"],
        "cell_type_label": row["cell_type"],
        "time_anchor_type": "baseline",
        "t0_timestamp": "collection_snapshot",
        "t0_time_unit": "collection_snapshot",
        "state_representation_type": "raw_measured",
        "matched_modalities": 1,
        "license_class": "cellxgene_public",
        "measurement_support_score": 0.88,
        "transcriptome": row["transcriptome"],
        "dominant_pathway": infer_cellxgene_pathway(row["transcriptome"]),
    }
    if row.get("spatial"):
        payload["spatial_region_label"] = f"spatial_x_{row['spatial'][0]:.1f}_y_{row['spatial'][1]:.1f}"
        payload["has_spatial_state"] = True
    return payload


def fetch_cellxgene_subset(base_dir: Path, cfg: dict[str, Any]) -> FetchArtifact:
    raw_dir, normalized_dir = ensure_dirs(base_dir, "cellxgene")
    url = cfg["dataset_url"]
    payload_bytes = fetch_get_bytes(url)
    checksum = sha256_bytes(payload_bytes)
    downloaded_at = now_iso()
    raw_path = raw_dir / "dataset.h5ad"
    raw_path.write_bytes(payload_bytes)
    artifact = FetchArtifact("CELLxGENE", url, downloaded_at, checksum, cfg["dataset_id"], normalized_dir / "cellxgene_real_records.jsonl", raw_path, 0)
    rows = sparse_row_marker_values(raw_path, cfg["marker_genes"], cfg["size"])
    records = [
        normalize_cellxgene_row(row, artifact, idx, cfg["collection_name"], cfg["dataset_id"])
        for idx, row in enumerate(rows, start=1)
    ]
    write_jsonl(artifact.records_path, records)
    artifact.normalized_count = len(records)
    write_manifest(
        raw_dir / "manifest.json",
        base_manifest(
            source=artifact.source_name,
            source_family="spatial_context",
            download_url=artifact.download_url,
            downloaded_at=artifact.downloaded_at,
            checksum_sha256=artifact.checksum_sha256,
            release_info=artifact.release_info,
            access_notes="Public CELLxGENE h5ad download.",
            payload_type="h5ad_state_bearing_subset",
            transformation_manifest=["fetch_cellxgene_subset", "sparse_row_marker_values", "normalize_cellxgene_row"],
        )
        | {"notes": "Small public CELLxGENE atlas subset with per-cell marker-gene expression slices."},
    )
    return artifact


def extract_encode_age_and_sex(summary: str | None) -> tuple[str | None, str | None]:
    if not summary:
        return None, None
    sex = "male" if " male " in f" {summary} " else "female" if " female " in f" {summary} " else None
    match = re.search(r"\((\d+)\s+years?\)", summary)
    age = f"{match.group(1)} years" if match else None
    return age, sex


def normalize_encode_record(hit: dict[str, Any], artifact: FetchArtifact, idx: int) -> dict[str, Any]:
    age, sex = extract_encode_age_and_sex(hit.get("biosample_summary"))
    biosample = hit.get("biosample_ontology") or {}
    return {
        "record_id": f"encode_real_{idx:03d}",
        "dataset": "ENCODE",
        "study_id": hit["accession"],
        "source_sample_id": hit["accession"],
        "source_cell_id": None,
        "assay_id": hit.get("assay_title", "ATAC-seq"),
        "source_record_pointer": f"{artifact.download_url}#accession={hit['accession']}",
        "source_accession": hit["accession"],
        "source_download_url": artifact.download_url,
        "source_downloaded_at": artifact.downloaded_at,
        "source_checksum": artifact.checksum_sha256,
        "source_release_info": artifact.release_info,
        "subject_id": hit["accession"],
        "cell_instance_id": hit["accession"],
        "species": "Homo sapiens",
        "sex": sex,
        "age": age,
        "health_status": "unknown",
        "disease_state": "unknown",
        "tissue_label": UNKNOWN_TISSUE,
        "cell_type_label": biosample.get("term_name") or UNKNOWN_CELL_TYPE,
        "time_anchor_type": "baseline",
        "t0_timestamp": hit.get("date_released") or "released",
        "t0_time_unit": "timestamp",
        "has_epigenome_state": True,
        "state_representation_type": "raw_measured",
        "matched_modalities": 1,
        "license_class": "public_unrestricted",
        "constraint_profile_ref": f"constraint:{hit['accession']}",
        "mechanistic_support_score": 0.72,
        "measurement_support_score": 0.81,
    }


def fetch_encode_subset(base_dir: Path, cfg: dict[str, Any]) -> FetchArtifact:
    raw_dir, normalized_dir = ensure_dirs(base_dir, "encode")
    url = (
        "https://www.encodeproject.org/search/?type=Experiment"
        f"&assay_title={cfg['assay_title']}"
        "&status=released"
        "&replicates.library.biosample.donor.organism.scientific_name=Homo+sapiens"
        f"&limit={cfg['size']}&format=json"
    )
    payload_bytes = fetch_get_bytes(url, headers={"Accept": "application/json"})
    checksum = sha256_bytes(payload_bytes)
    downloaded_at = now_iso()
    raw_path = raw_dir / "search_response.json"
    raw_path.write_bytes(payload_bytes)
    obj = json.loads(payload_bytes.decode("utf-8"))
    artifact = FetchArtifact("ENCODE", url, downloaded_at, checksum, None, normalized_dir / "encode_real_records.jsonl", raw_path, 0)
    records = [normalize_encode_record(hit, artifact, idx) for idx, hit in enumerate(obj["@graph"][: cfg["size"]], start=1)]
    write_jsonl(artifact.records_path, records)
    artifact.normalized_count = len(records)
    write_manifest(
        raw_dir / "manifest.json",
        base_manifest(
            source=artifact.source_name,
            source_family="regulatory_logic",
            download_url=artifact.download_url,
            downloaded_at=artifact.downloaded_at,
            checksum_sha256=artifact.checksum_sha256,
            release_info=artifact.release_info,
            access_notes="Public ENCODE REST access; deeper signal-file processing is not yet performed.",
            payload_type="experiment_metadata",
            transformation_manifest=["fetch_encode_subset", "normalize_encode_record"],
        )
        | {"rate_limit_note": "ENCODE asks scripted GET usage to stay at or below 10 requests/second."},
    )
    return artifact


def normalize_perturb_seq_row(row: dict[str, str], artifact: FetchArtifact, idx: int) -> dict[str, Any]:
    barcode = row.get("") or f"barcode_{idx}"
    target_gene = row.get("gene") or None
    is_nt = (row.get("NT") or "").strip().upper() in {"TRUE", "T", "1", "YES"}
    return {
        "record_id": f"perturb_real_{idx:05d}",
        "dataset": "Perturb-seq",
        "study_id": "GSE153056",
        "source_sample_id": row.get("orig.ident") or row.get("MULTI_ID") or "unknown_sample",
        "source_cell_id": barcode,
        "assay_id": "ECCITE-seq",
        "source_record_pointer": f"{artifact.download_url}#cell={barcode}",
        "source_accession": "GSE153056",
        "source_download_url": artifact.download_url,
        "source_downloaded_at": artifact.downloaded_at,
        "source_checksum": artifact.checksum_sha256,
        "source_release_info": "GEO supplementary metadata TSV",
        "subject_id": "THP1",
        "cell_instance_id": barcode,
        "species": "Homo sapiens",
        "health_status": "cell_line",
        "disease_state": "acute monocytic leukemia",
        "tissue_label": "blood",
        "cell_type_label": "THP-1",
        "time_anchor_type": "post_perturbation",
        "t0_timestamp": row.get("replicate") or "unknown",
        "t0_time_unit": "replicate",
        "intervention_present": not is_nt and bool(target_gene),
        "intervention_type": "genetic",
        "intervention_target_entity": target_gene,
        "intervention_target_id": target_gene,
        "intervention_direction": "knockout" if (not is_nt and target_gene) else "none",
        "control_definition": "non-targeting guide" if is_nt else None,
        "state_representation_type": "raw_measured",
        "measurement_support_score": 0.84,
        "matched_modalities": 2,
        "license_class": "geo_public_no_restriction",
        "proliferation_measure": row.get("S.Score") or None,
        "raw_qc_score": min(float(row.get("nFeature_RNA") or 0) / 4000.0, 1.0) if row.get("nFeature_RNA") else 0.5,
        "assay_distortion_notes_ref": "GEO public metadata ingest with optional marker-gene transcriptome slice from raw supplement.",
    }


def extract_tar_member_bytes(tar_path: Path, member_name: str) -> bytes:
    with tarfile.open(tar_path) as tf:
        extracted = tf.extractfile(member_name)
        if extracted is None:
            raise FileNotFoundError(f"Member {member_name} not found in {tar_path}")
        return extracted.read()


def infer_perturb_pathway(transcriptome: list[dict[str, Any]], target_gene: str | None) -> str:
    values = {row["feature_id"]: row["value"] for row in transcriptome}
    interferon = sum(values.get(g, 0.0) for g in ["STAT1", "ISG15", "IFIT1", "IFIT3", "CXCL10"])
    inflammatory = sum(values.get(g, 0.0) for g in ["IL6", "TNF", "NFKBIA"])
    proliferative = sum(values.get(g, 0.0) for g in ["MKI67", "TOP2A"])
    if target_gene == "JAK1" and interferon < 1.0:
        return "interferon_suppression"
    if interferon >= max(inflammatory, proliferative) and interferon > 0:
        return "interferon_response"
    if inflammatory >= max(interferon, proliferative) and inflammatory > 0:
        return "NFkB_IL6"
    if proliferative > 0:
        return "cell_cycle_progression"
    return "perturbation_response"


def attach_perturb_expression(rows: list[dict[str, Any]], raw_tar_path: Path, member_name: str, marker_genes: list[str]) -> list[dict[str, Any]]:
    member_bytes = extract_tar_member_bytes(raw_tar_path, member_name)
    counts_path = raw_tar_path.parent / member_name
    counts_path.write_bytes(member_bytes)
    counts = pd.read_csv(counts_path, sep="\t", compression="gzip")
    gene_column = counts.columns[0]
    counts = counts.rename(columns={gene_column: "gene"}).set_index("gene")
    marker_present = [gene for gene in marker_genes if gene in counts.index]
    if not marker_present:
        return rows
    counts = counts.loc[marker_present]
    columns = set(str(col) for col in counts.columns)
    control_rows = [row for row in rows if not row.get("intervention_present")]
    control_barcodes = [row["source_cell_id"] for row in control_rows if row["source_cell_id"] in columns]
    control_means: dict[str, float] = {}
    for gene in marker_present:
        if control_barcodes:
            control_values = [float(counts.at[gene, barcode]) for barcode in control_barcodes]
            control_means[gene] = sum(control_values) / len(control_values)
        else:
            control_means[gene] = 0.0
    enriched_rows: list[dict[str, Any]] = []
    for row in rows:
        barcode = row["source_cell_id"]
        if barcode in columns:
            transcriptome = []
            for gene in marker_present:
                raw_value = float(counts.at[gene, barcode])
                value = round(raw_value - control_means.get(gene, 0.0), 4)
                if abs(value) > 0:
                    transcriptome.append(
                        {
                            "feature_id": gene,
                            "value": value,
                            "value_type": "log_fc",
                            "support_score": 0.92,
                        }
                    )
            if transcriptome:
                row["transcriptome"] = transcriptome
                row["dominant_pathway"] = infer_perturb_pathway(transcriptome, row.get("intervention_target_entity"))
                row["output_evidence_summary"] = "control-referenced marker delta from NT baseline"
                row["output_confidence_score"] = 0.84
        enriched_rows.append(row)
    return enriched_rows


def fetch_perturb_seq_subset(base_dir: Path, cfg: dict[str, Any]) -> FetchArtifact:
    raw_dir, normalized_dir = ensure_dirs(base_dir, "perturb_seq")
    url = cfg["metadata_url"]
    payload_bytes = fetch_get_bytes(url)
    checksum = sha256_bytes(payload_bytes)
    downloaded_at = now_iso()
    raw_path = raw_dir / "GSE153056_ECCITE_metadata.tsv.gz"
    raw_path.write_bytes(payload_bytes)
    text = gzip.decompress(payload_bytes).decode("utf-8")
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    rows = []
    for idx, row in enumerate(reader, start=1):
        rows.append(normalize_perturb_seq_row(row, FetchArtifact("Perturb-seq", url, downloaded_at, checksum, "GSE153056", normalized_dir / "perturb_seq_real_records.jsonl", raw_path, 0), idx))
        if len(rows) >= cfg["size"]:
            break
    artifact = FetchArtifact("Perturb-seq", url, downloaded_at, checksum, "GSE153056", normalized_dir / "perturb_seq_real_records.jsonl", raw_path, len(rows))
    if cfg.get("include_expression"):
        raw_tar_url = cfg["raw_tar_url"]
        raw_tar_bytes = fetch_get_bytes(raw_tar_url)
        raw_tar_checksum = sha256_bytes(raw_tar_bytes)
        raw_tar_path = raw_dir / "GSE153056_RAW.tar"
        raw_tar_path.write_bytes(raw_tar_bytes)
        rows = attach_perturb_expression(
            rows=rows,
            raw_tar_path=raw_tar_path,
            member_name=cfg["count_member"],
            marker_genes=cfg["marker_genes"],
        )
        artifact.checksum_sha256 = f"metadata:{checksum};raw_tar:{raw_tar_checksum}"
    write_jsonl(artifact.records_path, rows)
    write_manifest(
        raw_dir / "manifest.json",
        base_manifest(
            source=artifact.source_name,
            source_family="perturbation_response",
            download_url=artifact.download_url,
            downloaded_at=artifact.downloaded_at,
            checksum_sha256=artifact.checksum_sha256,
            release_info="GSE153056",
            access_notes="Public GEO supplementary files only.",
            payload_type="cell_metadata_plus_marker_transcriptome",
            transformation_manifest=["fetch_perturb_seq_subset", "normalize_perturb_seq_row", "attach_perturb_expression"],
        )
        | {
            "geo_accession": "GSE153056",
            "notes": "Parsed public supplementary cell metadata and, when enabled, a marker-gene transcriptome slice extracted from the GEO raw tar supplement.",
        },
    )
    return artifact


def normalize_hubmap_record(hit: dict[str, Any], artifact: FetchArtifact, idx: int) -> dict[str, Any]:
    source = hit["_source"]
    origin_sample = (source.get("origin_samples") or [{}])[0]
    donor = source.get("donor") or {}
    organ_code = origin_sample.get("organ") or "unknown"
    tissue_label = {"LI": "large intestine", "LY": "lymph node", "RK": "right kidney", "LK": "left kidney"}.get(organ_code, organ_code)
    return {
        "record_id": f"hubmap_real_{idx:03d}",
        "dataset": "HuBMAP",
        "study_id": source.get("hubmap_id"),
        "source_sample_id": source.get("hubmap_id"),
        "source_cell_id": None,
        "assay_id": source.get("dataset_type", "HuBMAP"),
        "source_record_pointer": f"{artifact.download_url}#hubmap_id={source.get('hubmap_id')}",
        "source_accession": source.get("hubmap_id"),
        "source_download_url": artifact.download_url,
        "source_downloaded_at": artifact.downloaded_at,
        "source_checksum": artifact.checksum_sha256,
        "source_release_info": artifact.release_info,
        "subject_id": donor.get("hubmap_id", source.get("hubmap_id")),
        "cell_instance_id": source.get("uuid"),
        "species": "Homo sapiens",
        "health_status": "unknown",
        "disease_state": "unknown",
        "tissue_label": tissue_label,
        "cell_type_label": UNKNOWN_CELL_TYPE,
        "microenvironment_label": source.get("group_name"),
        "time_anchor_type": "baseline",
        "t0_timestamp": str(source.get("published_timestamp") or source.get("created_timestamp") or "unknown"),
        "t0_time_unit": "timestamp",
        "has_spatial_state": source.get("dataset_type") == "CODEX",
        "state_representation_type": "normalized_measured",
        "matched_modalities": 1,
        "license_class": f"hubmap_{source.get('data_access_level', 'unknown')}",
        "measurement_support_score": 0.66,
        "assay_distortion_notes_ref": "Metadata/API-level ingest only; full file download for HuBMAP may require CLT/Globus workflow.",
    }


def fetch_hubmap_subset(base_dir: Path, cfg: dict[str, Any]) -> FetchArtifact:
    raw_dir, normalized_dir = ensure_dirs(base_dir, "hubmap")
    payload = {
        "size": cfg["size"],
        "query": {
            "bool": {
                "must": [
                    {"term": {"entity_type.keyword": "Dataset"}},
                    {"term": {"status.keyword": "Published"}},
                    {"term": {"data_access_level.keyword": "public"}},
                    {"term": {"dataset_type.keyword": cfg["dataset_type"]}},
                ]
            }
        },
    }
    url = "https://search.api.hubmapconsortium.org/v3/search"
    payload_bytes = fetch_post_bytes(url, payload)
    checksum = sha256_bytes(payload_bytes)
    downloaded_at = now_iso()
    raw_path = raw_dir / "search_response.json"
    raw_path.write_bytes(payload_bytes)
    obj = json.loads(payload_bytes.decode("utf-8"))
    artifact = FetchArtifact("HuBMAP", url, downloaded_at, checksum, f"dataset_type={cfg['dataset_type']}", normalized_dir / "hubmap_real_records.jsonl", raw_path, 0)
    records = [normalize_hubmap_record(hit, artifact, idx) for idx, hit in enumerate(obj["hits"]["hits"][: cfg["size"]], start=1)]
    write_jsonl(artifact.records_path, records)
    artifact.normalized_count = len(records)
    write_manifest(
        raw_dir / "manifest.json",
        base_manifest(
            source=artifact.source_name,
            source_family="spatial_context",
            download_url=artifact.download_url,
            downloaded_at=artifact.downloaded_at,
            checksum_sha256=artifact.checksum_sha256,
            release_info=artifact.release_info,
            access_notes="Public search metadata access; deeper payloads may require HuBMAP CLT/Globus.",
            payload_type="dataset_metadata",
            transformation_manifest=["fetch_hubmap_subset", "normalize_hubmap_record"],
        )
        | {
            "query_payload": payload,
            "notes": "Search API metadata download is fully automated; bulk file transfer may require HuBMAP CLT/Globus.",
        },
    )
    return artifact


def normalize_tcga_record(hit: dict[str, Any], artifact: FetchArtifact, idx: int) -> dict[str, Any]:
    diagnosis = next((item for item in hit.get("diagnoses", []) if item.get("age_at_diagnosis") is not None), {})
    age_days = diagnosis.get("age_at_diagnosis")
    age_years = f"{round(age_days / 365.25)} years" if isinstance(age_days, int) else None
    return {
        "record_id": f"tcga_real_{idx:03d}",
        "dataset": "TCGA",
        "study_id": "TCGA-LUAD",
        "source_sample_id": hit["submitter_id"],
        "source_cell_id": None,
        "assay_id": "clinical_metadata",
        "source_record_pointer": f"{artifact.download_url}#case={hit['submitter_id']}",
        "source_accession": hit["submitter_id"],
        "source_download_url": artifact.download_url,
        "source_downloaded_at": artifact.downloaded_at,
        "source_checksum": artifact.checksum_sha256,
        "source_release_info": artifact.release_info,
        "subject_id": hit["submitter_id"],
        "cell_instance_id": hit["submitter_id"],
        "species": "Homo sapiens",
        "sex": (hit.get("demographic") or {}).get("gender"),
        "age": age_years,
        "health_status": "diseased",
        "disease_state": "lung adenocarcinoma",
        "tissue_label": "lung",
        "cell_type_label": "Epithelial tumor cell",
        "time_anchor_type": "diagnosis",
        "t0_timestamp": "diagnosis",
        "t0_time_unit": "clinical_epoch",
        "has_clinical_context": True,
        "state_representation_type": "inferred",
        "matched_modalities": 1,
        "license_class": "gdc_open_metadata",
        "therapy_response_label": diagnosis.get("vital_status"),
        "outcome_time_horizon": "clinical_followup",
        "measurement_support_score": 0.58,
        "assay_distortion_notes_ref": "Clinical case metadata mapped to pseudo-cell outcome context.",
    }


def fetch_tcga_subset(base_dir: Path, cfg: dict[str, Any]) -> FetchArtifact:
    raw_dir, normalized_dir = ensure_dirs(base_dir, "tcga")
    payload = {
        "filters": {
            "op": "and",
            "content": [
                {"op": "=", "content": {"field": "project.project_id", "value": cfg["project_id"]}},
            ],
        },
        "fields": "submitter_id,disease_type,primary_site,demographic.gender,diagnoses.age_at_diagnosis,diagnoses.vital_status,diagnoses.tumor_stage",
        "format": "JSON",
        "size": cfg["size"],
    }
    url = "https://api.gdc.cancer.gov/cases"
    payload_bytes = fetch_post_bytes(url, payload)
    checksum = sha256_bytes(payload_bytes)
    downloaded_at = now_iso()
    raw_path = raw_dir / "cases_response.json"
    raw_path.write_bytes(payload_bytes)
    obj = json.loads(payload_bytes.decode("utf-8"))
    artifact = FetchArtifact("TCGA", url, downloaded_at, checksum, cfg["project_id"], normalized_dir / "tcga_real_records.jsonl", raw_path, 0)
    records = [normalize_tcga_record(hit, artifact, idx) for idx, hit in enumerate(obj["data"]["hits"], start=1)]
    write_jsonl(artifact.records_path, records)
    artifact.normalized_count = len(records)
    write_manifest(
        raw_dir / "manifest.json",
        base_manifest(
            source=artifact.source_name,
            source_family="clinical_outcomes",
            download_url=artifact.download_url,
            downloaded_at=artifact.downloaded_at,
            checksum_sha256=artifact.checksum_sha256,
            release_info=cfg["project_id"],
            access_notes="Open GDC metadata only; controlled genomic files intentionally excluded.",
            payload_type="clinical_case_metadata",
            transformation_manifest=["fetch_tcga_subset", "normalize_tcga_record"],
        )
        | {
            "project_id": cfg["project_id"],
            "notes": "Open-access clinical and biospecimen metadata only. Controlled genomic files are intentionally not fetched in this command.",
        },
    )
    return artifact


def normalize_omnipath_record(row: dict[str, Any], artifact: FetchArtifact, idx: int) -> dict[str, Any]:
    return {
        "record_id": f"omnipath_real_{idx:05d}",
        "dataset": "OmniPath",
        "study_id": "omnipath_interactions",
        "source_sample_id": f"{row.get('source_genesymbol')}->{row.get('target_genesymbol')}",
        "source_cell_id": None,
        "assay_id": "knowledge_graph",
        "source_record_pointer": f"{artifact.download_url}#edge={idx}",
        "source_accession": f"{row.get('source')}->{row.get('target')}",
        "source_download_url": artifact.download_url,
        "source_downloaded_at": artifact.downloaded_at,
        "source_checksum": artifact.checksum_sha256,
        "source_release_info": artifact.release_info,
        "subject_id": row.get("source_genesymbol") or f"edge_{idx}",
        "cell_instance_id": f"EDGE-{idx:05d}",
        "species": "Homo sapiens",
        "health_status": "knowledge_graph",
        "disease_state": "unknown",
        "tissue_label": UNKNOWN_TISSUE,
        "cell_type_label": UNKNOWN_CELL_TYPE,
        "time_anchor_type": "inferred",
        "t0_timestamp": "knowledge_graph",
        "t0_time_unit": "knowledge_graph",
        "signals": [
            {"feature_id": row.get("source_genesymbol"), "value": 1.0, "value_type": "binary", "support_score": 0.75},
            {"feature_id": row.get("target_genesymbol"), "value": 1.0, "value_type": "binary", "support_score": 0.75},
        ],
        "dominant_pathway": "intercellular_signaling" if row.get("is_stimulation") else "signaling_inhibition",
        "state_representation_type": "inferred",
        "matched_modalities": 1,
        "license_class": "omnipath_academic",
        "measurement_support_score": 0.62,
    }


def fetch_omnipath_subset(base_dir: Path, cfg: dict[str, Any]) -> FetchArtifact:
    raw_dir, normalized_dir = ensure_dirs(base_dir, "omnipath")
    url = f"https://omnipathdb.org/interactions?genesymbols=1&license=academic&format=json"
    payload_bytes = fetch_get_bytes(url)
    checksum = sha256_bytes(payload_bytes)
    downloaded_at = now_iso()
    raw_path = raw_dir / "interactions.json"
    raw_path.write_bytes(payload_bytes)
    rows = json.loads(payload_bytes.decode("utf-8"))
    artifact = FetchArtifact("OmniPath", url, downloaded_at, checksum, "license=academic", normalized_dir / "omnipath_real_records.jsonl", raw_path, 0)
    records = [normalize_omnipath_record(row, artifact, idx) for idx, row in enumerate(rows[: cfg["size"]], start=1)]
    write_jsonl(artifact.records_path, records)
    artifact.normalized_count = len(records)
    write_manifest(
        raw_dir / "manifest.json",
        base_manifest(
            source=artifact.source_name,
            source_family="signaling_graph",
            download_url=artifact.download_url,
            downloaded_at=artifact.downloaded_at,
            checksum_sha256=artifact.checksum_sha256,
            release_info=artifact.release_info,
            access_notes="Public web service with academic license filter applied.",
            payload_type="interaction_edges",
            transformation_manifest=["fetch_omnipath_subset", "normalize_omnipath_record"],
        )
        | {"notes": "Academic license filter requested explicitly from public web service."},
    )
    return artifact


def normalize_gtex_record(
    tissue: str,
    transcriptome: list[dict[str, Any]],
    sample_count: int,
    artifact: FetchArtifact,
    idx: int,
) -> dict[str, Any]:
    return {
        "record_id": f"gtex_real_{idx:03d}",
        "dataset": "GTEx",
        "study_id": "GTEx_v8",
        "source_sample_id": tissue,
        "source_cell_id": None,
        "assay_id": "bulk_tissue_rnaseq",
        "source_record_pointer": f"{artifact.download_url}#tissue={tissue}",
        "source_accession": "GTEx_v8",
        "source_download_url": artifact.download_url,
        "source_downloaded_at": artifact.downloaded_at,
        "source_checksum": artifact.checksum_sha256,
        "source_release_info": artifact.release_info,
        "subject_id": tissue,
        "cell_instance_id": f"GTEX-{idx:03d}",
        "species": "Homo sapiens",
        "health_status": "healthy",
        "disease_state": "normal",
        "tissue_label": tissue,
        "cell_type_label": f"{tissue} reference pseudo-cell",
        "microenvironment_label": "healthy_tissue_reference",
        "time_anchor_type": "baseline",
        "t0_timestamp": "GTEx_v8_release",
        "t0_time_unit": "release",
        "state_representation_type": "normalized_measured",
        "matched_modalities": 1,
        "license_class": "gtex_public",
        "measurement_support_score": 0.83,
        "replication_count": sample_count,
        "transcriptome": transcriptome,
        "dominant_pathway": "healthy_tissue_baseline",
        "assay_distortion_notes_ref": "Bulk tissue median TPM summarized as pseudo-cell baseline reference.",
    }


def fetch_gtex_subset(base_dir: Path, cfg: dict[str, Any]) -> FetchArtifact:
    raw_dir, normalized_dir = ensure_dirs(base_dir, "gtex")
    sample_url = cfg["sample_attributes_url"]
    expr_url = cfg["median_tpm_url"]
    sample_path = raw_dir / "GTEx_Analysis_v8_Annotations_SampleAttributesDS.txt"
    expr_path = raw_dir / "GTEx_gene_median_tpm.gct.gz"
    sample_checksum = download_to_path(sample_url, sample_path)
    expr_checksum = download_to_path(expr_url, expr_path)
    downloaded_at = now_iso()
    sample_df = pd.read_csv(sample_path, sep="\t", usecols=["SAMPID", "SMTS", "SMTSD"])
    tissue_counts = sample_df["SMTSD"].value_counts().to_dict()
    expr_df = pd.read_csv(expr_path, sep="\t", compression="gzip", skiprows=2)
    marker_df = expr_df[expr_df["Description"].isin(cfg["marker_genes"])]
    selected_tissues = cfg["tissues"][: cfg["size"]]
    artifact = FetchArtifact(
        "GTEx",
        expr_url,
        downloaded_at,
        f"sample:{sample_checksum};expr:{expr_checksum}",
        "GTEx_v8",
        normalized_dir / "gtex_real_records.jsonl",
        expr_path,
        0,
    )
    records: list[dict[str, Any]] = []
    for idx, tissue in enumerate(selected_tissues, start=1):
        if tissue not in marker_df.columns:
            continue
        transcriptome = []
        for _, row in marker_df.iterrows():
            value = float(row[tissue])
            if value > 0:
                transcriptome.append(
                    {
                        "feature_id": str(row["Description"]),
                        "value": round(value, 4),
                        "value_type": "abundance",
                        "support_score": 0.9,
                    }
                )
        records.append(normalize_gtex_record(tissue, transcriptome, int(tissue_counts.get(tissue, 0)), artifact, idx))
    write_jsonl(artifact.records_path, records)
    artifact.normalized_count = len(records)
    write_manifest(
        raw_dir / "manifest.json",
        base_manifest(
            source=artifact.source_name,
            source_family="baseline_state",
            download_url=artifact.download_url,
            downloaded_at=artifact.downloaded_at,
            checksum_sha256=artifact.checksum_sha256,
            release_info=artifact.release_info,
            access_notes="Public GTEx v8 annotation and median TPM files from official Google Cloud storage.",
            payload_type="bulk_tissue_reference_expression",
            transformation_manifest=["fetch_gtex_subset", "normalize_gtex_record"],
        )
        | {"sample_attributes_url": sample_url, "notes": "Healthy tissue baseline summaries from GTEx v8 median TPM with sample-count provenance."},
    )
    return artifact


def _read_lincs_matrix_metadata(matrix_path: Path) -> tuple[list[str], dict[str, list[str]], int]:
    with gzip.open(matrix_path, "rt", encoding="utf-8") as handle:
        handle.readline()
        dims = handle.readline().strip().split("\t")
        n_col_meta = int(dims[3])
        header = handle.readline().strip().split("\t")
        sample_ids = header[12:]
        metadata_rows: dict[str, list[str]] = {}
        for _ in range(n_col_meta):
            row = handle.readline().strip().split("\t")
            metadata_rows[row[0]] = row[12:]
    return sample_ids, metadata_rows, n_col_meta


def _extract_lincs_marker_profiles(matrix_path: Path, sample_indices: dict[str, int], marker_genes: list[str], n_col_meta: int) -> dict[str, dict[str, float]]:
    profiles = {sample_id: {} for sample_id in sample_indices}
    with gzip.open(matrix_path, "rt", encoding="utf-8") as handle:
        handle.readline()
        handle.readline()
        handle.readline()
        for _ in range(n_col_meta):
            handle.readline()
        for line in handle:
            row = line.rstrip("\n").split("\t")
            gene_symbol = row[5]
            if gene_symbol not in marker_genes:
                continue
            values = row[12:]
            for sample_id, column_index in sample_indices.items():
                profiles[sample_id][gene_symbol] = float(values[column_index])
    return profiles


def fetch_lincs_subset(base_dir: Path, cfg: dict[str, Any]) -> FetchArtifact:
    raw_dir, normalized_dir = ensure_dirs(base_dir, "lincs")
    matrix_path = raw_dir / "level2.gct.gz"
    cell_info_path = raw_dir / "cell_info.txt.gz"
    pert_info_path = raw_dir / "pert_info.txt.gz"
    matrix_checksum = download_to_path(cfg["level2_matrix_url"], matrix_path)
    cell_checksum = download_to_path(cfg["cell_info_url"], cell_info_path)
    pert_checksum = download_to_path(cfg["pert_info_url"], pert_info_path)
    downloaded_at = now_iso()
    cell_info = pd.read_csv(cell_info_path, sep="\t", compression="gzip")
    pert_info = pd.read_csv(pert_info_path, sep="\t", compression="gzip")
    sample_ids, metadata_rows, n_col_meta = _read_lincs_matrix_metadata(matrix_path)
    sample_df = pd.DataFrame(
        {
            "sample_id": sample_ids,
            "cell_id": metadata_rows.get("CL_Center_Specific_ID", ["unknown"] * len(sample_ids)),
            "compound_id": metadata_rows.get("SM_Center_Compound_ID", ["unknown"] * len(sample_ids)),
            "dose": metadata_rows.get("SM_Dose", ["-666"] * len(sample_ids)),
            "dose_unit": metadata_rows.get("SM_Dose_Unit", ["unknown"] * len(sample_ids)),
        }
    )
    allowed_cells = cfg.get("cell_ids", ["*"])
    if allowed_cells == ["*"] or allowed_cells == "*":
        cell_mask = pd.Series([True] * len(sample_df))
    else:
        cell_mask = sample_df["cell_id"].isin(allowed_cells)
    selected = sample_df[cell_mask & ~sample_df["compound_id"].isin(["dmso", "-666"])].head(cfg["size"])
    control_df = sample_df[cell_mask & sample_df["compound_id"].isin(["dmso"])]
    selected_ids = selected["sample_id"].tolist() + control_df["sample_id"].tolist()
    sample_index_map = {sample_id: idx for idx, sample_id in enumerate(sample_ids)}
    profiles = _extract_lincs_marker_profiles(matrix_path, {sid: sample_index_map[sid] for sid in selected_ids}, cfg["marker_genes"], n_col_meta)
    control_means: dict[str, dict[str, float]] = {}
    for cell_id, frame in control_df.groupby("cell_id"):
        control_means[cell_id] = {}
        for gene in cfg["marker_genes"]:
            values = [profiles[sid].get(gene, 0.0) for sid in frame["sample_id"]]
            control_means[cell_id][gene] = sum(values) / len(values) if values else 0.0
    pert_lookup = pert_info.set_index("pert_id").to_dict(orient="index")
    cell_lookup = cell_info.set_index("cell_id").to_dict(orient="index")
    artifact = FetchArtifact(
        "LINCS",
        cfg["level2_matrix_url"],
        downloaded_at,
        f"matrix:{matrix_checksum};cell:{cell_checksum};pert:{pert_checksum}",
        "GSE70138",
        normalized_dir / "lincs_real_records.jsonl",
        matrix_path,
        0,
    )
    records: list[dict[str, Any]] = []
    for idx, row in enumerate(selected.itertuples(index=False), start=1):
        cell_meta = cell_lookup.get(row.cell_id, {})
        pert_meta = pert_lookup.get(row.compound_id, {})
        transcriptome = []
        for gene in cfg["marker_genes"]:
            delta = float(profiles[row.sample_id].get(gene, 0.0)) - float(control_means.get(row.cell_id, {}).get(gene, 0.0))
            if abs(delta) >= cfg.get("min_abs_delta", 0.25):
                transcriptome.append(
                    {"feature_id": gene, "value": round(delta, 4), "value_type": "log_fc", "support_score": 0.78}
                )
        records.append(
            {
                "record_id": f"lincs_real_{idx:04d}",
                "dataset": "LINCS",
                "study_id": "GSE70138",
                "source_sample_id": row.sample_id,
                "source_cell_id": row.sample_id,
                "assay_id": "L1000_Level2",
                "source_record_pointer": f"{artifact.download_url}#sample={row.sample_id}",
                "source_accession": "GSE70138",
                "source_download_url": artifact.download_url,
                "source_downloaded_at": artifact.downloaded_at,
                "source_checksum": artifact.checksum_sha256,
                "source_release_info": artifact.release_info,
                "subject_id": row.cell_id,
                "cell_instance_id": row.sample_id,
                "species": "Homo sapiens",
                "sex": cell_meta.get("donor_sex"),
                "age": f"{cell_meta.get('donor_age')} years" if cell_meta.get("donor_age") not in [None, "-666"] else None,
                "health_status": "cell_line",
                "disease_state": cell_meta.get("primary_site", "unknown"),
                "tissue_label": cell_meta.get("primary_site", UNKNOWN_TISSUE),
                "cell_type_label": row.cell_id,
                "time_anchor_type": "post_perturbation",
                "t0_timestamp": "LINCS_phase2",
                "t0_time_unit": "release",
                "intervention_present": True,
                "intervention_type": "chemical",
                "intervention_target_entity": pert_meta.get("pert_iname", row.compound_id),
                "intervention_target_id": row.compound_id,
                "intervention_direction": "exposure",
                "intervention_dose": str(row.dose),
                "intervention_dose_unit": row.dose_unit,
                "control_definition": f"DMSO controls in {row.cell_id}",
                "state_representation_type": "normalized_measured",
                "measurement_support_score": 0.79,
                "matched_modalities": 2,
                "license_class": "geo_public_no_restriction",
                "transcriptome": transcriptome,
                "dominant_pathway": "lincs_chemical_response",
                "output_evidence_summary": f"DMSO-referenced landmark-gene delta in {row.cell_id}",
                "output_confidence_score": 0.8,
            }
        )
    write_jsonl(artifact.records_path, records)
    artifact.normalized_count = len(records)
    write_manifest(
        raw_dir / "manifest.json",
        base_manifest(
            source=artifact.source_name,
            source_family="perturbation_response",
            download_url=artifact.download_url,
            downloaded_at=artifact.downloaded_at,
            checksum_sha256=artifact.checksum_sha256,
            release_info=artifact.release_info,
            access_notes="Public GEO supplementary metadata and Level2 matrix download.",
            payload_type="chemical_perturbation_response_subset",
            transformation_manifest=["fetch_lincs_subset", "_read_lincs_matrix_metadata", "_extract_lincs_marker_profiles"],
        )
        | {"notes": "Small public LINCS subset using DMSO-referenced landmark-gene deltas from official GEO Level2 matrix."},
    )
    return artifact


def fetch_depmap_subset(base_dir: Path, cfg: dict[str, Any]) -> FetchArtifact:
    raw_dir, normalized_dir = ensure_dirs(base_dir, "depmap")
    sample_info_path = raw_dir / "sample_info.csv"
    dependency_path = raw_dir / "gene_dependency.csv"
    expression_path = raw_dir / "expression.csv"
    sample_checksum = download_to_path(cfg["sample_info_url"], sample_info_path)
    dep_checksum = download_to_path(cfg["dependency_url"], dependency_path)
    expr_checksum = download_to_path(cfg["expression_url"], expression_path)
    downloaded_at = now_iso()
    sample_info = pd.read_csv(sample_info_path)
    dependency = pd.read_csv(dependency_path)
    expression = pd.read_csv(expression_path)
    selected_samples = sample_info.head(cfg["size"]).copy()
    dependency = dependency.rename(columns={dependency.columns[0]: "DepMap_ID"}).set_index("DepMap_ID")
    expression = expression.rename(columns={expression.columns[0]: "DepMap_ID"}).set_index("DepMap_ID")
    artifact = FetchArtifact(
        "DepMap",
        cfg["dependency_url"],
        downloaded_at,
        f"sample:{sample_checksum};dependency:{dep_checksum};expression:{expr_checksum}",
        cfg["release_info"],
        normalized_dir / "depmap_real_records.jsonl",
        dependency_path,
        0,
    )
    records: list[dict[str, Any]] = []
    for idx, row in enumerate(selected_samples.itertuples(index=False), start=1):
        depmap_id = row.DepMap_ID
        if depmap_id not in dependency.index or depmap_id not in expression.index:
            continue
        dependency_row = dependency.loc[depmap_id]
        target_gene = None
        target_score = None
        for gene in cfg["dependency_priority_genes"]:
            matching = [column for column in dependency_row.index if column.startswith(f"{gene} ")]
            if matching:
                target_gene = gene
                target_score = float(dependency_row[matching[0]])
                break
        if target_gene is None:
            continue
        transcriptome = []
        expr_row = expression.loc[depmap_id]
        for gene in cfg["marker_genes"]:
            matching = [column for column in expr_row.index if column.startswith(f"{gene} ")]
            if matching:
                value = float(expr_row[matching[0]])
                if value > 0:
                    transcriptome.append({"feature_id": gene, "value": round(value, 4), "value_type": "abundance", "support_score": 0.86})
        records.append(
            {
                "record_id": f"depmap_real_{idx:04d}",
                "dataset": "DepMap",
                "study_id": cfg["release_info"],
                "source_sample_id": depmap_id,
                "source_cell_id": None,
                "assay_id": "CRISPR_dependency_plus_expression",
                "source_record_pointer": f"{artifact.download_url}#depmap_id={depmap_id}",
                "source_accession": depmap_id,
                "source_download_url": artifact.download_url,
                "source_downloaded_at": artifact.downloaded_at,
                "source_checksum": artifact.checksum_sha256,
                "source_release_info": artifact.release_info,
                "subject_id": depmap_id,
                "cell_instance_id": depmap_id,
                "species": "Homo sapiens",
                "sex": getattr(row, "sex", None),
                "health_status": "cell_line",
                "disease_state": getattr(row, "primary_disease", None) or getattr(row, "lineage", "unknown"),
                "tissue_label": getattr(row, "lineage", UNKNOWN_TISSUE),
                "cell_type_label": getattr(row, "CCLE_Name", depmap_id),
                "time_anchor_type": "post_perturbation",
                "t0_timestamp": cfg["release_info"],
                "t0_time_unit": "release",
                "intervention_present": True,
                "intervention_type": "genetic",
                "intervention_target_entity": target_gene,
                "intervention_target_id": target_gene,
                "intervention_direction": "knockout",
                "state_representation_type": "normalized_measured",
                "measurement_support_score": 0.82,
                "matched_modalities": 2,
                "license_class": "depmap_public_subset",
                "transcriptome": transcriptome,
                "viability_measure": str(round(target_score, 4)),
                "dominant_pathway": "dependency_viability_constraint",
                "output_evidence_summary": f"gene dependency score for {target_gene}",
                "output_confidence_score": 0.82,
            }
        )
    write_jsonl(artifact.records_path, records)
    artifact.normalized_count = len(records)
    write_manifest(
        raw_dir / "manifest.json",
        base_manifest(
            source=artifact.source_name,
            source_family="perturbation_response",
            download_url=artifact.download_url,
            downloaded_at=artifact.downloaded_at,
            checksum_sha256=artifact.checksum_sha256,
            release_info=artifact.release_info,
            access_notes="Public pediatric DepMap subset files from Broad/figshare.",
            payload_type="dependency_viability_subset",
            transformation_manifest=["fetch_depmap_subset"],
        )
        | {"notes": "Cell-line dependency events with paired expression marker slices from public DepMap pediatric subset."},
    )
    return artifact


def fetch_trrust_subset(base_dir: Path, cfg: dict[str, Any]) -> FetchArtifact:
    raw_dir, normalized_dir = ensure_dirs(base_dir, "trrust")
    raw_path = raw_dir / "trrust_human.tsv"
    checksum = download_to_path(cfg["human_url"], raw_path)
    downloaded_at = now_iso()
    rows: list[dict[str, Any]] = []
    with raw_path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle, start=1):
            tf_symbol, target_symbol, effect_direction, pubmed_id = line.strip().split("\t")
            rows.append(
                {
                    "record_id": f"trrust_real_{idx:05d}",
                    "dataset": "TRRUST",
                    "study_id": "TRRUST_human",
                    "source_sample_id": f"{tf_symbol}->{target_symbol}",
                    "source_cell_id": None,
                    "assay_id": "regulatory_edge",
                    "source_record_pointer": f"{cfg['human_url']}#edge={idx}",
                    "source_accession": f"{tf_symbol}->{target_symbol}",
                    "source_download_url": cfg["human_url"],
                    "source_downloaded_at": downloaded_at,
                    "source_checksum": checksum,
                    "source_release_info": "TRRUST_human",
                    "subject_id": tf_symbol,
                    "cell_instance_id": f"TRRUST-{idx:05d}",
                    "species": "Homo sapiens",
                    "health_status": "knowledge_graph",
                    "disease_state": "unknown",
                    "tissue_label": UNKNOWN_TISSUE,
                    "cell_type_label": UNKNOWN_CELL_TYPE,
                    "time_anchor_type": "inferred",
                    "t0_timestamp": "knowledge_graph",
                    "t0_time_unit": "knowledge_graph",
                    "signals": [
                        {"feature_id": tf_symbol, "value": 1.0, "value_type": "binary", "support_score": 0.84},
                        {"feature_id": target_symbol, "value": 1.0, "value_type": "binary", "support_score": 0.84},
                    ],
                    "state_representation_type": "inferred",
                    "license_class": "trrust_public",
                    "measurement_support_score": 0.68,
                    "constraint_refs": [f"pubmed:{pubmed_id}"],
                    "dominant_pathway": f"trrust_{effect_direction.lower()}",
                }
            )
            if len(rows) >= cfg["size"]:
                break
    artifact = FetchArtifact("TRRUST", cfg["human_url"], downloaded_at, checksum, "TRRUST_human", normalized_dir / "trrust_real_records.jsonl", raw_path, len(rows))
    write_jsonl(artifact.records_path, rows)
    write_manifest(
        raw_dir / "manifest.json",
        base_manifest(
            source=artifact.source_name,
            source_family="regulatory_logic",
            download_url=artifact.download_url,
            downloaded_at=artifact.downloaded_at,
            checksum_sha256=artifact.checksum_sha256,
            release_info=artifact.release_info,
            access_notes="Public TRRUST human TSV download.",
            payload_type="tf_target_edges",
            transformation_manifest=["fetch_trrust_subset"],
        ),
    )
    return artifact


def fetch_reactome_subset(base_dir: Path, cfg: dict[str, Any]) -> FetchArtifact:
    raw_dir, normalized_dir = ensure_dirs(base_dir, "reactome")
    version_url = "https://reactome.org/ContentService/data/database/version"
    version_bytes = fetch_get_bytes(version_url)
    release_info = version_bytes.decode("utf-8").strip()
    url = "https://reactome.org/ContentService/data/pathways/top/9606"
    payload_bytes = fetch_get_bytes(url)
    checksum = sha256_bytes(payload_bytes)
    downloaded_at = now_iso()
    raw_path = raw_dir / "top_pathways.json"
    raw_path.write_bytes(payload_bytes)
    rows = json.loads(payload_bytes.decode("utf-8"))
    records = []
    for idx, row in enumerate(rows[: cfg["size"]], start=1):
        pathway_name = row["displayName"]
        records.append(
            {
                "record_id": f"reactome_real_{idx:04d}",
                "dataset": "Reactome",
                "study_id": "Reactome_ContentService",
                "source_sample_id": row["stId"],
                "source_cell_id": None,
                "assay_id": "pathway_knowledge",
                "source_record_pointer": f"{url}#pathway={row['stId']}",
                "source_accession": row["stId"],
                "source_download_url": url,
                "source_downloaded_at": downloaded_at,
                "source_checksum": checksum,
                "source_release_info": release_info,
                "subject_id": row["stId"],
                "cell_instance_id": f"REACTOME-{idx:04d}",
                "species": "Homo sapiens",
                "health_status": "knowledge_graph",
                "disease_state": "unknown",
                "tissue_label": UNKNOWN_TISSUE,
                "cell_type_label": UNKNOWN_CELL_TYPE,
                "time_anchor_type": "inferred",
                "t0_timestamp": "knowledge_graph",
                "t0_time_unit": "knowledge_graph",
                "signals": [{"feature_id": row["stId"], "value": 1.0, "value_type": "binary", "support_score": 0.82}],
                "state_representation_type": "inferred",
                "license_class": "reactome_cc_by_4_0",
                "measurement_support_score": 0.7,
                "dominant_pathway": pathway_name,
            }
        )
    artifact = FetchArtifact("Reactome", url, downloaded_at, checksum, release_info, normalized_dir / "reactome_real_records.jsonl", raw_path, len(records))
    write_jsonl(artifact.records_path, records)
    write_manifest(
        raw_dir / "manifest.json",
        base_manifest(
            source=artifact.source_name,
            source_family="signaling_graph",
            download_url=artifact.download_url,
            downloaded_at=artifact.downloaded_at,
            checksum_sha256=artifact.checksum_sha256,
            release_info=artifact.release_info,
            access_notes="Public Reactome Content Service.",
            payload_type="pathway_topology_subset",
            transformation_manifest=["fetch_reactome_subset"],
        ),
    )
    return artifact


def fetch_biomodels_subset(base_dir: Path, cfg: dict[str, Any]) -> FetchArtifact:
    raw_dir, normalized_dir = ensure_dirs(base_dir, "biomodels")
    url = f"https://www.ebi.ac.uk/biomodels/search?query={cfg['query']}&offset=0&numResults={cfg['size']}&format=json"
    payload_bytes = fetch_get_bytes(url)
    checksum = sha256_bytes(payload_bytes)
    downloaded_at = now_iso()
    raw_path = raw_dir / "search_response.json"
    raw_path.write_bytes(payload_bytes)
    obj = json.loads(payload_bytes.decode("utf-8"))
    records = []
    for idx, model in enumerate(obj.get("models", [])[: cfg["size"]], start=1):
        model_id = model["id"]
        sbml_url = f"https://www.ebi.ac.uk/biomodels/model/download/{model_id}?filename={model_id}_url.xml"
        records.append(
            {
                "record_id": f"biomodels_real_{idx:04d}",
                "dataset": "BioModels",
                "study_id": "BioModels_search",
                "source_sample_id": model_id,
                "source_cell_id": None,
                "assay_id": "mechanistic_model",
                "source_record_pointer": sbml_url,
                "source_accession": model_id,
                "source_download_url": url,
                "source_downloaded_at": downloaded_at,
                "source_checksum": checksum,
                "source_release_info": cfg["query"],
                "subject_id": model_id,
                "cell_instance_id": model_id,
                "species": "Homo sapiens",
                "health_status": "knowledge_model",
                "disease_state": "unknown",
                "tissue_label": UNKNOWN_TISSUE,
                "cell_type_label": UNKNOWN_CELL_TYPE,
                "time_anchor_type": "inferred",
                "t0_timestamp": model.get("submissionDate", "unknown"),
                "t0_time_unit": "timestamp",
                "signals": [{"feature_id": model_id, "value": 1.0, "value_type": "binary", "support_score": 0.8}],
                "state_representation_type": "inferred",
                "license_class": "biomodels_cc_by_4_0",
                "measurement_support_score": 0.67,
                "constraint_refs": [sbml_url],
                "dominant_pathway": model.get("name", cfg["query"]),
            }
        )
    artifact = FetchArtifact("BioModels", url, downloaded_at, checksum, cfg["query"], normalized_dir / "biomodels_real_records.jsonl", raw_path, len(records))
    write_jsonl(artifact.records_path, records)
    write_manifest(
        raw_dir / "manifest.json",
        base_manifest(
            source=artifact.source_name,
            source_family="metabolism_feasibility",
            download_url=artifact.download_url,
            downloaded_at=artifact.downloaded_at,
            checksum_sha256=artifact.checksum_sha256,
            release_info=artifact.release_info,
            access_notes="Public BioModels search and model download endpoints.",
            payload_type="mechanistic_model_metadata_subset",
            transformation_manifest=["fetch_biomodels_subset"],
        ),
    )
    return artifact


def load_fetch_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def copy_fixture_raw(root: Path, output_dir: Path) -> Path:
    source = root / "examples" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in source.glob("*.jsonl"):
        shutil.copy2(path, output_dir / path.name)
    return output_dir


def fetch_real_public_subset(root: Path, config_path: Path, output_dir: Path, source_filter: str | None = None) -> list[FetchArtifact]:
    cfg = load_fetch_config(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    fetchers = [
        ("hca", fetch_hca_subset),
        ("gtex", fetch_gtex_subset),
        ("cellxgene", fetch_cellxgene_subset),
        ("encode", fetch_encode_subset),
        ("perturb_seq", fetch_perturb_seq_subset),
        ("lincs", fetch_lincs_subset),
        ("depmap", fetch_depmap_subset),
        ("hubmap", fetch_hubmap_subset),
        ("tcga", fetch_tcga_subset),
        ("trrust", fetch_trrust_subset),
        ("reactome", fetch_reactome_subset),
        ("biomodels", fetch_biomodels_subset),
        ("omnipath", fetch_omnipath_subset),
    ]
    artifacts: list[FetchArtifact] = []
    for name, fetcher in fetchers:
        if source_filter and name != source_filter:
            continue
        artifacts.append(fetcher(output_dir, cfg["sources"][name]))

    normalized_all_dir = output_dir / "normalized_all"
    normalized_all_dir.mkdir(parents=True, exist_ok=True)
    for artifact in artifacts:
        target = normalized_all_dir / artifact.records_path.name
        target.write_text(artifact.records_path.read_text(encoding="utf-8"), encoding="utf-8")

    manifest_rows = [
        {
            "source_name": artifact.source_name,
            "download_url": artifact.download_url,
            "downloaded_at": artifact.downloaded_at,
            "checksum_sha256": artifact.checksum_sha256,
            "release_info": artifact.release_info,
            "records_path": str(artifact.records_path),
            "raw_path": str(artifact.raw_path),
            "normalized_count": artifact.normalized_count,
        }
        for artifact in artifacts
    ]
    write_manifest(
        output_dir / "fetch_manifest.json",
        {
            "artifacts": manifest_rows,
            "generated_at": now_iso(),
            "normalized_all_dir": str(normalized_all_dir),
        },
    )
    return artifacts
