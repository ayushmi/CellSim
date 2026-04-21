# COD Explorer Demo

## Run locally

```bash
. .venv/bin/activate
streamlit run ui/streamlit_app.py
```

The app defaults to [`examples/output`](/Users/ayush/Development/PhysicalAI/CellSim/examples/output) and can also point at a real materialized run such as `data/materialized_real`.

## Views

- `Overview`: event counts, source coverage, action/evidence distributions, split counts, missingness summary
- `Event Explorer`: filter/search CTEs and export filtered subsets
- `Event Detail`: full read-only inspection of one event
- `Ontology Browser`: action ontology, evidence tiers, and current rule mapping summary
- `Benchmark Explorer`: inspect benchmark rows and export filtered subsets
- `Data Quality`: missingness, confidence, support, and state representation counts

## Why Streamlit

The Explorer is deliberately local-first and read-only. Streamlit keeps the maintenance burden low while still making the materialized COD bundle legible to researchers who are onboarding to the schema.
