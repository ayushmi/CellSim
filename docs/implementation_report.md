# COD v0.1 Implementation Report

## What is complete

- Canonical CTE schema implemented as typed Pydantic models.
- JSON Schema export path and relational SQL DDL.
- First-pass action ontology and evidence-tier ontology.
- Source-family contracts representing all 19 datasets named in the manual.
- Executable end-to-end subset for `Human Cell Atlas`, `Perturb-seq`, `ENCODE`, `HuBMAP`, `TCGA`, and `OmniPath`.
- Executable state-bearing atlas subset for `CELLxGENE`.
- Streamlit-based COD Explorer for local read-only inspection.
- Real public-subset acquisition path for `Human Cell Atlas`, `Perturb-seq` via GEO, `ENCODE`, `HuBMAP`, `TCGA`, and `OmniPath`.
- Example materialization into JSONL and Parquet, plus benchmark task rows.
- Machine-readable source support matrix for all 19 source families.
- Build manifests, summary stats, and benchmark-prep outputs.

## What is partial

- HCA ingestion currently uses sample metadata, not full cell-by-gene matrices.
- CELLxGENE ingestion now provides a genuine state-bearing subset, but only through marker-gene expression slices rather than full-expression integration.
- Perturb-seq upstream ingestion now parses public GEO metadata plus a marker-gene transcriptome slice, but not a full generalized processed expression workflow.
- HuBMAP ingestion currently uses Search API metadata, not the CLT/Globus dataset transfer path.
- TCGA ingestion currently uses open clinical metadata only, not controlled genomic data.
- OmniPath ingestion is real and useful but remains graph-context rather than event-observation data.

## What is stubbed

- Source-specific parsers for `GTEx`, `Tabula Sapiens`, `Roadmap`, `TRRUST`, `LINCS`, `DepMap`, `Recon3D`, `BioModels`, `HMDB`, `CELLxGENE`, `UK Biobank`, `Reactome`, and `KEGG`.
- Large-scale ontology registries for genes, proteins, metabolites, compounds, and diseases.
- Learned action classifiers and batch-correction workflows.

## Key design decisions

- The CTE is the central fact table; modalities stay in linked profile tables.
- Provenance is emitted for transformed fields instead of being embedded as comments or hidden metadata.
- Pairing uncertainty is treated as data, not as an ingestion inconvenience.
- The current action labeling engine uses weak supervision from transcriptome markers, perturbation context, pathway hints, and metabolite signals so the action layer exists immediately and can later be replaced by stronger biological classifiers.

## Where probabilistic linkage was necessary

- `HuBMAP` spatial context to single-cell state was represented as contextual linkage rather than exact cell identity.
- `TCGA` outcomes were attached as pseudo-cell or subject-level outcome context with probabilistic support semantics.
- Signaling priors from `OmniPath` were linked as contextual support, not as direct observations of a specific event.

## Assumptions

- Example records use compact synthetic subsets meant to exercise the architecture, not reproduce source datasets.
- Disease, cell type, and tissue mappings use a small built-in registry to keep the reference implementation runnable without external downloads.
