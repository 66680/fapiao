from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_release_check_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "release_check.py"
    spec = importlib.util.spec_from_file_location("release_check_script_repro", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_dist_artifacts_check_passes_for_current_version_only(tmp_path: Path):
    module = _load_release_check_module()
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "invstruct-1.2.3-py3-none-any.whl").write_text("x", encoding="utf-8")
    (dist_dir / "invstruct-1.2.3.tar.gz").write_text("x", encoding="utf-8")

    result = module.check_dist_artifacts_current_version_only(dist_dir, "1.2.3")

    assert result.ok is True


def test_dist_artifacts_check_fails_for_mixed_versions(tmp_path: Path):
    module = _load_release_check_module()
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "invstruct-1.2.3-py3-none-any.whl").write_text("x", encoding="utf-8")
    (dist_dir / "invstruct-1.2.2.tar.gz").write_text("x", encoding="utf-8")

    result = module.check_dist_artifacts_current_version_only(dist_dir, "1.2.3")

    assert result.ok is False
    assert "1.2.2" in result.message


def test_release_artifacts_check_fails_for_old_bundle(tmp_path: Path):
    module = _load_release_check_module()
    release_dir = tmp_path / "release"
    release_dir.mkdir()
    (release_dir / "invstruct_1.2.3_release_bundle.zip").write_text("x", encoding="utf-8")
    (release_dir / "invstruct_1.2.3_release_bundle.sha256").write_text("x", encoding="utf-8")
    (release_dir / "release_notes_1.2.3.md").write_text("x", encoding="utf-8")
    (release_dir / "invstruct_1.2.2_release_bundle.zip").write_text("x", encoding="utf-8")

    result = module.check_release_artifacts_current_version_only(release_dir, "1.2.3")

    assert result.ok is False
    assert "1.2.2" in result.message


def test_openapi_consistency_fails_when_payload_differs(tmp_path: Path):
    module = _load_release_check_module()
    openapi_path = tmp_path / "openapi.json"
    openapi_path.write_text('{"openapi":"3.1.0","info":{"title":"A"}}', encoding="utf-8")

    result = module.check_openapi_in_sync(openapi_path, {"openapi": "3.1.0", "info": {"title": "B"}})

    assert result.ok is False
    assert "mismatch" in result.message.lower()
