# Action Derivation

COD action derivation currently combines:

- transcriptome marker programs when available
- perturbation context
- metabolite signals
- pathway or signaling hints
- evidence-tier-aware assignment

## Current mapper

Implemented in [`src/cod/action_mapping.py`](src/cod/action_mapping.py).

Current grounded rules include:

- interferon activation from `STAT1`, `ISG15`, `IFIT1`, `IFIT3`, `CXCL10`
- interferon suppression in compatible perturbational contexts such as `JAK1` loss with weak interferon markers
- inflammatory cytokine program from `IL6`, `TNF`, `NFKBIA`
- proliferative entry from `MKI67`, `TOP2A`
- glycolytic shift from lactate-like metabolite evidence

## Important non-claim

These are still **weak biological labels**, not gold-standard mechanistic truth. COD preserves:

- raw observations
- action assignment method
- confidence
- evidence tier
- provenance trace

The next step is to replace or augment these rules with differential-expression and pathway-scoring pipelines on deeper source ingests.
