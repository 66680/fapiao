from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from invstruct.cli import app


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def test_merge_dedup_profiles(tmp_path: Path) -> None:
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    out_strict = tmp_path / "strict.jsonl"
    out_business = tmp_path / "business.jsonl"
    out_temporal = tmp_path / "temporal.jsonl"

    row_1 = {
        "doc_id": "doc-a",
        "merchant_name": "My Store LLC",
        "issue_date": "2026-02-10",
        "total_amount_gross": 88.2,
        "currency": "CNY",
        "status": "skipped",
        "retry_key": "abc:10:1700000000",
        "source": {"file_name": "invoice.png", "sha256": "", "trace_id": "t1"},
        "confidence": {"overall": 0.2, "fields": {}},
    }
    row_2 = {
        "doc_id": "doc-b",
        "merchant_name": "MY   STORE LLC",
        "issue_date": "2026-02-10",
        "total_amount_gross": 88.2,
        "currency": "CNY",
        "status": "success",
        "retry_key": "def:11:1700000000",
        "source": {"file_name": "invoice.png", "sha256": "", "trace_id": "t2"},
        "confidence": {"overall": 0.95, "fields": {}},
    }

    _write_jsonl(a, [row_1])
    _write_jsonl(b, [row_2])

    runner = CliRunner()

    strict = runner.invoke(app, ["merge", str(a), str(b), "--out", str(out_strict)])
    assert strict.exit_code == 0, strict.stdout
    strict_rows = [json.loads(line) for line in out_strict.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(strict_rows) == 2

    business = runner.invoke(
        app,
        ["merge", str(a), str(b), "--dedup-profile", "business_key_hybrid", "--out", str(out_business)],
    )
    assert business.exit_code == 0, business.stdout
    business_rows = [json.loads(line) for line in out_business.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(business_rows) == 1
    assert business_rows[0]["status"] == "success"

    temporal = runner.invoke(
        app,
        ["merge", str(a), str(b), "--dedup-profile", "temporal_window", "--out", str(out_temporal)],
    )
    assert temporal.exit_code == 0, temporal.stdout
    temporal_rows = [json.loads(line) for line in out_temporal.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(temporal_rows) == 1
    assert temporal_rows[0]["status"] == "success"

    report = json.loads((out_temporal.with_name("merge_report.json")).read_text(encoding="utf-8"))
    assert report["dedup_profile"] == "temporal_window"
    assert report["key_type_stats"]
