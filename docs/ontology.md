# Ontology Notes

COD currently carries several ontology layers:

- action ontology: [`schemas/ontology/action_ontology.yaml`](/Users/ayush/Development/PhysicalAI/CellSim/schemas/ontology/action_ontology.yaml)
- evidence tiers: [`schemas/ontology/evidence_tiers.yaml`](/Users/ayush/Development/PhysicalAI/CellSim/schemas/ontology/evidence_tiers.yaml)
- benchmark splits: [`schemas/ontology/benchmark_splits.yaml`](/Users/ayush/Development/PhysicalAI/CellSim/schemas/ontology/benchmark_splits.yaml)

## Entity harmonization

The current open-source implementation includes a compact built-in registry for:

- selected genes
- selected tissues
- selected cell types
- selected diseases

This is enough to keep the public-subset program reproducible, but it is not yet a full production registry.

## Important distinction

- raw source identifier: source-native ID
- normalized identifier: mapped registry ID where available
- harmonized representation: COD-integrated field used across sources
- inferred representation: model or rule-produced latent/summary field

The repository intentionally does not overwrite raw source identity with harmonized values.
