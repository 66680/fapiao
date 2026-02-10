from __future__ import annotations

from datetime import date
from pathlib import Path

from invstruct.schemas import Confidence, InvoiceRecord, SourceInfo
from invstruct.utils.hash import sha256_file


def parse_with_mock(file_path: str | Path, trace_id: str) -> InvoiceRecord:
    input_path = Path(file_path)
    return InvoiceRecord(
        doc_id=f"doc-{trace_id[:8]}",
        doc_type="unknown",
        issue_date=date.today(),
        total_amount_gross=0.01,
        confidence=Confidence(overall=0.0, fields={}),
        source=SourceInfo(file_name=input_path.name, sha256=sha256_file(input_path), trace_id=trace_id),
    )
