from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from invstruct.api.app import app


def test_api_job_export_preview(tmp_path: Path) -> None:
    sample = tmp_path / "sample.png"
    sample.write_bytes(b"fake")

    client = TestClient(app)
    with sample.open("rb") as handle:
        batch_resp = client.post(
            "/v1/batch?sync=true",
            files=[("files", ("sample.png", handle, "image/png"))],
        )
    assert batch_resp.status_code == 200
    job_id = batch_resp.json()["job_id"]

    preview_resp = client.get(
        f"/v1/jobs/{job_id}/export/preview",
        params={"template_id": "generic_expense_v1", "limit": 5},
    )
    assert preview_resp.status_code == 200
    body = preview_resp.json()
    assert body["job_id"] == job_id
    assert body["template_id"] == "generic_expense_v1"
    assert "rows" in body
    assert "stats" in body
