from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    E1001 = "E1001"
    E2001 = "E2001"
    E3001 = "E3001"
    E3002 = "E3002"
    E4001 = "E4001"
    E5001 = "E5001"


class ErrorDetail(BaseModel):
    code: ErrorCode
    message: str
    trace_id: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


def error_payload(
    code: ErrorCode,
    message: str,
    trace_id: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    envelope = ErrorEnvelope(
        error=ErrorDetail(
            code=code,
            message=message,
            trace_id=trace_id,
            details=details or {},
        )
    )
    return envelope.model_dump(mode="json")


# Backward compatibility alias
as_error_payload = error_payload


class InvstructError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        trace_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.trace_id = trace_id
        self.details = details or {}

    def to_envelope(self) -> ErrorEnvelope:
        return ErrorEnvelope(
            error=ErrorDetail(
                code=self.code,
                message=self.message,
                trace_id=self.trace_id,
                details=self.details,
            )
        )


class InputError(InvstructError):
    pass


class OcrError(InvstructError):
    pass


class ExtractError(InvstructError):
    pass


class TemplateError(InvstructError):
    pass


class ExportError(InvstructError):
    pass
