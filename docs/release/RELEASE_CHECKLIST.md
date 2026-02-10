# invstruct Release Checklist

Use this checklist before tagging or publishing a release.

## 1) Versioning

- [ ] `pyproject.toml` `project.version` is updated.
- [ ] `src/invstruct/__init__.py` `__version__` matches `project.version`.
- [ ] `CHANGELOG.md` updated (`Unreleased` + target release section).
- [ ] Changelog / milestone docs updated (`docs/plans/*`).
- [ ] Release notes drafted (scope, breaking changes, migration notes).

## 2) Local Required Commands

- [ ] `python -m pip install -e .[dev]`
- [ ] `pytest -q`
- [ ] `python scripts/release_check.py --strict`
- [ ] `python scripts/dump_openapi.py`
- [ ] `python -m build`
- [ ] `python scripts/package_release.py`
- [ ] `python scripts/generate_release_notes.py --version <x.y.z>`

## 3) API Contract Checks

- [ ] `/healthz` returns `200` and `{"status":"ok"}`.
- [ ] `/v1/parse` response shape unchanged: `{trace_id, record}`.
- [ ] `/v1/export/preview` returns `{columns, rows, stats, template_id}`.
- [ ] `/v1/jobs/{job_id}/export` returns correct filename/content-type by `kind`.
- [ ] Error payload uses envelope format:
  - `{"error":{"code","message","trace_id","details"}}`

## 4) Docker Manual Checks (mock engine, offline)

- [ ] `docker compose up -d`
- [ ] `bash scripts/demo.sh` or `powershell -ExecutionPolicy Bypass -File .\scripts\demo.ps1`
- [ ] Demo verifies:
  - `/healthz`
  - `/v1/parse`
  - `/v1/export/preview`
  - `/v1/batch?sync=true`
  - `/v1/jobs/{job_id}/export`

## 5) Template/Export Checks

- [ ] `invstruct export templates list`
- [ ] `invstruct export templates diff --a ... --b ... --out ... --format json,md`
- [ ] `invstruct export accounting --in ... --template ... --out ...`

## 6) Git / Auth / Push Safety

- [ ] `git status` clean (no accidental generated files).
- [ ] `git remote -v` points to expected repo.
- [ ] Auth validated (`git ls-remote`/`gh auth status`).
- [ ] Tag and push plan confirmed (`main`/release branch policy).

## 7) Artifacts

- [ ] `docs/api/openapi.json` regenerated and reviewed.
- [ ] `dist/*` wheels/sdist generated and sanity checked.
- [ ] `release/invstruct_<version>_release_bundle.zip` generated.
- [ ] `release/invstruct_<version>_release_bundle.sha256` generated and verified.
- [ ] Release notes file generated from template/changelog.
- [ ] CI run passed for release commit/tag.
