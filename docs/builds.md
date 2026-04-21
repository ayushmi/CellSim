# Build Versioning

Every materialized COD build now writes:

- `build_manifest.json`
- `summary_stats.json`

## Build manifest fields

- build ID
- schema version
- ontology version
- action-mapper version
- benchmark split version
- source support matrix version
- materialization timestamp
- build kind
- source manifest bundle
- counts
- summary stats

This is the minimum viable build provenance layer for reproducible public COD releases.
