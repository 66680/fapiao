from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi.testclient import TestClient

from invstruct.api.app import app


def test_api_job_export_accounting_csv(tmp_path: Path) -> None:
    sample = tmp_path / "sample.png"
    sample.write_bytes(b"fake")

    client = TestClient(app)
    with sample.open("rb") as handle:
        response = client.post(
            "/v1/batch?sync=true",
            files=[("files", ("sample.png", handle, "image/png"))],
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"]

    export_resp = client.get(
        f"/v1/jobs/{payload['job_id']}/export",
        params={"kind": "accounting_csv", "template_id": "generic_expense_v1"},
    )
    assert export_resp.status_code == 200
    assert "text/csv" in export_resp.headers.get("content-type", "")
    assert "attachment" in export_resp.headers.get("content-disposition", "").lower()

    content = export_resp.content.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    header = next(reader)
    assert "expense_date" in header
