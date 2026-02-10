from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

from invstruct.anomalies.models import Anomaly


class FieldProvenance(BaseModel):
    page: int = 0
    bbox: list[float] = Field(default_factory=list)
    extractor: str = "mock"
    line_id: int = -1
    line_text: str = ""


class Confidence(BaseModel):
    overall: float = 0.0
    fields: dict[str, float] = Field(default_factory=dict)


class SourceInfo(BaseModel):
    file_name: str
    sha256: str
    trace_id: str


class InvoiceRecord(BaseModel):
    doc_id: str
    doc_type: str = "unknown"
    template_id: str | None = None
    issue_date: date | None = None
    merchant_name: str | None = None
    merchant_tax_id: str | None = None
    invoice_number: str | None = None
    currency: str = "CNY"
    total_amount_gross: float | None = None
    subtotal_amount_net: float | None = None
    tax_amount: float | None = None
    tax_rate: float | None = None
    category: str | None = None
    confidence: Confidence = Field(default_factory=Confidence)
    provenance: dict[str, FieldProvenance] = Field(default_factory=dict)
    validation_issues: list[dict[str, Any]] = Field(default_factory=list)
    status: Literal["success", "failed", "skipped"] = "success"
    error_code: str | None = None
    error_message: str | None = None
    warnings: list[dict[str, Any]] | None = None
    retry_key: str | None = None
    parser_version: str | None = None
    anomalies: list[Anomaly] = Field(default_factory=list)
    source: SourceInfo

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, raw: str) -> "InvoiceRecord":
        return cls.model_validate_json(raw)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
