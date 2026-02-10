#!/usr/bin/env bash
set -euo pipefail

echo "[1/8] install editable + dev extras"
python -m pip install -e ".[dev]"

echo "[2/8] release check"
python scripts/release_check.py --strict

echo "[3/8] tests"
pytest -q

echo "[4/8] dump openapi"
python scripts/dump_openapi.py

echo "[5/8] build dist"
python -m build

echo "[6/8] package release bundle"
python scripts/package_release.py

echo "[7/8] generate release notes (best effort)"
python scripts/generate_release_notes.py || true

echo "[8/8] release check (final)"
python scripts/release_check.py --strict

echo "release pipeline completed"
