# invstruct

Offline-first invoice/receipt structuring toolkit:

- OCR + extraction + normalization
- template-driven export (Excel/CSV/accounting CSV)
- batch jobs + API preview + traceable outputs

No Paddle/PDF heavy dependencies are required for the default mock-engine demo.

## Features

- `CLI + FastAPI + Docker` deployable baseline
- Template refinement (static HTML editors)
- Export template fallback sources (`source_candidates`)
- Batch job exports (`report_xlsx`, `details_csv`, `accounting_csv`)
- Export preview APIs (`/v1/export/preview`, `/v1/jobs/{job_id}/export/preview`)

## Quickstart (CLI)

```bash
pip install -e .
pytest -q

# Parse folder and export xlsx/csv
python -m invstruct.cli batch ./some_dir --out ./out --export xlsx,csv

# Accounting export by template profile
python -m invstruct.cli export accounting --in ./out/records.jsonl --template generic_expense_v1 --out ./out/accounting.csv

# Template diff report (json + markdown)
python -m invstruct.cli export templates diff --a configs/export_templates/generic_expense_v1.yaml --b configs/export_templates/generic_expense_v1.yaml --out ./out_diff --format json,md
```

## Quickstart (API)

```bash
uvicorn invstruct.api.app:app --port 8000
```

```bash
# Health
curl http://127.0.0.1:8000/healthz

# Parse single file
curl -F "file=@sample.png;type=image/png" http://127.0.0.1:8000/v1/parse

# Export preview from uploaded records.jsonl
curl -F "records=@out/records.jsonl;type=application/json" -F "template_id=generic_expense_v1" \
  "http://127.0.0.1:8000/v1/export/preview?limit=20"
```

Preview response shape:

```json
{
  "template_id": "generic_expense_v1",
  "columns": ["expense_date", "merchant", "amount"],
  "rows": [{"expense_date": "2026-02-09", "merchant": "Demo Store", "amount": "12.34"}],
  "stats": {
    "input_rows": 1,
    "preview_rows": 1,
    "truncated": false,
    "fallback_usage_by_column": {},
    "source_usage_by_column": {},
    "invalid_rows": 0,
    "has_more": false
  }
}
```

## Docker Demo (mock engine, offline)

```bash
docker compose up -d
bash scripts/demo.sh
```

PowerShell:

```powershell
docker compose up -d
powershell -ExecutionPolicy Bypass -File .\scripts\demo.ps1
```

## Export Template Workflow

```bash
# Generate static wizard bundle
python -m invstruct.cli export templates wizard --in ./out/records.jsonl --base generic_expense_v1 --out ./out_wizard

# Open out_wizard/wizard.html and export export_template_update.json

# Apply + validate
python -m invstruct.cli export templates refine apply --base configs/export_templates/generic_expense_v1.yaml --update ./out_wizard/export_template_update.json --out configs/export_templates/generic_expense_v1_refined.yaml
python -m invstruct.cli export templates validate configs/export_templates/generic_expense_v1_refined.yaml
```

## API Batch + Job Export

```bash
# Create sync batch job
curl -F "files=@sample.png;type=image/png" "http://127.0.0.1:8000/v1/batch?sync=true"

# Download exports by job_id
curl -OJ "http://127.0.0.1:8000/v1/jobs/<job_id>/export?kind=report_xlsx"
curl -OJ "http://127.0.0.1:8000/v1/jobs/<job_id>/export?kind=details_csv"
curl -OJ "http://127.0.0.1:8000/v1/jobs/<job_id>/export?kind=accounting_csv&template_id=generic_expense_v1"

# Preview by job_id
curl "http://127.0.0.1:8000/v1/jobs/<job_id>/export/preview?template_id=generic_expense_v1&limit=20"
```

## Optional Extras

- PDF support extras: `pip install -e .[pdf]`
- Paddle OCR extras: `pip install -e .[paddle]`

## Release Automation

```bash
# Optional: bump version
python scripts/bump_version.py --patch

python scripts/release_check.py --strict
python scripts/dump_openapi.py
python -m build
python scripts/package_release.py
python scripts/generate_release_notes.py
```

PowerShell one-shot:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\release.ps1
```

## Demos (placeholders)

- GIF: folder batch -> report.xlsx
- GIF: template editor refine loop
- GIF: API preview + job export
