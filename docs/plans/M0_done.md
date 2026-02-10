# M0 Done (Day1-2)

## Scope
- Built runnable scaffold with `CLI + FastAPI + config + logging + errors + schema`.
- Kept OCR as adapter-only with `MockOcrEngine`.
- Added Docker CPU skeleton and baseline tests.

## Completed
- Project layout under `src/invstruct`, `configs`, `tests`, `docker`, `docs`.
- Packaging via `pyproject.toml` (`pip install -e .` ready).
- Unified error model (`E1001/E2001/E3001/E4001/E5001`).
- Data schema: `InvoiceRecord`, `FieldProvenance`, `Confidence`.
- Config: YAML + env override (`INVSTRUCT_*`).
- Trace + hash utilities (`trace_id`, `sha256`).
- CLI commands: `parse/batch/export/check/template/serve`.
- API routes: `/healthz`, `/v1/parse`, `/v1/jobs/{job_id}`.
- Tests: hash, trace_id, schema roundtrip, config load, api healthz, cli help.

## Notes
- All non-M0 behaviors intentionally stubbed and stable by interface.

## Docker 验收状态：环境阻断
- 阻断原因：当前机器执行 `docker --version` 报 `CommandNotFoundException`，系统无可用 Docker 命令。
- 结论：本机无法执行 `docker build/run/compose` 的真实验收，这属于环境缺失，不是应用代码故障。

### 可在有 Docker 的机器上执行的命令
- `docker build -f docker/Dockerfile.cpu . -t invstruct:cpu`
- `docker run --rm -p 8000:8000 invstruct:cpu`
- `Invoke-WebRequest http://127.0.0.1:8000/healthz | Select-Object -Expand Content`
- `docker compose up --build`
- `Invoke-WebRequest http://127.0.0.1:8000/healthz | Select-Object -Expand Content`

### 本次 Docker 文件加固点
- `docker/Dockerfile.cpu`：保持 src-layout 所需拷贝（`pyproject.toml` + `src/` + `configs/`），并补充 `docs/` 拷贝以便容器内调试。
- `docker/Dockerfile.cpu`：保留 `pip install -e .`，确保镜像内可导入 `invstruct`。
- `docker/Dockerfile.cpu`：保留 uvicorn 启动命令 `invstruct.api.app:app`，host `0.0.0.0`、port `8000`。
- `docker-compose.yml`：保留一键构建与端口映射 `8000:8000`，确保 compose 路径一致。
