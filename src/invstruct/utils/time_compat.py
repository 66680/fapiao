from __future__ import annotations

import datetime as _dt

UTC = getattr(_dt, "UTC", _dt.timezone.utc)


def utc_now() -> _dt.datetime:
    return _dt.datetime.now(UTC)

