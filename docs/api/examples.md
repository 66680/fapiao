# API Examples

Base URL:

- `http://127.0.0.1:8000`

## 1) Parse Single File

### curl

```bash
curl -F "file=@sample.png;type=image/png" http://127.0.0.1:8000/v1/parse
```

### PowerShell

```powershell
$form = @{ file = Get-Item .\sample.png }
Invoke-WebRequest -Uri "http://127.0.0.1:8000/v1/parse" -Method Post -Form $form -UseBasicParsing
```

### Python (requests)

```python
import requests

with open("sample.png", "rb") as handle:
    resp = requests.post(
        "http://127.0.0.1:8000/v1/parse",
        files={"file": ("sample.png", handle, "image/png")},
        timeout=30,
    )
print(resp.status_code, resp.json())
```

## 2) Export Preview (uploaded records.jsonl)

### curl

```bash
curl -F "records=@out/records.jsonl;type=application/json" \
     -F "template_id=generic_expense_v1" \
     "http://127.0.0.1:8000/v1/export/preview?limit=20"
```

### PowerShell

```powershell
$form = @{
  records = Get-Item .\out\records.jsonl
  template_id = "generic_expense_v1"
}
Invoke-WebRequest -Uri "http://127.0.0.1:8000/v1/export/preview?limit=20" -Method Post -Form $form -UseBasicParsing
```

### Python (requests)

```python
import requests

with open("out/records.jsonl", "rb") as handle:
    resp = requests.post(
        "http://127.0.0.1:8000/v1/export/preview?limit=20",
        files={"records": ("records.jsonl", handle, "application/json")},
        data={"template_id": "generic_expense_v1"},
        timeout=30,
    )
print(resp.status_code, resp.json())
```

## 3) Batch + Job Preview + Export

### curl

```bash
# create sync batch
curl -F "files=@sample.png;type=image/png" "http://127.0.0.1:8000/v1/batch?sync=true"

# get preview by job
curl "http://127.0.0.1:8000/v1/jobs/<job_id>/export/preview?template_id=generic_expense_v1&limit=20"

# download accounting csv
curl -OJ "http://127.0.0.1:8000/v1/jobs/<job_id>/export?kind=accounting_csv&template_id=generic_expense_v1"
```

### PowerShell

```powershell
$batch = Invoke-WebRequest -Uri "http://127.0.0.1:8000/v1/batch?sync=true" -Method Post -Form @{ files = Get-Item .\sample.png } -UseBasicParsing
$job = ($batch.Content | ConvertFrom-Json).job_id
Invoke-WebRequest -Uri "http://127.0.0.1:8000/v1/jobs/$job/export/preview?template_id=generic_expense_v1&limit=20" -UseBasicParsing
Invoke-WebRequest -Uri "http://127.0.0.1:8000/v1/jobs/$job/export?kind=accounting_csv&template_id=generic_expense_v1" -OutFile .\accounting.csv -UseBasicParsing
```

### Python (requests)

```python
import requests

with open("sample.png", "rb") as handle:
    batch = requests.post(
        "http://127.0.0.1:8000/v1/batch?sync=true",
        files=[("files", ("sample.png", handle, "image/png"))],
        timeout=60,
    )
job_id = batch.json()["job_id"]

preview = requests.get(
    f"http://127.0.0.1:8000/v1/jobs/{job_id}/export/preview",
    params={"template_id": "generic_expense_v1", "limit": 20},
    timeout=30,
)
print(preview.status_code, preview.json())

export = requests.get(
    f"http://127.0.0.1:8000/v1/jobs/{job_id}/export",
    params={"kind": "accounting_csv", "template_id": "generic_expense_v1"},
    timeout=30,
)
open("accounting.csv", "wb").write(export.content)
```
