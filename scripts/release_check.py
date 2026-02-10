from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    name: str
    required: bool
    ok: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "required": self.required,
            "ok": self.ok,
            "message": self.message,
        }


def _load_pyproject(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import tomllib  # py311+

        return tomllib.loads(text)
    except Exception:  # noqa: BLE001
        pass

    # minimal fallback parser for version/name only
    project_block = re.search(r"(?ms)^\[project\]\n(.*?)(^\[|\Z)", text)
    if not project_block:
        return {}
    body = project_block.group(1)
    name_match = re.search(r'(?m)^name\s*=\s*"([^"]+)"', body)
    version_match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', body)
    result: dict[str, Any] = {"project": {}}
    if name_match:
        result["project"]["name"] = name_match.group(1)
    if version_match:
        result["project"]["version"] = version_match.group(1)
    return result


def _load_init_version(init_path: Path) -> str | None:
    if not init_path.exists():
        return None
    text = init_path.read_text(encoding="utf-8")
    match = re.search(r'(?m)^__version__\s*=\s*"([^"]+)"\s*$', text)
    if not match:
        return None
    return match.group(1)


def check_version_consistency(pyproject_path: Path, init_path: Path) -> CheckResult:
    payload = _load_pyproject(pyproject_path) if pyproject_path.exists() else {}
    project = payload.get("project") if isinstance(payload, dict) else {}
    pyproject_version = project.get("version") if isinstance(project, dict) else None
    init_version = _load_init_version(init_path)
    if not pyproject_version:
        return CheckResult(
            "project_version_matches_package",
            True,
            False,
            "missing project.version in pyproject.toml",
        )
    if not init_version:
        return CheckResult(
            "project_version_matches_package",
            True,
            False,
            f'missing __version__ in "{init_path}"',
        )
    matches = str(pyproject_version) == str(init_version)
    return CheckResult(
        "project_version_matches_package",
        True,
        matches,
        f'pyproject="{pyproject_version}" package="{init_version}"',
    )


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="invstruct release readiness checks")
    parser.add_argument("--strict", action="store_true", help="Return non-zero when required checks fail")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    pyproject_path = repo_root / "pyproject.toml"
    results: list[CheckResult] = []

    if not pyproject_path.exists():
        results.append(CheckResult("pyproject_exists", True, False, f"missing: {pyproject_path}"))
    else:
        payload = _load_pyproject(pyproject_path)
        project = payload.get("project") if isinstance(payload, dict) else {}
        name = project.get("name") if isinstance(project, dict) else None
        version = project.get("version") if isinstance(project, dict) else None
        results.append(CheckResult("project_name", True, bool(name), f"name={name!r}"))
        semver_ok = bool(version) and bool(re.fullmatch(r"\d+\.\d+\.\d+", str(version)))
        results.append(CheckResult("project_version_semver", True, semver_ok, f"version={version!r}"))
        results.append(check_version_consistency(pyproject_path, repo_root / "src" / "invstruct" / "__init__.py"))

    required_files = [
        "CHANGELOG.md",
        "docs/release/RELEASE_CHECKLIST.md",
        "docs/release/RELEASE_NOTES_TEMPLATE.md",
        "docs/api/examples.md",
        "scripts/bump_version.py",
        "scripts/dump_openapi.py",
        "scripts/package_release.py",
        "scripts/generate_release_notes.py",
        "scripts/release.ps1",
        "scripts/release.sh",
    ]
    for relative in required_files:
        path = repo_root / relative
        results.append(CheckResult(f"file:{relative}", True, path.exists(), str(path)))

    for cmd in ("python", "pip", "pytest"):
        results.append(CheckResult(f"command:{cmd}", True, shutil.which(cmd) is not None, shutil.which(cmd) or "not found"))

    # optional docker availability
    docker_ok = shutil.which("docker") is not None
    results.append(CheckResult("command:docker", False, docker_ok, "docker available" if docker_ok else "docker not found"))

    # optional git auth/push context
    git_ok = (repo_root / ".git").exists()
    if git_ok:
        rc, out = _run(["git", "-C", str(repo_root), "remote", "-v"])
        results.append(CheckResult("git_remote", False, rc == 0 and bool(out.strip()), out or "no remote"))
        rc, out = _run(["git", "-C", str(repo_root), "config", "--get", "user.email"])
        results.append(CheckResult("git_user_email", False, rc == 0 and bool(out.strip()), out or "missing"))
    else:
        results.append(CheckResult("git_repo_detected", False, False, ".git not found"))

    required_failures = [item for item in results if item.required and not item.ok]
    summary = {
        "ok": len(required_failures) == 0,
        "required_failures": len(required_failures),
        "checks": [item.to_dict() for item in results],
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("invstruct release check")
        for item in results:
            tag = "OK" if item.ok else ("FAIL" if item.required else "WARN")
            req = "required" if item.required else "optional"
            print(f"[{tag}] ({req}) {item.name}: {item.message}")
        print(f"required_failures={len(required_failures)}")

    if args.strict and required_failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
