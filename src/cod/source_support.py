from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_source_support(root: Path) -> dict[str, Any]:
    return yaml.safe_load((root / "configs" / "source_support_matrix.yaml").read_text(encoding="utf-8"))


def source_support_rows(root: Path) -> list[dict[str, Any]]:
    return load_source_support(root)["sources"]


def generate_support_matrix_markdown(root: Path) -> str:
    rows = source_support_rows(root)
    header = [
        "| Source | Family | Access | Automated fetch | State depth | Intervention depth | Outcome depth | Action usefulness | Status | Blockers |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    body = [
        f"| {row['source_name']} | {row['source_family']} | {row['access_class']} | {str(row['automated_fetch_available']).lower()} | "
        f"{row['state_depth']} | {row['intervention_depth']} | {row['outcome_depth']} | {row['action_usefulness']} | "
        f"{row['current_status']} | {row['blockers']} |"
        for row in rows
    ]
    return "\n".join(header + body) + "\n"
