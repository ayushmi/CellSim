from pathlib import Path

from cod.materialize import materialize_cod


def test_materialize_example_outputs(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    counts = materialize_cod(root=root, raw_dir=root / "examples" / "raw", output_dir=tmp_path)

    assert counts["events"] == 8
    assert counts["metabolome_values"] >= 2
    assert (tmp_path / "cod_events.jsonl").exists()
    assert (tmp_path / "cod_events.parquet").exists()

    rows = (tmp_path / "cod_events.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(rows) == 8
    assert any("activate_interferon_program" in row for row in rows)
