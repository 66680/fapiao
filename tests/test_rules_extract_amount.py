from invstruct.extractors.rules import extract_fields
from invstruct.ocr.base import OcrTextBlock


def test_amount_prefers_total_line_then_max_fallback() -> None:
    blocks = [
        OcrTextBlock(text="Line item 12.00", bbox=[0, 0, 1, 1], conf=0.9, page=1),
        OcrTextBlock(text="Amount Due: 88.50", bbox=[0, 2, 1, 3], conf=0.8, page=1),
        OcrTextBlock(text="Random value 120.00", bbox=[0, 4, 1, 5], conf=0.7, page=1),
    ]

    extracted = extract_fields(blocks, locale="en-US", currency="USD", low_conf=0.7)
    assert extracted["total_amount_gross"][0] == 88.5

