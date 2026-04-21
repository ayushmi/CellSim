# COD 3.0 Platform Notes

COD 3.0 reframes the repository around four main goals:

- honest outcome support
- trajectory-aware event construction
- stronger plausibility and constraint layers
- evaluation of external action models against COD

## Outcome Strategy

COD 3.0 does not pretend that the public-open build has rich long-horizon outcomes.

Current stance:

- `DepMap` contributes `proxy_only` medium-horizon viability-like outcomes
- `TCGA` remains weak clinical context in the open path and is not promoted into intervention-linked outcome benchmarks
- `Perturb-seq` and `LINCS` remain short-horizon output sources in the current public path

The public-open outcome benchmark is therefore labeled `proxy_only`, not `meaningful`.

## Trajectory Strategy

COD 3.0 adds trajectory-aware metadata, but does not invent dense longitudinal chains.

Current public-open support:

- transition events from `Perturb-seq`, `LINCS`, and `DepMap` receive inferred short-chain trajectory ids
- trajectory refs are marked as inferred when they are assembled from pre-state / intervention / output structure rather than repeated direct observation
- atlas state rows can form single-step trajectory groups for browsing and evaluation bookkeeping

## Plausibility Layer

Plausibility is intentionally evidence-weighted and conservative.

Current support combines:

- regulatory overlap from `TRRUST`
- signaling overlap from `OmniPath`
- pathway context from `Reactome` and `BioModels`
- viability/dependency constraints from `DepMap`
- measurement support already present in the source record

These produce:

- `regulatory_support_score`
- `pathway_support_score`
- `metabolic_support_score`
- `viability_constraint_score`
- `overall_plausibility_score`
- `unsupported_action_flag`

## External Evaluation

COD 3.0 now includes an evaluator for external action models.

The evaluator:

- accepts a simple prediction file keyed by `cod_event_id`
- scores action agreement and candidate agreement
- scores output-type agreement where outputs exist
- reports calibration, held-out robustness, plausibility penalties, and failure taxonomy
- never rewrites the external predictions

## Current Truth Boundary

COD 3.0 is strongest today as:

- a state/intervention/output dataset
- a proxy-outcome substrate
- a plausibility layer
- an evaluation harness

It is not yet:

- a rich public-open clinical outcome dataset
- a dense true longitudinal trajectory atlas
- a mechanistic simulator grounded in executed pathway or metabolic models
