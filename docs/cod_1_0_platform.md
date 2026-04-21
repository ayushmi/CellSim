# COD 1.0 Platform Note

COD 1.0 is the first truthful public-open platform release of the Cell Operating Dataset.

## What COD 1.0 Includes

- 19 source families represented in code, contracts, and support matrix
- automated public-open ingestion for `Human Cell Atlas`, `GTEx`, `CELLxGENE`, `ENCODE`, `Perturb-seq`, `LINCS`, `DepMap`, `HuBMAP`, `TCGA` open metadata, `TRRUST`, `Reactome`, `BioModels`, and `OmniPath`
- manual/local adapters for `Tabula Sapiens`, `Roadmap Epigenomics`, `Recon3D`, `HMDB`, `KEGG`, and `UK Biobank`
- explicit event typing, state-depth typing, abstention-aware action labeling, benchmark gating, leakage audit, and release artifacts

## What COD 1.0 Does Not Claim

- It does not claim valid long-horizon outcome tasks in the public-open build.
- It does not claim exact cell joins where only contextual linkage exists.
- It does not claim weakly supervised action labels are mechanistic truth.
- It does not claim that controlled sources are unlocked by the public-open workflow.

## Current Public-Open Build

Reference build:

- [data/materialized_cod10_public](data/materialized_cod10_public)
- [benchmarks/cod10_public](benchmarks/cod10_public)

Headline numbers:

- `286` events
- `13` represented upstream datasets
- `7` represented source families
- `198` valid `state_to_action` benchmark rows
- `83` valid `state + intervention -> output` benchmark rows
- `0` valid outcome rows

## Best Current Task

The strongest current public-open task is `state_plus_intervention_to_output`.

`state_to_action` is now benchmark-valid and materially less source-leaky than Alpha, but still remains weakly supervised and should be treated as a learning benchmark rather than a biological ground-truth task.
