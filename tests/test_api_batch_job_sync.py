from pathlib import Path

from fastapi.testclient import TestClient

from invstruct.api.app import app


def test_batch_job_sync_returns_results(tmp_path: Path) -> None:
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
    assert payload["status"] == "finished"

    result_resp = client.get(f"/v1/jobs/{payload['job_id']}/results")
    assert result_resp.status_code == 200
    assert len(result_resp.json().get("records", [])) >= 1

