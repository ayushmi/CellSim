# Example Fixtures

Files in [`examples/raw`](examples/raw) are **hand-curated fixtures** used for local development and testing.

They are not direct upstream downloads.

Use them when you want:

- fast schema testing
- deterministic CI
- a tiny demo bundle

Use the real upstream path when you want actual public-source ingestion:

```bash
. .venv/bin/activate
python -m cod.cli fetch-real --config configs/real_public_subset.yaml --output-dir data/upstream_real
python -m cod.cli materialize --raw-dir data/upstream_real/normalized_all --output-dir data/materialized_real
```
