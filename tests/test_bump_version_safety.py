from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "bump_version.py"


def _load_bump_module():
    script_path = _script_path()
    spec = importlib.util.spec_from_file_location("bump_version_script", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_bump_refuses_when_worktree_dirty(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "tester"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=repo, check=True, capture_output=True, text=True)

    pyproject = repo / "pyproject.toml"
    init_file = repo / "src" / "invstruct" / "__init__.py"
    init_file.parent.mkdir(parents=True, exist_ok=True)
    pyproject.write_text('[project]\nname = "invstruct"\nversion = "0.1.0"\n', encoding="utf-8")
    init_file.write_text('__version__ = "0.1.0"\n', encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True, text=True)

    pyproject.write_text('[project]\nname = "invstruct"\nversion = "0.1.1"\n', encoding="utf-8")

    module = _load_bump_module()
    with pytest.raises(RuntimeError, match="Working tree is not clean"):
        module.ensure_git_worktree_clean(repo)


def test_bump_refuses_when_target_tag_exists(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "tester"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=repo, check=True, capture_output=True, text=True)

    pyproject = repo / "pyproject.toml"
    init_file = repo / "src" / "invstruct" / "__init__.py"
    init_file.parent.mkdir(parents=True, exist_ok=True)
    pyproject.write_text('[project]\nname = "invstruct"\nversion = "0.1.0"\n', encoding="utf-8")
    init_file.write_text('__version__ = "0.1.0"\n', encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "tag", "v0.1.1"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "tag", "v0.1.2"], cwd=repo, check=True, capture_output=True, text=True)

    module = _load_bump_module()
    with pytest.raises(RuntimeError, match="Tag already exists"):
        module.ensure_target_tag_not_exists(repo, "0.1.1")


def test_bump_module_has_safety_helpers():
    module = _load_bump_module()
    assert hasattr(module, "ensure_git_worktree_clean")
    assert hasattr(module, "ensure_target_tag_not_exists")
