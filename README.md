# Cell Operating Dataset (COD)

This repository is the first implementation of the **Cell Operating Dataset**, built directly from [`COD_research_manual_v3.md`](COD_research_manual_v3.md).

COD centers the **Cell Transition Event (CTE)** as the unit of record:

`cell state + inputs/interventions + constraints -> actions + short-horizon outputs + long-horizon outcomes + reward context`

The repository is designed as a serious extension point for:

- dataset construction
- model training
- intervention ranking
- world/policy/value modeling
- future closed-loop biology workflows

## Repository layout

- `src/cod/`: typed models, harmonization, action mapping, and materialization pipeline
- `ui/`: Streamlit COD Explorer
- `schemas/`: JSON Schema, SQL DDL, ontologies, and source-family contracts
- `docs/`: architecture, data model notes, and implementation report
- `examples/`: synthetic subset inputs and generated COD outputs
- `configs/`: materialization config
- `tests/`: schema and pipeline tests
- `ingestion/`: ingestion notes and extension guidance

## Program status

- Canonical CTE model with explicit uncertainty, pairing, provenance, evidence-tier fields, build manifests, release notes, and summary stats
- SQL DDL for the core event/modality/provenance tables
- Versioned action ontology and evidence-tier ontology
- Benchmark split specification plus benchmark-prep outputs, leakage audit, quality flags, and baseline reports
- Data contracts and support-matrix coverage for all 19 source datasets from the manual
- Example fixture pipeline for deterministic development
- Real public-subset acquisition path for:
  - Human Cell Atlas metadata
  - GTEx healthy tissue reference summaries
  - CELLxGENE state-bearing atlas subset
  - ENCODE experiment metadata
  - Perturb-seq via GEO metadata plus marker-gene transcriptome slices from public raw counts
  - LINCS chemical perturbation subset from public GEO Level2 matrix
  - DepMap pediatric public dependency/expression subset
  - HuBMAP dataset metadata
  - TCGA open clinical metadata
  - TRRUST regulatory edges
  - Reactome top pathways
  - BioModels mechanistic model metadata
  - OmniPath signaling interactions
- Manual/local adapters for Tabula Sapiens, Roadmap Epigenomics, Recon3D, HMDB, KEGG, and UK Biobank
- COD Explorer UI for local inspection of materialized outputs and build manifests

## Quick start: fixture path

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
python -m cod.cli export-schema
python -m cod.cli fetch-fixtures --output-dir data/fixtures_raw
python -m cod.cli materialize --raw-dir examples/raw --output-dir examples/output
pytest
```

## Quick start: COD 3.0 public-open build

```bash
. .venv/bin/activate
python -m cod.cli fetch-real --config configs/cod3_public_large.yaml --output-dir data/upstream_cod3_public
python -m cod.cli materialize --raw-dir data/upstream_cod3_public/normalized_all --output-dir data/materialized_cod3_public
python -m cod.cli benchmark-prep --input-dir data/materialized_cod3_public --output-dir benchmarks/cod3_public
python -m cod.cli evaluate-predictions --input-dir data/materialized_cod3_public --predictions examples/predictions/cod3_sample_external_predictions.jsonl --output-dir benchmarks/cod3_public/evaluation_latest
python -m cod.cli launch-explorer --data-dir data/materialized_cod3_public
```

COD 3.0 adds proxy-only outcome support, trajectory-aware event fields, plausibility scoring, and an external-model evaluation harness.

## Quick start: COD 2.0 public-open build

```bash
. .venv/bin/activate
python -m cod.cli fetch-real --config configs/cod2_public_large.yaml --output-dir data/upstream_cod2_public
python -m cod.cli materialize --raw-dir data/upstream_cod2_public/normalized_all --output-dir data/materialized_cod2_public
python -m cod.cli benchmark-prep --input-dir data/materialized_cod2_public --output-dir benchmarks/cod2_public
python -m cod.cli launch-explorer --data-dir data/materialized_cod2_public
```

The COD 2.0 public-open build is the current recommended release path. It scales the strongest open sources instead of broadening shallow coverage and keeps the outcome task disabled by design because no valid public-open long-horizon outcome labels are present.

## Quick start: COD 1.0 public subset

```bash
. .venv/bin/activate
python -m cod.cli fetch-real --config configs/real_public_subset.yaml --output-dir data/upstream_cod10_public
python -m cod.cli materialize --raw-dir data/upstream_cod10_public/normalized_all --output-dir data/materialized_cod10_public
python -m cod.cli benchmark-prep --input-dir data/materialized_cod10_public --output-dir benchmarks/cod10_public
python -m cod.cli launch-explorer --data-dir data/materialized_cod10_public
```

Legacy larger deep public build:

```bash
python -m cod.cli fetch-real --config configs/real_public_large.yaml --output-dir data/upstream_real_large
python -m cod.cli materialize --raw-dir data/upstream_real_large/normalized_all --output-dir data/materialized_real_large
python -m cod.cli benchmark-prep --input-dir data/materialized_real_large --output-dir benchmarks/real_public_large
```

Point the Explorer at `data/materialized_cod3_public` to inspect the current COD 3.0 build, or compare against `data/materialized_cod2_public` / `data/materialized_cod10_public`.

## CLI

Core commands:

- `python -m cod.cli fetch-fixtures`
- `python -m cod.cli fetch-real`
- `python -m cod.cli fetch-source --source perturb_seq`
- `python -m cod.cli fetch-source --source gtex`
- `python -m cod.cli fetch-source --source lincs`
- `python -m cod.cli fetch-source --source depmap`
- `python -m cod.cli fetch-source --source reactome`
- `python -m cod.cli fetch-source --source biomodels`
- `python -m cod.cli normalize-source --input data/upstream_real/hca/normalized/hca_real_records.jsonl --output-dir data/normalized_oneoffs`
- `python -m cod.cli run-manual-adapter --adapter tabula_sapiens_h5ad --input /path/to/local.h5ad --output data/manual/tabula.jsonl --dataset-id tabula_subset`
- `python -m cod.cli materialize`
- `python -m cod.cli generate-support-matrix`
- `python -m cod.cli benchmark-prep`
- `python -m cod.cli report-build`
- `python -m cod.cli launch-explorer --data-dir data/materialized_real`

## Storage model

Relational:

- `cod_event`
- `transcriptome_profiles`
- `metabolome_profiles`
- `signaling_profiles`
- `entity_registry`
- `action_ontology`
- `evidence_trace`
- `benchmark_rows`

Lakehouse layout:

- `bronze_raw/`
- `silver_normalized/`
- `gold_cod_release/`
- `benchmarks/`
- `ontology/`
- `provenance/`

Each build now emits:

- `build_manifest.json`
- `source_manifest.json`
- `summary_stats.json`
- `action_space_report.json`
- `output_space_report.json`
- `outcome_space_report.json`
- `trajectory_report.json`
- `plausibility_report.json`
- `data_quality_report.json`
- `benchmark_report.json`
- `benchmark_audit_report.json`
- `evaluation_report.json`
- `release_notes.md`
- explicit `state_depth_category` and `event_type` fields in materialized events

## COD Explorer

The Explorer is a read-only Streamlit app with:

- `Overview`
- `Event Explorer`
- `Event Detail`
- `Source Browser`
- `Ontology Browser`
- `Benchmark Explorer`
- `Data Quality`
- `Build Comparison`

See [`docs/explorer_demo.md`](docs/explorer_demo.md).

## Honest support boundaries

This first version does **not** pretend every dataset can be cell-joined exactly. Where joins are only contextual or probabilistic, the materialized CTEs carry:

- `measurement_pairing_status`
- `harmonization_confidence`
- `support_density_estimate`
- `support_domain_tag`
- `modality_conflict_flag`

Important truthfulness notes:

- [`examples/raw`](examples/raw) contains fixtures, not upstream downloads.
- Real upstream acquisition status is documented in [`docs/truth_audit.md`](docs/truth_audit.md).
- Per-source support is summarized in [`docs/source_support_matrix.md`](docs/source_support_matrix.md) and [`docs/source_support_matrix.json`](docs/source_support_matrix.json).
- Complete implementation status is in [`docs/implementation_report.md`](docs/implementation_report.md).
- COD 1.0 platform notes are in [`docs/cod_1_0_platform.md`](docs/cod_1_0_platform.md).
- COD 2.0 platform notes are in [`docs/cod_2_0_platform.md`](docs/cod_2_0_platform.md).
- COD 3.0 platform notes are in [`docs/cod_3_0_platform.md`](docs/cod_3_0_platform.md).
- Benchmark workflow notes are in [`docs/benchmarking.md`](docs/benchmarking.md).
- Action derivation notes are in [`docs/action_derivation.md`](docs/action_derivation.md).
- External prediction contract and evaluator notes are in [`docs/evaluation_contract.md`](docs/evaluation_contract.md).
- Manual and controlled adapters are documented in [`docs/manual_adapters.md`](docs/manual_adapters.md).
