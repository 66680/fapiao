from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from invstruct.cli import app
from invstruct.utils.hash import canonical_json_sha256


def test_merge_conflict_traceability_hashes(tmp_path: Path) -> None:
    left = tmp_path / "left.jsonl"
    right = tmp_path / "right.jsonl"
    merged = tmp_path / "merged.jsonl"

    dropped_row = {
        "doc_id": "doc-1",
        "status": "skipped",
        "confidence": {"overall": 0.2, "fields": {}},
        "source": {"file_name": "a.png", "sha256": "a" * 64, "trace_id": "t-1"},
    }
    kept_row = {
        "doc_id": "doc-2",
        "status": "success",
        "confidence": {"overall": 0.9, "fields": {}},
        "source": {"file_name": "a.png", "sha256": "a" * 64, "trace_id": "t-2"},
    }
    left.write_text(json.dumps(dropped_row, ensure_ascii=False) + "\n", encoding="utf-8")
    right.write_text(json.dumps(kept_row, ensure_ascii=False) + "\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["merge", str(left), str(right), "--out", str(merged)])
    assert result.exit_code == 0, result.stdout

    report = json.loads((tmp_path / "merge_report.json").read_text(encoding="utf-8"))
    assert report["snapshot_hash_algorithm"] == "sha256(canonical_json)"
    assert report["conflicts"]
    first = report["conflicts"][0]
    assert len(first["kept_snapshot_hash"]) == 64
    assert len(first["dropped"][0]["snapshot_hash"]) == 64
    assert first["kept_snapshot_hash"] == canonical_json_sha256(kept_row)
    assert first["dropped"][0]["snapshot_hash"] == canonical_json_sha256(dropped_row)
