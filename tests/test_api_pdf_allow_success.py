from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from invstruct.api.app import app
from pdf_test_utils import write_text_pdf

pdfplumber = pytest.importorskip("pdfplumber")


def test_api_pdf_allow_success(tmp_path: Path) -> None:
    sample_pdf = tmp_path / "sample.pdf"
    write_text_pdf(sample_pdf, pages=[["My Store LLC", "Date 2026-02-09", "Total Amount 123.45"]])

    client = TestClient(app)
    with sample_pdf.open("rb") as handle:
        response = client.post(
            "/v1/parse?allow_pdf=true",
            files={"file": ("sample.pdf", handle, "application/pdf")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert "record" in payload
    record = payload["record"]
    assert record["status"] == "success"
    assert record["source"]["trace_id"]
    assert len(record["source"]["sha256"]) == 64

