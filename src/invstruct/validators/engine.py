from __future__ import annotations

import re
from typing import Any


def _is_missing(value: Any) -> bool:
    return value is None or value == ""


def run_validators(record: dict[str, Any], validators: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for validator in validators:
        v_type = validator.get("type")
        field = validator.get("field")
        severity = validator.get("severity", "warning")
        value = record.get(field)

        if v_type == "required":
            if _is_missing(value):
                issues.append({"type": "required", "field": field, "severity": severity, "message": "field required"})
        elif v_type == "gt":
            threshold = validator.get("value")
            if value is None or not (float(value) > float(threshold)):
                issues.append({"type": "gt", "field": field, "severity": severity, "message": f"must be > {threshold}"})
        elif v_type == "lt":
            threshold = validator.get("value")
            if value is None or not (float(value) < float(threshold)):
                issues.append({"type": "lt", "field": field, "severity": severity, "message": f"must be < {threshold}"})
        elif v_type == "eq":
            expected = validator.get("value")
            if value != expected:
                issues.append({"type": "eq", "field": field, "severity": severity, "message": f"must equal {expected}"})
        elif v_type == "regex":
            pattern = validator.get("pattern")
            if value is None or pattern is None or not re.search(str(pattern), str(value)):
                issues.append({"type": "regex", "field": field, "severity": severity, "message": "regex mismatch"})
    return issues

