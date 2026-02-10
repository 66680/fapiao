from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from invstruct.api.app import app


def test_api_batch_export_response_model_regression(tmp_path: Path) -> None:
    sample = tmp_path / "sample.png"
    sample.write_bytes(b"fake")

    client = TestClient(app)
    with sample.open("rb") as handle:
        batch_resp = client.post("/v1/batch?sync=true", files=[("files", ("sample.png", handle, "image/png"))])
    assert batch_resp.status_code == 200
    job_id = batch_resp.json()["job_id"]

    file_resp = client.get(f"/v1/jobs/{job_id}/export", params={"kind": "details_csv"})
    assert file_resp.status_code == 200
    assert "text/csv" in file_resp.headers.get("content-type", "")

    json_resp = client.get(f"/v1/jobs/{job_id}/export", params={"kind": "unknown_kind"})
    assert json_resp.status_code == 400
    payload = json_resp.json()
    assert payload["error"]["code"] == "E1001"
    assert payload["error"]["message"] == "unknown export kind"
