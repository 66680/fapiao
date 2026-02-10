# M2-7 Done

## Scope
- OpenAPI documentation and schema polish.
- Docker compose one-command mock demo packaging.
- Job export response header normalization.
- README front-page overhaul for copy-paste quickstarts.

## Completed
- OpenAPI improvements:
  - Added route summaries/descriptions/tags for parse, batch, and export APIs.
  - Added Pydantic API response models under `src/invstruct/api/models.py`.
  - Added error response model wiring (`ErrorEnvelope`) on major routes.
- Error envelope consistency:
  - Added `api_error_response(...)` helper and applied it to batch/export route errors.
- Export download header normalization:
  - Added `download_file_response(...)` helper with explicit `Content-Disposition` and `Content-Type`.
- Docker demo updates:
  - Updated `docker-compose.yml` with env + volumes for offline mock engine run.
  - Updated `docker/Dockerfile.cpu` with default config/template dirs and env defaults.
  - Added runnable demo scripts:
    - `scripts/demo.sh`
    - `scripts/demo.ps1`
- README restructure:
  - Rewrote top sections (value proposition, quickstarts, docker demo, API preview examples).

## Validation
- `pip install -e .`
- `pytest -q` (full suite green)
- CLI/API smoke checks for diff markdown and preview endpoints.
