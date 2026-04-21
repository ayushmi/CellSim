# Benchmarking

COD benchmark preparation is driven by [`configs/benchmark_prep.yaml`](configs/benchmark_prep.yaml) and the CLI command:

```bash
python -m cod.cli benchmark-prep --input-dir data/materialized_real --output-dir benchmarks/real_public
```

## Outputs

- `benchmark_dataset.jsonl`
- `benchmark_report.json`

## Included views

- state to action
- state plus intervention to short-horizon output
- state plus intervention to outcome
- source-family generalization view
- measured vs inferred state flags
- high-evidence row flags

## Baselines

The repository currently ships simple reproducible baselines:

- global majority action
- per-source majority action

These are intentionally modest. They are here to prove dataset usability and evaluation wiring, not to claim strong biological modeling performance.
