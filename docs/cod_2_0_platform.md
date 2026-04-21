# COD 2.0 Platform Notes

COD 2.0 is the current public-open release track for the Cell Operating Dataset.

## What Changed Relative To COD 1.0

- The public-open build now scales to thousands of real events instead of hundreds.
- The dominant added depth comes from `Perturb-seq` and `LINCS`, which now provide most `transition_bearing` events in the modeling build.
- `CELLxGENE`, `GTEx`, and `DepMap` continue to provide state-bearing or output-bearing context instead of being drowned out by metadata rows.
- Benchmark leakage is still audited, but the COD 2.0 action task is materially less source-shortcut-driven than the earlier Alpha/COD 1.0 builds.
- Output semantics are now reported explicitly via `output_type`, `output_evidence_summary`, `output_confidence_score`, and `output_space_report.json`.

## Public-Open COD 2.0 Build

Recommended commands:

```bash
python -m cod.cli fetch-real --config configs/cod2_public_large.yaml --output-dir data/upstream_cod2_public
python -m cod.cli materialize --raw-dir data/upstream_cod2_public/normalized_all --output-dir data/materialized_cod2_public
python -m cod.cli benchmark-prep --input-dir data/materialized_cod2_public --output-dir benchmarks/cod2_public
python -m cod.cli launch-explorer --data-dir data/materialized_cod2_public
```

## Outcome Strategy

COD 2.0 uses an honest public-open no-outcome design.

- `state_plus_intervention_to_outcome` remains disabled in the default public-open build.
- Viability-like and transcriptomic responses from `DepMap`, `LINCS`, and `Perturb-seq` are treated as short-horizon outputs, not long-horizon outcomes.
- Controlled or restricted sources may eventually unlock stronger outcome layers, but COD 2.0 does not pretend those labels exist today.

## Strongest Current Event Types

- `transition_event` + `transition_bearing`: intervention-response rows from `Perturb-seq`, `LINCS`, and `DepMap`
- `state_event` + `state_bearing`: atlas/reference rows from `CELLxGENE` and `GTEx`
- `knowledge_support_event`: signaling/regulatory/mechanistic priors from `OmniPath`, `TRRUST`, `Reactome`, and `BioModels`

## What COD 2.0 Is Good For

- training and stress-testing `state -> action` models with explicit leakage audit
- training `state + intervention -> output` models on the strongest public-open task in the repo
- inspecting how action labels were weakly derived from transcriptomic and contextual evidence
- auditing provenance, uncertainty, event depth, and exact vs probabilistic linkage

## What COD 2.0 Still Does Not Solve

- public-open long-horizon outcomes
- full-transcriptome deep ingestion across all sources
- mechanistic gold-standard action labels
- controlled-data molecular depth from resources like deeper TCGA or UK Biobank
