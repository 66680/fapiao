import json
from pathlib import Path

import pytest

from invstruct.extractors.rules import extract_fields
from invstruct.ocr.base import OcrTextBlock


def _load_cases() -> list[dict]:
    root = Path(__file__).parent / "fixtures" / "blocks_cases"
    cases: list[dict] = []
    for path in sorted(root.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_file"] = path.name
        cases.append(payload)
    return cases


@pytest.mark.parametrize("case", _load_cases(), ids=lambda case: case["name"])
def test_rules_benchmark_cases(case: dict) -> None:
    blocks = [
        OcrTextBlock(
            text=item["text"],
            bbox=item.get("bbox", []),
            conf=float(item.get("conf", 0.9)),
            page=int(item.get("page", 1)),
        )
        for item in case["blocks"]
    ]
    debug_data: dict = {}
    extracted = extract_fields(
        blocks,
        locale="zh-CN",
        currency="CNY",
        low_conf=0.75,
        debug_collector=debug_data,
    )

    assert "total_amount_gross" in extracted, case["_file"]
    assert "issue_date" in extracted, case["_file"]

    optional_hits = [field for field in ("merchant_name", "invoice_number", "merchant_tax_id") if field in extracted]
    assert optional_hits, case["_file"]

    amount_conf = float(extracted["total_amount_gross"][1])
    assert amount_conf >= float(case["expect"]["amount_min_conf"]), case["_file"]
    assert str(extracted["issue_date"][0]) == case["expect"]["date"], case["_file"]

    if "invoice" in case["expect"]:
        assert str(extracted["invoice_number"][0]) == case["expect"]["invoice"], case["_file"]
    if "tax" in case["expect"]:
        assert str(extracted["merchant_tax_id"][0]) == case["expect"]["tax"], case["_file"]
    if "merchant" in case["expect"]:
        assert case["expect"]["merchant"].lower() in str(extracted["merchant_name"][0]).lower(), case["_file"]

    prov = extracted["total_amount_gross"][2]
    assert prov.page >= 1
    assert prov.line_text

    assert "normalized_lines" in debug_data
    assert "candidates" in debug_data
    assert "selected" in debug_data

