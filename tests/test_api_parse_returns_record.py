from pathlib import Path

from fastapi.testclient import TestClient

from invstruct.api.app import app


def test_api_parse_returns_record(tmp_path: Path) -> None:
    sample = tmp_path / "sample.png"
    sample.write_bytes(b"fake-content")

    client = TestClient(app)
    with sample.open("rb") as handle:
        response = client.post("/v1/parse", files={"file": ("sample.png", handle, "image/png")})

    assert response.status_code == 200
    payload = response.json()
    assert payload["record"]["source"]["trace_id"]
    assert payload["record"]["source"]["sha256"]

