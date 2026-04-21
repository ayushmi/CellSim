from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from .acquisition import copy_fixture_raw, fetch_real_public_subset
from .benchmarks import prepare_benchmarks
from .evaluation import evaluate_predictions
from .materialize import materialize_cod
from .manual_adapters import ADAPTER_FUNCTIONS
from .models import CellTransitionEvent
from .reporting import write_build_summary
from .source_support import generate_support_matrix_markdown, load_source_support


def export_json_schema(root: Path) -> Path:
    target = root / "schemas" / "json" / "cell_transition_event.schema.json"
    target.write_text(json.dumps(CellTransitionEvent.model_json_schema(), indent=2), encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="COD reference pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("export-schema", help="Export JSON schema from Pydantic model")

    fixture_parser = subparsers.add_parser("fetch-fixtures", help="Copy bundled fixture raws into a target directory")
    fixture_parser.add_argument("--output-dir", default="data/fixtures_raw")

    materialize_parser = subparsers.add_parser("materialize", help="Materialize COD sample from example raw inputs")
    materialize_parser.add_argument("--raw-dir", default="examples/raw")
    materialize_parser.add_argument("--output-dir", default="examples/output")

    fetch_real_parser = subparsers.add_parser("fetch-real", help="Fetch small real public subsets and normalize them for COD materialization")
    fetch_real_parser.add_argument("--config", default="configs/real_public_subset.yaml")
    fetch_real_parser.add_argument("--output-dir", default="data/upstream_real")

    fetch_source_parser = subparsers.add_parser("fetch-source", help="Fetch one real public source from the configured set")
    fetch_source_parser.add_argument("--source", required=True, choices=["hca", "gtex", "cellxgene", "encode", "perturb_seq", "lincs", "depmap", "hubmap", "tcga", "trrust", "reactome", "biomodels", "omnipath"])
    fetch_source_parser.add_argument("--config", default="configs/real_public_subset.yaml")
    fetch_source_parser.add_argument("--output-dir", default="data/upstream_real")

    normalize_parser = subparsers.add_parser("normalize-source", help="Validate and rewrite normalized per-source JSONL into a target directory")
    normalize_parser.add_argument("--input", required=True)
    normalize_parser.add_argument("--output-dir", required=True)

    adapter_parser = subparsers.add_parser("run-manual-adapter", help="Run a local/manual adapter for non-default or controlled sources")
    adapter_parser.add_argument("--adapter", required=True, choices=sorted(ADAPTER_FUNCTIONS.keys()))
    adapter_parser.add_argument("--input", required=True)
    adapter_parser.add_argument("--output")
    adapter_parser.add_argument("--dataset-id", default="manual_adapter_dataset")

    support_parser = subparsers.add_parser("generate-support-matrix", help="Emit source support matrix artifacts")
    support_parser.add_argument("--output-markdown", default="docs/source_support_matrix.md")
    support_parser.add_argument("--output-json", default="docs/source_support_matrix.json")

    benchmark_parser = subparsers.add_parser("benchmark-prep", help="Prepare benchmark datasets and baseline reports")
    benchmark_parser.add_argument("--input-dir", default="examples/output")
    benchmark_parser.add_argument("--output-dir", default="benchmarks/example")
    benchmark_parser.add_argument("--config", default="configs/benchmark_prep.yaml")

    evaluation_parser = subparsers.add_parser("evaluate-predictions", help="Score an external model prediction file against COD")
    evaluation_parser.add_argument("--input-dir", default="examples/output")
    evaluation_parser.add_argument("--predictions", required=True)
    evaluation_parser.add_argument("--output-dir", default="evaluations/example")

    report_parser = subparsers.add_parser("report-build", help="Generate summary stats for a materialized build")
    report_parser.add_argument("--input-dir", default="examples/output")
    report_parser.add_argument("--output", default="")

    explorer_parser = subparsers.add_parser("launch-explorer", help="Launch the Streamlit COD Explorer")
    explorer_parser.add_argument("--data-dir", default="examples/output")

    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]

    if args.command == "export-schema":
        target = export_json_schema(root)
        print(target)
    elif args.command == "fetch-fixtures":
        target = copy_fixture_raw(root=root, output_dir=root / args.output_dir)
        print(target)
    elif args.command == "fetch-real":
        artifacts = fetch_real_public_subset(root=root, config_path=root / args.config, output_dir=root / args.output_dir)
        for artifact in artifacts:
            print(f"{artifact.source_name} records={artifact.normalized_count} path={artifact.records_path}")
    elif args.command == "fetch-source":
        artifacts = fetch_real_public_subset(root=root, config_path=root / args.config, output_dir=root / args.output_dir, source_filter=args.source)
        for artifact in artifacts:
            print(f"{artifact.source_name} records={artifact.normalized_count} path={artifact.records_path}")
    elif args.command == "normalize-source":
        source = root / args.input
        output_dir = root / args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / Path(args.input).name
        rows = []
        for line in source.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        target.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")
        print(target)
    elif args.command == "run-manual-adapter":
        adapter = ADAPTER_FUNCTIONS[args.adapter]
        input_path = root / args.input
        output_path = root / args.output if args.output else input_path.with_suffix(".normalized.jsonl")
        kwargs = {"dataset_id": args.dataset_id} if "dataset_id" in adapter.__code__.co_varnames else {}
        count = adapter(input_path, output_path, **kwargs)
        print(f"{output_path} rows={count}")
    elif args.command == "materialize":
        counts = materialize_cod(root=root, raw_dir=root / args.raw_dir, output_dir=root / args.output_dir)
        for key, value in counts.items():
            print(f"{key}={value}")
    elif args.command == "generate-support-matrix":
        markdown = generate_support_matrix_markdown(root)
        markdown_path = root / args.output_markdown
        markdown_path.write_text("# Source Support Matrix\n\n" + markdown, encoding="utf-8")
        json_path = root / args.output_json
        json_path.write_text(json.dumps(load_source_support(root), indent=2, sort_keys=True), encoding="utf-8")
        print(markdown_path)
        print(json_path)
    elif args.command == "benchmark-prep":
        report = prepare_benchmarks(input_dir=root / args.input_dir, output_dir=root / args.output_dir, config_path=root / args.config)
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.command == "evaluate-predictions":
        report = evaluate_predictions(
            input_dir=root / args.input_dir,
            predictions_path=root / args.predictions,
            output_dir=root / args.output_dir,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.command == "report-build":
        output = root / args.output if args.output else (root / args.input_dir / "summary_stats.json")
        summary = write_build_summary(root / args.input_dir, output)
        print(json.dumps(summary, indent=2, sort_keys=True))
    elif args.command == "launch-explorer":
        subprocess.run(
            [
                str(root / ".venv" / "bin" / "streamlit") if (root / ".venv" / "bin" / "streamlit").exists() else "streamlit",
                "run",
                str(root / "ui" / "streamlit_app.py"),
                "--",
                str(root / args.data_dir),
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
