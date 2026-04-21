# COD Architecture

COD is implemented as a layered, event-centric system built around the **Cell Transition Event (CTE)**.

## Layers

1. `bronze_raw/`
   Immutable source-native records, file manifests, and source metadata.
2. `silver_normalized/`
   Identifier-normalized and contract-validated source records with explicit unresolved mappings.
3. `gold_cod_release/`
   Materialized CTEs, modality tables, ontologies, benchmark rows, and provenance traces.
4. `benchmarks/`
   Benchmark task views and split membership tables.
5. `ontology/`
   Entity registries, action ontology, evidence tiers, and split definitions.

## Table strategy

- `cod_event` is the central fact table.
- High-dimensional modalities are kept in linked profile tables.
- Ontology and graph knowledge stay separate from the event table so they can evolve independently.
- Provenance is mandatory and field-aware.

## Probabilistic linkage policy

The manual is explicit that many biological joins are not exact. This implementation therefore carries:

- `measurement_pairing_status`
- `harmonization_confidence`
- `support_density_estimate`
- `support_domain_tag`
- `modality_conflict_flag`

Exact cell joins are only used when the source gives a stable cell identifier. Cross-assay or patient-to-cell mappings otherwise stay probabilistic.
