from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from invstruct.api.app import app


def test_api_export_preview_returns_rows_and_stats(tmp_path: Path) -> None:
    records = tmp_path / "records.jsonl"
    payload = {
        "doc_id": "doc-1",
        "merchant_name": "Store A",
        "issue_date": "2026-02-09",
        "total_amount_gross": 12.34,
        "currency": "CNY",
        "source": {"file_name": "a.png", "sha256": "a" * 64, "trace_id": "trace-1"},
    }
    records.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")

    client = TestClient(app)
    with records.open("rb") as handle:
        response = client.post(
            "/v1/export/preview?limit=10",
            files={"records": ("records.jsonl", handle, "application/json")},
            data={"template_id": "generic_expense_v1"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["template_id"] == "generic_expense_v1"
    assert "columns" in body
    assert "rows" in body
    assert len(body["rows"]) == 1
    assert "stats" in body
    assert "fallback_usage_by_column" in body["stats"]
