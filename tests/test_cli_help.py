import subprocess
import sys


def test_cli_help_returns_zero() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "invstruct.cli", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "invstruct CLI" in completed.stdout

