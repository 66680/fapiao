from __future__ import annotations

import json
from pathlib import Path

from invstruct.api.app import app


def main() -> int:
    target = Path("docs/api/openapi.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = app.openapi()
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"openapi dumped: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
