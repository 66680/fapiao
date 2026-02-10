from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Anomaly(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "critical"] = "warning"
    details: dict[str, Any] = Field(default_factory=dict)
