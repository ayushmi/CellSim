# Truth Audit: Fixtures vs Real Upstream Ingestion

## Bottom line

Before this upgrade, the repository used only bundled fixture files in [`examples/raw`](/Users/ayush/Development/PhysicalAI/CellSim/examples/raw). It did **not** download from true upstream public sources.

After this upgrade, the repository supports a separate `fetch-real` path for six public sources:

- Human Cell Atlas
- CELLxGENE
- ENCODE
- Perturb-seq via GEO
- HuBMAP
- TCGA via GDC
- OmniPath

The example fixtures are still present, but they are now explicitly labeled as fixtures.

## Per-source audit

### Human Cell Atlas

- Previous state: fixture only
- Current upstream path: `python -m cod.cli fetch-real`
- Source: HCA Data Browser API sample metadata query
- Truly parsed: project ID/title, sample ID, organ, disease, donor sex, donor age, developmental stage, submission timestamps, source snapshot identifier
- Placeholder/inferred: cell type when HCA sample API does not expose it, action labels, outcome labels
- Access/licensing: public metadata; HCA Data Use Agreement states datasets in current release are CC BY 4.0

### CELLxGENE

- Previous state: adapter/spec only
- Current upstream path: `python -m cod.cli fetch-real`
- Source: public CELLxGENE `h5ad` asset download
- Truly parsed: per-cell metadata, per-cell marker-gene expression slice, tissue, disease, cell type, spatial coordinates when present
- Placeholder/inferred: only marker-gene slice rather than full-expression integration, action labels
- Access/licensing: public dataset asset URLs, open-download path

### ENCODE

- Previous state: fixture only
- Current upstream path: `python -m cod.cli fetch-real`
- Source: ENCODE REST search endpoint for released ATAC-seq experiments
- Truly parsed: accession, assay title, biosample ontology term, biosample summary, release metadata
- Placeholder/inferred: tissue label if not exposed in returned payload, action labels, outcomes
- Access/licensing: publicly released ENCODE objects are downloadable without login; ENCODE FAQ indicates use without restriction with citation

### Perturb-seq

- Previous state: fixture only
- Current upstream path: `python -m cod.cli fetch-real`
- Source: GEO supplementary metadata plus `GSE153056_RAW.tar`
- Truly parsed: cell barcode, lane/sample identifiers, RNA/ADT/GDO counts, guide identifiers, perturbed gene, replicate, cell-cycle scores, and a marker-gene transcriptome slice extracted from public cDNA counts
- Placeholder/inferred: full transcriptome processing, generalized differential pipeline, output/outcome labels
- Access/licensing: GEO is public and NCBI states it places no restrictions on use/distribution of GEO data

### HuBMAP

- Previous state: fixture only
- Current upstream path: `python -m cod.cli fetch-real`
- Source: HuBMAP Search API POST query over published public datasets
- Truly parsed: HuBMAP ID, dataset type, access level, group name, origin sample organ, timestamps, UUID
- Placeholder/inferred: cell type, fine spatial neighborhood, direct molecular outputs
- Access/licensing: public metadata is accessible; bulk dataset download may require HuBMAP CLT/Globus and some datasets can be protected

### TCGA

- Previous state: fixture only
- Current upstream path: `python -m cod.cli fetch-real`
- Source: GDC `cases` endpoint filtered to `TCGA-LUAD`
- Truly parsed: submitter ID, primary site, disease type, gender, age at diagnosis where available, diagnosis metadata
- Placeholder/inferred: pseudo-cell mapping, epithelial tumor cell label, action labels
- Access/licensing: open metadata is accessible without login; controlled genomic data is intentionally not automated here

### OmniPath

- Previous state: fixture only
- Current upstream path: `python -m cod.cli fetch-real`
- Source: public OmniPath interactions endpoint with `license=academic`
- Truly parsed: source/target IDs, source/target gene symbols, directionality, stimulation/inhibition flags
- Placeholder/inferred: event-level cellular context and action labels
- Access/licensing: license filter matters; this implementation explicitly requests academic-allowed records

## What is still not true

- The repository does not yet perform rich cell-level joins across these real sources.
- The repository does not yet download full raw matrices or protected files for every source.
- The real-source materialization is still a **public subset path**, not a full production release builder.
