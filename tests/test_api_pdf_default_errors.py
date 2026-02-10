from pathlib import Path

from fastapi.testclient import TestClient

from invstruct.api.app import app
from pdf_test_utils import write_text_pdf


def test_api_pdf_default_errors(tmp_path: Path) -> None:
    sample_pdf = tmp_path / "sample.pdf"
    write_text_pdf(sample_pdf, pages=[["Total Amount 123.45"]])

    client = TestClient(app)
    with sample_pdf.open("rb") as handle:
        response = client.post(
            "/v1/parse",
            files={"file": ("sample.pdf", handle, "application/pdf")},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "E3001"

