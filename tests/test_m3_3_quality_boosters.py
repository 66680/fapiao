from __future__ import annotations

import runpy
import sys
from datetime import date

from invstruct.anomalies import attach_anomalies
from invstruct.normalize.common import normalize_amount, normalize_date
from invstruct.templates.models import TemplateSpec
from invstruct.templates.registry import TemplateRegistry


def test_module_main_executes_cli_main(monkeypatch):
    called = {"ok": False}

    def fake_main():
        called["ok"] = True

    monkeypatch.setattr("invstruct.cli.main", fake_main)
    sys.modules.pop("invstruct.__main__", None)
    runpy.run_module("invstruct.__main__", run_name="__main__")

    assert called["ok"] is True


def test_anomalies_package_attach_wrapper_smoke():
    assert attach_anomalies([]) == []


def test_template_registry_fallback_get_and_empty_case():
    receipt_cn = TemplateSpec(template_id="t1", version="1.0.0", locale="zh-CN", doc_type="receipt")
    receipt_en = TemplateSpec(template_id="t2", version="1.0.0", locale="en-US", doc_type="receipt")

    registry = TemplateRegistry([receipt_cn, receipt_en])

    selected_fallback = registry.select([], doc_type="receipt", locale="ja-JP")
    assert selected_fallback is not None
    assert selected_fallback.template_id == "t1"

    assert registry.get("t2") is not None
    assert registry.get("not-exist") is None

    empty = TemplateRegistry([])
    assert empty.select([], doc_type="x", locale="y") is None


def test_normalize_common_date_and_amount_paths():
    assert normalize_date(None) is None
    assert normalize_date("2026-02-11") == date(2026, 2, 11)
    assert normalize_date("2026/02/30") is None

    assert normalize_amount(None) is None
    assert normalize_amount("abc") is None
    assert normalize_amount("CNY 1,234.567") == 1234.56
