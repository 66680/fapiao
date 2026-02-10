from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass


@dataclass
class EnvStatus:
    python: str
    pip_available: bool
    pip_version: str
    docker_available: bool
    docker_path: str
    docker_version: str
    note: str


def _pip_info() -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode == 0:
            return True, completed.stdout.strip()
        return False, completed.stderr.strip() or "pip not available"
    except Exception as exc:
        return False, str(exc)


def _docker_info() -> tuple[bool, str, str]:
    docker_path = shutil.which("docker") or ""
    if not docker_path:
        return False, "", "docker command not found in PATH"

    completed = subprocess.run(
        ["docker", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return True, docker_path, completed.stdout.strip()
    return False, docker_path, completed.stderr.strip() or "docker command failed"


def main() -> int:
    pip_available, pip_version = _pip_info()
    docker_available, docker_path, docker_version = _docker_info()

    note = (
        "Docker unavailable -> skip Docker acceptance on this machine"
        if not docker_available
        else "Docker available -> Docker acceptance can run"
    )

    status = EnvStatus(
        python=platform.python_version(),
        pip_available=pip_available,
        pip_version=pip_version,
        docker_available=docker_available,
        docker_path=docker_path,
        docker_version=docker_version,
        note=note,
    )

    print(json.dumps(asdict(status), ensure_ascii=False, indent=2))

    # Important: Docker absence is not a failure for this environment check.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

