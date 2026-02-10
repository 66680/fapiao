from __future__ import annotations

import argparse
import re
from pathlib import Path


def _read_project_version(pyproject_path: Path) -> str:
    text = pyproject_path.read_text(encoding="utf-8")
    match = re.search(r'(?ms)^\[project\]\n.*?^version\s*=\s*"([^"]+)"\s*$', text)
    if not match:
        raise ValueError("Could not find [project].version in pyproject.toml")
    return match.group(1)


def _replace_project_version(pyproject_text: str, new_version: str) -> str:
    pattern = re.compile(r'(?ms)(^\[project\]\n.*?^version\s*=\s*")([^"]+)("\s*$)')
    replaced = pattern.sub(rf"\g<1>{new_version}\g<3>", pyproject_text, count=1)
    if replaced == pyproject_text:
        raise ValueError("Could not replace [project].version in pyproject.toml")
    return replaced


def _replace_init_version(init_text: str, new_version: str) -> str:
    pattern = re.compile(r'(?m)^__version__\s*=\s*"([^"]+)"\s*$')
    replaced = pattern.sub(f'__version__ = "{new_version}"', init_text, count=1)
    if replaced == init_text:
        raise ValueError("Could not replace __version__ in src/invstruct/__init__.py")
    return replaced


def _bump_patch(version: str) -> str:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise ValueError(f"Current version is not semver: {version!r}")
    major, minor, patch = (int(part) for part in match.groups())
    return f"{major}.{minor}.{patch + 1}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Bump invstruct version")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--patch", action="store_true", help="Increment patch version")
    group.add_argument("--to", type=str, help="Set explicit semantic version")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    pyproject_path = repo_root / "pyproject.toml"
    init_path = repo_root / "src" / "invstruct" / "__init__.py"

    current = _read_project_version(pyproject_path)
    target = _bump_patch(current) if args.patch else args.to
    if not target or not re.fullmatch(r"\d+\.\d+\.\d+", target):
        raise ValueError(f"Target version must be semantic version: {target!r}")

    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    init_text = init_path.read_text(encoding="utf-8")

    pyproject_path.write_text(_replace_project_version(pyproject_text, target), encoding="utf-8")
    init_path.write_text(_replace_init_version(init_text, target), encoding="utf-8")

    print(f"version bumped: {current} -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
