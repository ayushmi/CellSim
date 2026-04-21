Run it from the repo root.

## 1. Set up the environment

```bash id="gfd2c8"
cd /Users/ayush/Development/PhysicalAI/CellSim

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e '.[dev]'
```

## 2. Sanity check the install

```bash id="1fiv2r"
python -m cod.cli --help
pytest -q
```

You should see the CLI help and the tests pass.

## 3. Run the small public build first

This is the quickest end-to-end test.

```bash id="z2griy"
python -m cod.cli fetch-real --config configs/real_public_subset.yaml --output-dir data/upstream_cod_test
python -m cod.cli materialize --raw-dir data/upstream_cod_test/normalized_all --output-dir data/materialized_cod_test
python -m cod.cli benchmark-prep --input-dir data/materialized_cod_test --output-dir benchmarks/cod_test --config configs/benchmark_prep.yaml
```

## 4. Inspect the generated artifacts

```bash id="6h4g1r"
ls data/materialized_cod_test
ls benchmarks/cod_test
```

Useful files to check:

* `data/materialized_cod_test/build_manifest.json`
* `data/materialized_cod_test/source_manifest.json`
* `data/materialized_cod_test/summary_stats.json`
* `data/materialized_cod_test/action_space_report.json`
* `data/materialized_cod_test/output_space_report.json`
* `data/materialized_cod_test/data_quality_report.json`
* `benchmarks/cod_test/benchmark_report.json`
* `benchmarks/cod_test/benchmark_audit_report.json`

A quick view:

```bash id="sqd8gv"
cat data/materialized_cod_test/summary_stats.json
cat benchmarks/cod_test/benchmark_report.json
```

## 5. Launch the Explorer UI

```bash id="3kfm0e"
python -m cod.cli launch-explorer --data-dir data/materialized_cod_test
```

That should start Streamlit locally and print a local URL, usually:

* `http://localhost:8501`

Open it in your browser.

## 6. Run the larger COD 2.0 public build

Once the small build works:

```bash id="ko982d"
python -m cod.cli fetch-real --config configs/cod2_public_large.yaml --output-dir data/upstream_cod2_public
python -m cod.cli materialize --raw-dir data/upstream_cod2_public/normalized_all --output-dir data/materialized_cod2_public
python -m cod.cli benchmark-prep --input-dir data/materialized_cod2_public --output-dir benchmarks/cod2_public --config configs/benchmark_prep.yaml
python -m cod.cli launch-explorer --data-dir data/materialized_cod2_public
```

## 7. What to verify manually

Check these five things:

### A. Fetch actually downloaded real files

```bash id="f6e7uw"
find data/upstream_cod2_public -maxdepth 3 | head -50
```

### B. Materialization produced the expected reports

```bash id="7n0s6x"
ls data/materialized_cod2_public
```

### C. Summary stats look sane

```bash id="hgz7p4"
cat data/materialized_cod2_public/summary_stats.json
```

### D. Benchmarks were created

```bash id="qrlw5r"
ls benchmarks/cod2_public
cat benchmarks/cod2_public/benchmark_report.json
```

### E. UI loads and shows the new build

Use the Explorer pages:

* Overview
* Event Explorer
* Event Detail
* Source Browser
* Benchmark Explorer
* Build Comparison

## 8. Fast troubleshooting

If install fails:

```bash id="36lf53"
pip install -U pip setuptools wheel
pip install -e '.[dev]'
```

If CLI import fails:

```bash id="t86faj"
python -c "import cod; print(cod)"
```

If Streamlit does not open automatically:

```bash id="4g2tz3"
streamlit run ui/streamlit_app.py -- --data-dir data/materialized_cod2_public
```

If a fetch step fails, test one source first:

```bash id="kam8dj"
python -m cod.cli fetch-source --source perturb_seq --config configs/cod2_public_large.yaml --output-dir data/upstream_one_source
```

## 9. Minimal “done” checklist

You’re good if all of these work:

* `pytest -q`
* small public build completes
* `summary_stats.json` exists
* benchmark reports exist
* Explorer opens locally
* larger COD 2.0 public build completes


