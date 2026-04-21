from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_source_contracts(root: Path) -> dict[str, Any]:
    return load_yaml(root / "schemas" / "contracts" / "source_family_contracts.yaml")


def load_action_ontology(root: Path) -> dict[str, Any]:
    return load_yaml(root / "schemas" / "ontology" / "action_ontology.yaml")


def load_benchmark_splits(root: Path) -> dict[str, Any]:
    return load_yaml(root / "schemas" / "ontology" / "benchmark_splits.yaml")
