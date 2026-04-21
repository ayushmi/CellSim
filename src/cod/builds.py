from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import load_benchmark_splits
from .source_support import load_source_support


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def build_id(prefix: str = "cod") -> str:
    return f"{prefix}_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def create_build_manifest(
    root: Path,
    output_dir: Path,
    source_manifests: list[dict[str, Any]],
    counts: dict[str, int],
    summary_stats: dict[str, Any],
    fixture_or_real: str,
) -> dict[str, Any]:
    support = load_source_support(root)
    benchmark_spec = load_benchmark_splits(root)
    manifest = {
        "build_id": build_id(),
        "schema_version": "1.0.0",
        "ontology_version": "1.0.0",
        "action_mapper_version": "1.0.0",
        "benchmark_split_version": benchmark_spec["version"],
        "source_support_matrix_version": support["version"],
        "materialization_timestamp": now_iso(),
        "output_dir": str(output_dir),
        "build_kind": fixture_or_real,
        "source_manifest_bundle": source_manifests,
        "counts": counts,
        "summary_stats": summary_stats,
    }
    write_json(output_dir / "build_manifest.json", manifest)
    return manifest
