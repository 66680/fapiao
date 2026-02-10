from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def _parse_max_annotations(raw: str | None, default: int = 5) -> int:
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _escape(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _truncate(value: str, limit: int = 800) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def _emit(level: str, title: str, message: str) -> None:
    print(f"::{level} title={_escape(title)}::{_escape(_truncate(message))}")


def _emit_notice(title: str, message: str) -> None:
    print(f"::notice title={_escape(title)}::{_escape(_truncate(message))}")


def _step_message(step: dict[str, Any]) -> str:
    name = str(step.get("name", "unknown"))
    command = step.get("command")
    if isinstance(command, list):
        command_text = " ".join(str(item) for item in command)
    else:
        command_text = str(command or "")
    tail_parts: list[str] = []
    stdout_tail = str(step.get("stdout_tail", "")).strip()
    stderr_tail = str(step.get("stderr_tail", "")).strip()
    if stdout_tail:
        tail_parts.extend(stdout_tail.splitlines()[-8:])
    if stderr_tail:
        tail_parts.extend(stderr_tail.splitlines()[-8:])
    tail_text = " | ".join(part.strip() for part in tail_parts if part.strip())
    if tail_text:
        return f"step={name}; command={command_text}; tail={tail_text}"
    return f"step={name}; command={command_text}"


def emit_annotations_from_report(
    report_path: str | Path,
    *,
    level: str,
    max_annotations: int,
) -> int:
    path = Path(report_path)
    if not path.exists():
        _emit_notice("invstruct gate report", f"report not found: {path}")
        return 0

    report = json.loads(path.read_text(encoding="utf-8"))
    if bool(report.get("ok", False)):
        _emit_notice("invstruct gates", f"CI gates ok + report path: {path}")
        return 0

    emitted = 0
    failed_step = str(report.get("failed_step", "")).strip()
    if failed_step and emitted < max_annotations:
        _emit(level, "invstruct gate failed", f"failed_step={failed_step}; report={path}")
        emitted += 1

    for step in report.get("steps", []):
        if emitted >= max_annotations:
            break
        if not isinstance(step, dict):
            continue
        return_code = int(step.get("returncode", 0))
        step_ok = bool(step.get("ok", return_code == 0))
        if step_ok and return_code == 0:
            continue
        _emit(level, "invstruct gate step", _step_message(step))
        emitted += 1

    for command in report.get("reproduce_commands", []):
        _emit_notice("invstruct reproduce", str(command))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit CI annotations from gate report.")
    parser.add_argument("--report", default=os.getenv("INVSTRUCT_CI_REPORT", "out/ci_gate_report.json"))
    args = parser.parse_args(argv)

    level = os.getenv("INVSTRUCT_ANNOTATION_LEVEL", "error").strip().lower()
    if level not in {"error", "warning"}:
        level = "error"
    max_annotations = _parse_max_annotations(os.getenv("INVSTRUCT_ANNOTATION_MAX"), default=5)
    return emit_annotations_from_report(args.report, level=level, max_annotations=max_annotations)


if __name__ == "__main__":
    raise SystemExit(main())

