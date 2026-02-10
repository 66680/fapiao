from __future__ import annotations

import argparse
import re
from pathlib import Path


def _load_project_version(pyproject_path: Path) -> str | None:
    text = pyproject_path.read_text(encoding="utf-8")
    match = re.search(r'(?ms)^\[project\]\n.*?^version\s*=\s*"([^"]+)"\s*$', text)
    if not match:
        return None
    return match.group(1)


def _extract_section(changelog_text: str, version: str) -> str | None:
    pattern = re.compile(
        rf"(?ms)^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)",
    )
    match = pattern.search(changelog_text)
    if not match:
        return None
    return match.group(1).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate release notes from CHANGELOG.md")
    parser.add_argument("--version", help="Version section to extract (defaults to pyproject version)")
    parser.add_argument("--out", help="Output path", default=None)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    changelog_path = repo_root / "CHANGELOG.md"
    if not changelog_path.exists():
        raise FileNotFoundError("CHANGELOG.md not found")

    version = args.version or _load_project_version(repo_root / "pyproject.toml")
    if not version:
        raise ValueError("Could not determine target version")

    changelog_text = changelog_path.read_text(encoding="utf-8")
    section = _extract_section(changelog_text, version)
    if not section:
        raise ValueError(f"Could not find section for version [{version}] in CHANGELOG.md")

    output_path = Path(args.out) if args.out else repo_root / "release" / f"release_notes_{version}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"# Release Notes {version}\n\n{section}\n", encoding="utf-8")
    print(f"release notes: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
