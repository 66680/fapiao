from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

CHANGELOG_CANDIDATES = ("CHANGELOG.md", "docs/CHANGELOG.md")
VERSION_HEADING_TEMPLATE = r"^##\s+v?{version}\s*$"
SCHEMA_NOTE_PATTERN = re.compile(r"(schema:|migration notes)", re.IGNORECASE)
VERSION_RE = re.compile(r"^\s*(RECORD_SCHEMA_VERSION|EXPORT_SCHEMA_VERSION)\s*=\s*(\d+)\s*$", re.MULTILINE)


def parse_versions(content: str) -> dict[str, int | None]:
    values: dict[str, int | None] = {
        "RECORD_SCHEMA_VERSION": None,
        "EXPORT_SCHEMA_VERSION": None,
    }
    for key, raw in VERSION_RE.findall(content):
        values[key] = int(raw)
    return values


def versions_changed(base_content: str, head_content: str) -> bool:
    base = parse_versions(base_content)
    head = parse_versions(head_content)
    return any(base[key] != head[key] for key in base)


def _extract_version(raw: str) -> str | None:
    value = raw.strip()
    if not value:
        return None
    match = re.search(r"v?(\d+\.\d+\.\d+)$", value)
    return match.group(1) if match else None


def _find_changelog(root: Path) -> Path | None:
    for candidate in CHANGELOG_CANDIDATES:
        path = root / candidate
        if path.exists():
            return path
    return None


def _extract_section(content: str, version: str) -> str | None:
    pattern = re.compile(VERSION_HEADING_TEMPLATE.format(version=re.escape(version)), re.MULTILINE)
    hit = pattern.search(content)
    if hit is None:
        return None
    next_heading = re.compile(r"^##\s+.+$", re.MULTILINE).search(content, hit.end())
    end = next_heading.start() if next_heading else len(content)
    return content[hit.end() : end].strip()


def _read_previous_schema(root: Path) -> str:
    result = subprocess.run(
        ["git", "show", "HEAD~1:src/invstruct/schema_version.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def evaluate_changelog_consistency(
    *,
    root: Path,
    version: str,
    previous_schema_content: str,
    current_schema_content: str,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "ok": False,
        "version": version,
        "path": None,
        "reason": "",
        "schema_versions": {
            "current": parse_versions(current_schema_content),
            "previous": parse_versions(previous_schema_content),
            "changed": versions_changed(previous_schema_content, current_schema_content)
            if previous_schema_content
            else False,
        },
    }

    changelog = _find_changelog(root)
    if changelog is None:
        report["reason"] = "changelog_not_found"
        return report
    report["path"] = str(changelog.relative_to(root))

    content = changelog.read_text(encoding="utf-8", errors="ignore")
    section = _extract_section(content, version)
    if section is None:
        report["reason"] = "version_heading_not_found"
        return report

    if report["schema_versions"]["changed"] and SCHEMA_NOTE_PATTERN.search(section) is None:
        report["reason"] = "schema_changed_without_migration_notes"
        return report

    report["ok"] = True
    report["reason"] = "ok"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check release changelog consistency.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="out/changelog_report.json")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    output = Path(args.output)
    output_path = (root / output).resolve() if not output.is_absolute() else output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    raw_version = os.getenv("INVSTRUCT_VERSION", "").strip() or os.getenv("GITHUB_REF_NAME", "").strip()
    version = _extract_version(raw_version)
    if version is None:
        report = {
            "ok": False,
            "version": raw_version,
            "path": None,
            "reason": "version_not_provided",
            "schema_versions": {},
        }
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 2

    schema_path = root / "src/invstruct/schema_version.py"
    current_schema = schema_path.read_text(encoding="utf-8", errors="ignore")
    previous_schema = _read_previous_schema(root)
    report = evaluate_changelog_consistency(
        root=root,
        version=version,
        previous_schema_content=previous_schema,
        current_schema_content=current_schema,
    )
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())

