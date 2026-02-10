from invstruct.extractors.rules import extract_fields
from invstruct.ocr.base import OcrTextBlock


def test_rules_normalize_multiple_date_formats() -> None:
    blocks = [
        OcrTextBlock(text="Date: 2026-02-09", bbox=[0, 0, 1, 1], conf=0.9, page=1),
        OcrTextBlock(text="Invoice Date 09.02.2026", bbox=[0, 2, 1, 3], conf=0.9, page=1),
        OcrTextBlock(text="Issue 02/09/2026", bbox=[0, 4, 1, 5], conf=0.9, page=1),
    ]

    extracted = extract_fields(blocks, locale="en-US", currency="USD", low_conf=0.7)
    issue_date = extracted["issue_date"][0]
    assert str(issue_date) in {"2026-02-09", "2026-09-02"}

