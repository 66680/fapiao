from __future__ import annotations

from typing import Any

from invstruct.export_templates.models import ExportTemplateSpec
from invstruct.exporters.mapped_csv import TRANSFORMS, _is_missing_value, resolve_source_value
from invstruct.schemas import InvoiceRecord


def _to_payload(row: InvoiceRecord | dict[str, Any]) -> dict[str, Any]:
    if isinstance(row, InvoiceRecord):
        return row.to_dict()
    if isinstance(row, dict):
        return row
    return {}


def preview_mapped(
    rows: list[InvoiceRecord | dict[str, Any]],
    template: ExportTemplateSpec,
    limit: int = 20,
) -> dict[str, Any]:
    capped = max(0, limit)
    selected = rows[:capped]
    output_rows: list[dict[str, Any]] = []
    fallback_usage_by_column: dict[str, dict[str, int]] = {}
    source_usage_by_column: dict[str, dict[str, int]] = {}
    headers = [column.name for column in template.columns]

    for row in selected:
        payload = _to_payload(row)
        rendered: dict[str, Any] = {}
        for column in template.columns:
            raw_value, used_source, used_index = resolve_source_value(payload, column)
            transformed = TRANSFORMS[column.transform](raw_value)
            value = column.default if _is_missing_value(transformed) else transformed
            rendered[column.name] = value

            fallback_stats = fallback_usage_by_column.setdefault(
                column.name,
                {"source_primary": 0, "source_fallback": 0, "default_or_missing": 0},
            )
            if used_source is None:
                fallback_stats["default_or_missing"] += 1
            elif (used_index or 0) == 0:
                fallback_stats["source_primary"] += 1
            else:
                fallback_stats["source_fallback"] += 1

            if used_source:
                by_source = source_usage_by_column.setdefault(column.name, {})
                by_source[used_source] = by_source.get(used_source, 0) + 1

        output_rows.append(rendered)

    return {
        "columns": headers,
        "rows": output_rows,
        "stats": {
            "input_rows": len(rows),
            "preview_rows": len(output_rows),
            "truncated": len(rows) > len(output_rows),
            "fallback_usage_by_column": fallback_usage_by_column,
            "source_usage_by_column": source_usage_by_column,
        },
    }
