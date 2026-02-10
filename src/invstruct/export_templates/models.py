from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


TransformType = Literal["as_is", "date_iso", "amount_2dp", "anomaly_codes_join"]
TRANSFORM_WHITELIST: tuple[str, ...] = ("as_is", "date_iso", "amount_2dp", "anomaly_codes_join")
CandidateStrategyType = Literal["first_non_empty", "prefer_primary_source", "highest_confidence"]


class ExportColumnSpec(BaseModel):
    name: str
    source: str | None = None
    source_candidates: list[str] | None = None
    transform: TransformType = "as_is"
    candidate_strategy: CandidateStrategyType = "first_non_empty"
    default: str | int | float | None = None
    required: bool = False

    @model_validator(mode="after")
    def validate_source_config(self) -> "ExportColumnSpec":
        source = (self.source or "").strip()
        candidates = self.source_candidates or []
        normalized_candidates = [item.strip() for item in candidates if isinstance(item, str) and item.strip()]
        if source:
            self.source = source
        elif self.source is not None:
            self.source = None
        self.source_candidates = normalized_candidates or None
        if not self.source and not self.source_candidates:
            raise ValueError("Either source or source_candidates must be provided")
        return self


class ExportTemplateSpec(BaseModel):
    template_id: str
    version: str = "1.0.0"
    description: str = ""
    columns: list[ExportColumnSpec] = Field(default_factory=list)
