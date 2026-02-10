# Changelog

All notable changes to this project are documented in this file.

The format follows Keep a Changelog and semantic versioning.

## [Unreleased]

### Added
- M3-1 release automation:
  - version bump script (`scripts/bump_version.py`)
  - release bundle packager (`scripts/package_release.py`)
  - release notes generator (`scripts/generate_release_notes.py`)
  - release check version-consistency validation

## [0.1.0] - 2026-02-10

### Added
- End-to-end parse pipeline (OCR abstraction, extraction, normalization, validation).
- Template-aware extraction chain and static refinement editors.
- Batch job API and job-based export/preview endpoints.
- Export systems:
  - report XLSX
  - details CSV
  - accounting mapped CSV with export templates and wizard/refine flow
- Anomaly detection with global config + template overrides.
- Docker mock-engine demo and OpenAPI export tooling.
- Release checklist and baseline CI workflow.
