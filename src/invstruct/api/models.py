from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class ParseResponse(BaseModel):
    trace_id: str
    record: dict[str, Any]


class BatchSubmitResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    created_at: str | None = None
    updated_at: str | None = None
    n_files: int | None = None
    bytes: int | None = None


class JobResultsResponse(BaseModel):
    job_id: str
    status: str
    records: list[dict[str, Any]] = Field(default_factory=list)
    failures: list[dict[str, Any]] = Field(default_factory=list)


class ExportTemplateMeta(BaseModel):
    template_id: str
    version: str
    description: str = ""
    columns: int


class ExportTemplateListResponse(BaseModel):
    templates: list[ExportTemplateMeta] = Field(default_factory=list)


class ExportPreviewStats(BaseModel):
    input_rows: int
    preview_rows: int
    truncated: bool
    fallback_usage_by_column: dict[str, dict[str, int]] = Field(default_factory=dict)
    source_usage_by_column: dict[str, dict[str, int]] = Field(default_factory=dict)
    invalid_rows: int | None = None
    has_more: bool | None = None
    total_records: int | None = None


class ExportPreviewResponse(BaseModel):
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    stats: ExportPreviewStats
    template_id: str
    job_id: str | None = None
