from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def run_simple_baselines(benchmark_dataset_path: Path) -> dict[str, float | None]:
    df = pd.read_json(benchmark_dataset_path, lines=True)
    train = df[df["split"] == "train"]
    test = df[df["split"] == "test"]
    if train.empty or test.empty or train["task_state_to_action"].dropna().empty:
        return {"majority_action_accuracy": None}
    majority = train["task_state_to_action"].dropna().mode().iloc[0]
    metrics = {
        "majority_action_accuracy": float((test["task_state_to_action"] == majority).mean()),
    }
    if "source_family" in train.columns:
        mapping = train.groupby("source_family")["task_state_to_action"].agg(lambda s: s.mode().iloc[0] if not s.mode().empty else majority).to_dict()
        preds = test["source_family"].map(mapping).fillna(majority)
        metrics["source_family_majority_action_accuracy"] = float((test["task_state_to_action"] == preds).mean())
    return metrics


def write_baseline_report(benchmark_dataset_path: Path, output_path: Path) -> dict[str, float | None]:
    report = run_simple_baselines(benchmark_dataset_path)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report
