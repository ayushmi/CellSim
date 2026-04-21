# Ingestion Layer

This directory documents the ingestion surface for COD.

- Contracts for all 19 source families live in [`schemas/contracts/source_family_contracts.yaml`](schemas/contracts/source_family_contracts.yaml).
- Executable ingestion and materialization logic lives in [`src/cod/materialize.py`](src/cod/materialize.py).
- Real public-subset acquisition lives in [`src/cod/acquisition.py`](src/cod/acquisition.py).
- The first end-to-end subset currently wires `Human Cell Atlas`, `Perturb-seq`, `ENCODE`, `HuBMAP`, `TCGA`, and `OmniPath`.

## Commands

Fixture path:

```bash
python -m cod.cli materialize --raw-dir examples/raw --output-dir examples/output
```

Real public-subset path:

```bash
python -m cod.cli fetch-real --config configs/real_public_subset.yaml --output-dir data/upstream_real
python -m cod.cli materialize --raw-dir data/upstream_real/normalized_all --output-dir data/materialized_real
```

Extension rule:

1. Add a new source contract entry.
2. Add a raw adapter or parser for the source-specific format.
3. Normalize identifiers into the shared registries.
4. Emit provenance traces for every transformed field.
5. Update tests with a fixture covering the new dataset family.
