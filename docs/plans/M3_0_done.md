# M3-0 Done

## Scope
- Release checklist automation.
- OpenAPI export tooling and examples docs.
- Optional minimal CI workflow.

## Completed
- Added release checklist:
  - `docs/release/RELEASE_CHECKLIST.md`
- Added automation scripts:
  - `scripts/release_check.py`
  - `scripts/dump_openapi.py`
  - `scripts/release.sh`
  - `scripts/release.ps1`
- Packaging:
  - added `build` to `[project.optional-dependencies].dev`
  - release scripts run `python -m build`
- OpenAPI docs/examples:
  - `docs/api/examples.md` with curl/PowerShell/python requests examples
  - `scripts/dump_openapi.py` exports `docs/api/openapi.json`
- OpenAPI route polish:
  - route summaries/descriptions/tags/response models on key API endpoints
  - error response model references (`ErrorEnvelope`) where applicable
- Response header normalization:
  - download responses include explicit content-disposition/content-type helper usage
- Optional CI:
  - `.github/workflows/ci.yml` with OS/Python matrix pytest + openapi artifact + dist build artifact

## Verification
- `pip install -e .`
- `pytest -q`
- `python scripts/dump_openapi.py`
- `python -m build`
