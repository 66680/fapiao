from __future__ import annotations

import re
from datetime import date


def normalize_date(raw: str | None) -> date | None:
    if not raw:
        return None
    cleaned = raw.strip()

    patterns = [
        r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})",
        r"(20\d{2})年(\d{1,2})月(\d{1,2})日",
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if not match:
            continue
        year, month, day = map(int, match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def normalize_amount(raw: str | None) -> float | None:
    if not raw:
        return None
    match = re.search(r"-?\d+(?:[\.,]\d{1,2})?", raw.replace(",", ""))
    if not match:
        return None
    value = float(match.group(0).replace(",", ""))
    return round(value, 2)

