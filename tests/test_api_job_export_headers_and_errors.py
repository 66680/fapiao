from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from invstruct.api.app import app


def test_api_job_export_headers_and_errors(tmp_path: Path) -> None:
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

    report_resp = client.get(f"/v1/jobs/{job_id}/export", params={"kind": "report_xlsx"})
    assert report_resp.status_code == 200
    assert report_resp.headers.get("content-type", "").startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert f'filename="{job_id}_report.xlsx"' in report_resp.headers.get("content-disposition", "")

    details_resp = client.get(f"/v1/jobs/{job_id}/export", params={"kind": "details_csv"})
    assert details_resp.status_code == 200
    assert details_resp.headers.get("content-type", "").startswith("text/csv")
    assert f'filename="{job_id}_details.csv"' in details_resp.headers.get("content-disposition", "")

    bad_resp = client.get(f"/v1/jobs/{job_id}/export", params={"kind": "unknown_kind"})
    assert bad_resp.status_code == 400
    error = bad_resp.json()["error"]
    assert error["code"] == "E1001"
