from invstruct.extractors.rules import extract_fields
from invstruct.ocr.base import OcrTextBlock


def test_provenance_contains_bbox_page_line_text() -> None:
    blocks = [
        OcrTextBlock(text="My Store LLC", bbox=[10, 10, 120, 20], conf=0.95, page=2),
        OcrTextBlock(text="Total 12.34", bbox=[10, 30, 120, 40], conf=0.95, page=2),
    ]

    extracted = extract_fields(blocks, locale="en-US", currency="USD", low_conf=0.7)
    prov = extracted["merchant_name"][2]
    assert prov.bbox
    assert prov.page == 2
    assert prov.line_id >= 0
    assert prov.line_text

