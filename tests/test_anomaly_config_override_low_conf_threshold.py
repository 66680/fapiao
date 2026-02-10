from __future__ import annotations

from datetime import date

from invstruct.anomalies.engine import attach_anomalies
from invstruct.config import AnomalyConfig, LowConfConfig
from invstruct.schemas import Confidence, InvoiceRecord, SourceInfo


def test_anomaly_config_override_low_conf_threshold() -> None:
    record = InvoiceRecord(
        doc_id="doc-1",
        merchant_name="Store A",
        issue_date=date(2026, 2, 9),
        total_amount_gross=20.0,
        confidence=Confidence(overall=0.7),
        source=SourceInfo(file_name="a.png", sha256="a" * 64, trace_id="t-1"),
    )
    cfg = AnomalyConfig(low_conf=LowConfConfig(threshold=0.6))
    result = attach_anomalies([record], config=cfg)[0]
    codes = {item.code for item in result.anomalies}
    assert "LOW_CONFIDENCE" not in codes
