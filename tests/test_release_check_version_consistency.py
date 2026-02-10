from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_release_check_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "release_check.py"
    spec = importlib.util.spec_from_file_location("release_check_script", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_version_consistency_check_ok(tmp_path: Path):
    module = _load_release_check_module()
    pyproject = tmp_path / "pyproject.toml"
    init_file = tmp_path / "__init__.py"
    pyproject.write_text('[project]\nname = "invstruct"\nversion = "1.2.3"\n', encoding="utf-8")
    init_file.write_text('__version__ = "1.2.3"\n', encoding="utf-8")

    result = module.check_version_consistency(pyproject, init_file)

    assert result.ok is True


def test_version_consistency_check_detects_mismatch(tmp_path: Path):
    module = _load_release_check_module()
    pyproject = tmp_path / "pyproject.toml"
    init_file = tmp_path / "__init__.py"
    pyproject.write_text('[project]\nname = "invstruct"\nversion = "1.2.3"\n', encoding="utf-8")
    init_file.write_text('__version__ = "1.2.4"\n', encoding="utf-8")

    result = module.check_version_consistency(pyproject, init_file)

    assert result.ok is False
    assert "1.2.3" in result.message
    assert "1.2.4" in result.message
