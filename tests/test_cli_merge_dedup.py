from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from invstruct.cli import app


def test_cli_merge_dedup_prefers_success_and_writes_report(tmp_path: Path) -> None:
    file_a = tmp_path / "a.jsonl"
    file_b = tmp_path / "b.jsonl"
    out_path = tmp_path / "merged.jsonl"

    skipped = {
        "doc_id": "doc-skipped",
        "status": "skipped",
        "confidence": {"overall": 0.2, "fields": {}},
        "source": {"file_name": "invoice.png", "sha256": "a" * 64, "trace_id": "t-s"},
    }
    success = {
        "doc_id": "doc-success",
        "status": "success",
        "confidence": {"overall": 0.9, "fields": {}},
        "source": {"file_name": "invoice.png", "sha256": "a" * 64, "trace_id": "t-ok"},
    }
    file_a.write_text(json.dumps(skipped, ensure_ascii=False) + "\n", encoding="utf-8")
    file_b.write_text(json.dumps(success, ensure_ascii=False) + "\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(app, ["merge", str(file_a), str(file_b), "--out", str(out_path)])
    assert result.exit_code == 0, result.stdout

    rows = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["status"] == "success"
    assert rows[0]["doc_id"] == "doc-success"

    report_path = tmp_path / "merge_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["input_rows"] == 2
    assert report["kept_rows"] == 1
    assert report["dropped_rows"] == 1
    assert report["reason_stats"]["status_priority"] == 1
