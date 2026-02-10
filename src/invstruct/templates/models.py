from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AnchorRule(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    roi: list[float] = Field(default_factory=lambda: [0.0, 0.0, 1.0, 1.0])
    direction: Literal["right", "below", "right_or_below"] = "right_or_below"


class ScoringRule(BaseModel):
    ocr_conf_weight: float = 0.4
    regex_weight: float = 0.3
    layout_weight: float = 0.3


class TemplateDuplicateOverride(BaseModel):
    enabled: bool | None = None
    use_sha256: bool | None = None
    use_business_key: bool | None = None
    business_key_fields: list[str] | None = None


class TemplateAmountMismatchOverride(BaseModel):
    enabled: bool | None = None
    tolerance: float | None = None


class TemplateLowConfOverride(BaseModel):
    enabled: bool | None = None
    threshold: float | None = None
    require_core_fields: bool | None = None
    missing_severity: Literal["info", "warning", "critical"] | None = None


class TemplateAnomalyOverrides(BaseModel):
    duplicate: TemplateDuplicateOverride | None = None
    amount_mismatch: TemplateAmountMismatchOverride | None = None
    low_conf: TemplateLowConfOverride | None = None


class TemplateSpec(BaseModel):
    template_id: str
    version: str = "1.0.0"
    locale: str = "zh-CN"
    doc_type: str = "receipt"
    aliases: dict[str, list[str]] = Field(default_factory=dict)
    regex: dict[str, str] = Field(default_factory=dict)
    anchors: dict[str, AnchorRule] = Field(default_factory=dict)
    scoring: ScoringRule = Field(default_factory=ScoringRule)
    validators: list[dict] = Field(default_factory=list)
    anomalies: TemplateAnomalyOverrides | None = None
