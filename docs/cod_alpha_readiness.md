# COD Alpha Readiness

## What Is Fixed

- Outcome benchmark rows are now gated by real outcome evidence. The current public build has `0` valid outcome rows, and the outcome task is marked unavailable instead of silently populated.
- Build summaries now report consistent counts for events, evidence traces, transcriptome rows, signaling rows, benchmark rows, source families, and per-source totals.
- Benchmark prep now emits a leakage audit and task-quality flags.
- Action mapping has been expanded from a 3-label regime into a broader weakly supervised action-family layer with candidate labels and confidence.

## What Is Still Weak

- `state_to_action` remains source-dominated in the current public build, especially across `perturbation_response`, `spatial_context`, and `signaling_graph`.
- Long-horizon outcomes remain absent in the open build, so outcome modeling is still unavailable rather than merely low quality.
- Action labels are still weakly supervised and should not be treated as gold mechanistic truth.
- ENCODE, HuBMAP, OmniPath, and TCGA remain contextual contributors rather than deep transition-bearing sources.

## Benchmark Validity

- `state_to_action`: available, but flagged `weak_or_source_dominated`
- `state_plus_intervention_to_output`: available and currently the most meaningful benchmark task
- `state_plus_intervention_to_outcome`: unavailable in the current public-open Alpha build

## Alpha Verdict

This repository can honestly be called a **COD Alpha** candidate for:

- reproducible public-open COD materialization
- state-bearing and transition-bearing public subsets
- provenance-aware weak action labeling
- benchmark generation with leakage audit

It should **not** yet be marketed as a biologically deep operational dataset for outcome prediction or source-robust action learning.
