# Manual And Controlled Adapters

COD 1.0 ships default automated fetchers for public-open sources and manual/local adapters for sources that cannot be fetched deeply by default in an open repository.

Available manual adapters live in [src/cod/manual_adapters.py](src/cod/manual_adapters.py) and are indexed in [configs/manual_adapter_specs.yaml](configs/manual_adapter_specs.yaml).

## Supported Adapters

- `tabula_sapiens_h5ad`: local h5ad to COD state-bearing records
- `roadmap_metadata`: local Roadmap metadata TSV to regulatory context records
- `recon3d_sbml`: local Recon3D SBML to metabolic constraint records
- `hmdb_metabolites_xml`: local HMDB XML to metabolite registry records
- `kegg_local_tsv`: local KEGG export to pathway knowledge records
- `ukb_tabular`: local UK Biobank export to cohort outcome/context records

## CLI

```bash
python -m cod.cli run-manual-adapter --adapter tabula_sapiens_h5ad --input /path/to/tabula.h5ad --output data/manual/tabula_sapiens.jsonl --dataset-id tabula_sapiens_subset
python -m cod.cli run-manual-adapter --adapter recon3d_sbml --input /path/to/recon3d.xml --output data/manual/recon3d.jsonl
python -m cod.cli run-manual-adapter --adapter ukb_tabular --input /path/to/ukb_export.tsv --output data/manual/ukb.jsonl
```

## Honesty Boundary

- These adapters do not bypass licensing, governance, or access controls.
- KEGG and UK Biobank remain user-supplied local inputs only.
- HMDB local parsing is supported, but the default repo path does not auto-fetch HMDB due access/reuse friction.
- Tabula Sapiens and Roadmap are adapter-complete for local files, but not default automated public-open fetches.
