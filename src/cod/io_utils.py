from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pyarrow as pa
import pyarrow.parquet as pq

from .models import ActionLabel, CellTransitionEvent, EvidenceTraceRecord, FeatureValue


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_parquet(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, path)


def dump_models(path: Path, models: list[CellTransitionEvent | EvidenceTraceRecord | FeatureValue | ActionLabel]) -> None:
    write_jsonl(path, [item.model_dump(mode="json") for item in models])
