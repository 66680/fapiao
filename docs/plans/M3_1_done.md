# M3-1 Done

## Scope
- CHANGELOG and release-note scaffolding.
- Version bump automation and version-consistency checks.
- Release bundle packaging automation.
- Release pipeline script updates and CI artifact enhancement.

## Completed
- Added `CHANGELOG.md` with `Unreleased` and `0.1.0` sections.
- Added `scripts/bump_version.py`:
  - supports `--patch` and `--to <x.y.z>`
  - updates both `pyproject.toml` and `src/invstruct/__init__.py`.
- Extended `scripts/release_check.py`:
  - added `check_version_consistency(...)`
  - validates `project.version` vs `__version__`
  - checks new release assets/scripts existence.
- Added `scripts/package_release.py`:
  - builds `release/invstruct_<ver>_release_bundle.zip`
  - includes `dist/*`, `docs/api/openapi.json`, `docs/api/examples.md`, `scripts/demo.sh`, `scripts/demo.ps1`
  - writes `release/invstruct_<ver>_release_bundle.sha256`.
- Added release-notes assets:
  - `docs/release/RELEASE_NOTES_TEMPLATE.md`
  - `scripts/generate_release_notes.py`.
- Updated release runners:
  - `scripts/release.sh`
  - `scripts/release.ps1`
  - now run package + notes generation + final release check.
- Updated CI build job to upload release bundle artifacts.
- Added regression test:
  - `tests/test_release_check_version_consistency.py`.

## Verification
- `pytest -q tests/test_release_check_version_consistency.py`
- Full project verification and acceptance commands executed after implementation.
