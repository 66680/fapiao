$ErrorActionPreference = "Stop"

Write-Host "[1/8] install editable + dev extras"
python -m pip install -e ".[dev]"

Write-Host "[2/8] release check"
python scripts/release_check.py --strict

Write-Host "[3/8] tests"
pytest -q

Write-Host "[4/8] dump openapi"
python scripts/dump_openapi.py

Write-Host "[5/8] build dist"
python -m build

Write-Host "[6/8] package release bundle"
python scripts/package_release.py

Write-Host "[7/8] generate release notes (best effort)"
try {
  python scripts/generate_release_notes.py
} catch {
  Write-Warning "release notes generation skipped: $($_.Exception.Message)"
}

Write-Host "[8/8] release check (final)"
python scripts/release_check.py --strict

Write-Host "release pipeline completed"
