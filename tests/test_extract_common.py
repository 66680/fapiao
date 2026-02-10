from invstruct.extractors.common import extract_fields
from invstruct.ocr.base import OcrTextBlock


def test_extract_fields_from_blocks() -> None:
    blocks = [
        OcrTextBlock(text="星河酒店有限公司", bbox=[0, 0, 120, 20], conf=0.98, page=1),
        OcrTextBlock(text="开票日期: 2026年2月9日", bbox=[0, 20, 120, 40], conf=0.95, page=1),
        OcrTextBlock(text="价税合计: ¥123.45", bbox=[0, 40, 120, 60], conf=0.96, page=1),
        OcrTextBlock(text="纳税人识别号: 91350100MA12345678", bbox=[0, 60, 120, 80], conf=0.93, page=1),
        OcrTextBlock(text="发票号: 202602090001", bbox=[0, 80, 120, 100], conf=0.94, page=1),
    ]

    extracted = extract_fields(blocks)

    assert extracted["merchant_name"][0] == "星河酒店有限公司"
    assert "2026" in str(extracted["issue_date"][0])
    assert "123.45" in str(extracted["total_amount_gross"][0])
    assert extracted["merchant_tax_id"][0] == "91350100MA12345678"
    assert extracted["invoice_number"][0] == "202602090001"

