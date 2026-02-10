from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from invstruct.export_templates.models import ExportTemplateSpec, TRANSFORM_WHITELIST
from invstruct.schemas import InvoiceRecord


def _flatten_payload(payload: dict[str, Any], prefix: str = "") -> list[str]:
    fields: list[str] = []
    for key, value in payload.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            fields.extend(_flatten_payload(value, path))
        else:
            fields.append(path)
    return fields


def build_field_catalog(records: list[InvoiceRecord]) -> list[str]:
    names: set[str] = set()
    for record in records[:20]:
        names.update(_flatten_payload(record.to_dict()))
    if not names:
        names.update(
            {
                "doc_id",
                "doc_type",
                "template_id",
                "merchant_name",
                "issue_date",
                "total_amount_gross",
                "currency",
                "invoice_number",
                "merchant_tax_id",
                "source.file_name",
                "source.trace_id",
            }
        )
    return sorted(names)


def wizard_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>invstruct export template wizard</title>
  <style>
    body { margin: 0; font-family: sans-serif; display: grid; grid-template-columns: 360px 1fr; min-height: 100vh; }
    aside { padding: 12px; border-right: 1px solid #ddd; overflow: auto; }
    main { padding: 12px; overflow: auto; }
    table { border-collapse: collapse; width: 100%; margin-top: 8px; }
    th, td { border: 1px solid #ddd; padding: 6px; font-size: 12px; vertical-align: top; }
    th { background: #f5f5f5; text-align: left; }
    input, select, button, textarea { font-size: 12px; }
    input, select, textarea { width: 100%; box-sizing: border-box; }
    .row { margin-bottom: 8px; }
    .muted { color: #666; font-size: 12px; }
    .toolbar button { margin-right: 6px; margin-bottom: 6px; }
    .danger { color: #b00020; }
    .candidate-row { display: grid; grid-template-columns: 1fr auto auto auto; gap: 4px; margin-bottom: 4px; }
    .candidate-row button { margin: 0; }
  </style>
</head>
<body>
  <aside>
    <h3>Export Mapping Wizard</h3>
    <div class="row muted">Static JSON workflow: export_template.json + sample_records.json -> export_template_update.json</div>
    <div class="toolbar row">
      <button id="addColumn">Add Column</button>
      <button id="downloadUpdate">Download export_template_update.json</button>
      <button id="downloadReport">Download wizard_refine_report.json</button>
    </div>
    <div class="row">
      <label>Template ID</label>
      <input id="templateId" />
    </div>
    <div class="row">
      <label>Version</label>
      <input id="templateVersion" />
    </div>
    <div class="row">
      <label>Description</label>
      <textarea id="templateDescription" rows="3"></textarea>
    </div>
    <div id="columnsEditor"></div>
  </aside>
  <main>
    <h3>Preview</h3>
    <div class="muted">Preview rows are rendered with transform whitelist and defaults.</div>
    <table>
      <thead id="previewHead"></thead>
      <tbody id="previewBody"></tbody>
    </table>
  </main>
  <script>
    const transformWhitelist = ["as_is", "date_iso", "amount_2dp", "anomaly_codes_join"];
    const state = { template: null, samples: [], fieldCatalog: [], previewRows: [] };
    const editorEl = document.getElementById("columnsEditor");
    const previewHeadEl = document.getElementById("previewHead");
    const previewBodyEl = document.getElementById("previewBody");
    const templateIdEl = document.getElementById("templateId");
    const templateVersionEl = document.getElementById("templateVersion");
    const templateDescriptionEl = document.getElementById("templateDescription");

    async function loadJson(name, fallback) {
      try {
        const resp = await fetch(name, { cache: "no-store" });
        if (!resp.ok) return fallback;
        return await resp.json();
      } catch (err) {
        return fallback;
      }
    }

    function isMissingValue(value) {
      if (value === null || value === undefined) return true;
      if (typeof value === "string") return value.trim() === "";
      if (Array.isArray(value)) return value.length === 0;
      if (typeof value === "object") return Object.keys(value).length === 0;
      return false;
    }

    function resolve(obj, source) {
      let cursor = obj;
      for (const part of String(source || "").split(".")) {
        if (!part) continue;
        if (cursor && typeof cursor === "object" && part in cursor) {
          cursor = cursor[part];
        } else {
          return null;
        }
      }
      return cursor;
    }

    function getCandidates(col) {
      const candidates = Array.isArray(col.source_candidates)
        ? col.source_candidates.filter((item) => String(item || "").trim() !== "")
        : [];
      if (candidates.length > 0) return candidates;
      if (col.source && String(col.source).trim() !== "") return [String(col.source).trim()];
      return [];
    }

    function resolveByCandidates(sample, col) {
      const candidates = getCandidates(col);
      for (let idx = 0; idx < candidates.length; idx += 1) {
        const src = candidates[idx];
        const raw = resolve(sample, src);
        if (!isMissingValue(raw)) return { value: raw, source: src, index: idx };
      }
      return { value: null, source: null, index: -1 };
    }

    function asIso(value) {
      if (value === null || value === undefined || value === "") return "";
      const raw = String(value);
      if (/^\\d{4}-\\d{2}-\\d{2}$/.test(raw)) return raw;
      return raw;
    }

    function amount2dp(value) {
      const num = Number(value);
      if (Number.isNaN(num)) return "";
      return num.toFixed(2);
    }

    function anomalyCodesJoin(value) {
      if (!Array.isArray(value)) return "";
      const codes = [];
      for (const item of value) {
        if (item && typeof item === "object" && item.code) codes.push(String(item.code));
      }
      return codes.join("|");
    }

    function applyTransform(transform, rawValue) {
      if (!transformWhitelist.includes(transform)) return "";
      if (transform === "as_is") return rawValue ?? "";
      if (transform === "date_iso") return asIso(rawValue);
      if (transform === "amount_2dp") return amount2dp(rawValue);
      if (transform === "anomaly_codes_join") return anomalyCodesJoin(rawValue);
      return "";
    }

    function computePreviewRows() {
      const rows = [];
      for (const sample of state.samples) {
        const row = {};
        for (const col of state.template.columns) {
          const resolved = resolveByCandidates(sample, col);
          const value = applyTransform(col.transform, resolved.value);
          const finalValue = (value === "" || value === null || value === undefined) ? (col.default ?? "") : value;
          row[col.name] = {
            value: finalValue,
            source: resolved.source,
            index: resolved.index
          };
        }
        rows.push(row);
      }
      state.previewRows = rows;
    }

    function renderPreview() {
      const headers = state.template.columns.map((c) => c.name);
      previewHeadEl.innerHTML = "<tr>" + headers.map((h) => `<th>${h}</th>`).join("") + "</tr>";
      previewBodyEl.innerHTML = state.previewRows.map((row) => {
        return "<tr>" + headers.map((h) => {
          const item = row[h] || {};
          const title = item.source ? `title="source: ${item.source} (#${item.index + 1})"` : "";
          return `<td ${title}>${String(item.value ?? "")}</td>`;
        }).join("") + "</tr>";
      }).join("");
    }

    function parseDefaultValue(value) {
      if (value === "") return null;
      if (value === "true") return true;
      if (value === "false") return false;
      if (/^-?\\d+(\\.\\d+)?$/.test(value)) return Number(value);
      return value;
    }

    function setColumnValue(index, key, value) {
      if (index < 0 || index >= state.template.columns.length) return;
      state.template.columns[index][key] = value;
      computePreviewRows();
      renderPreview();
    }

    function setSourceCandidates(index, candidates) {
      if (index < 0 || index >= state.template.columns.length) return;
      const normalized = candidates.map((item) => String(item || "").trim()).filter((item) => item !== "");
      state.template.columns[index].source_candidates = normalized.length > 0 ? normalized : null;
      state.template.columns[index].source = normalized[0] || state.template.columns[index].source || "";
      computePreviewRows();
      renderPreview();
    }

    function removeColumn(index) {
      state.template.columns.splice(index, 1);
      renderEditor();
      computePreviewRows();
      renderPreview();
    }

    function moveColumn(index, offset) {
      const target = index + offset;
      if (target < 0 || target >= state.template.columns.length) return;
      const current = state.template.columns[index];
      state.template.columns.splice(index, 1);
      state.template.columns.splice(target, 0, current);
      renderEditor();
      computePreviewRows();
      renderPreview();
    }

    function candidateRowTemplate(index, candidateIndex, value) {
      const options = state.fieldCatalog.map((field) => {
        const selected = field === value ? "selected" : "";
        return `<option value="${field}" ${selected}>${field}</option>`;
      }).join("");
      return `
        <div class="candidate-row sourceCandidatesList" data-index="${index}" data-candidate-index="${candidateIndex}">
          <select data-candidate-field="value">${options}</select>
          <button data-candidate-action="up">↑</button>
          <button data-candidate-action="down">↓</button>
          <button data-candidate-action="remove" class="danger">x</button>
        </div>
      `;
    }

    function addColumn() {
      const source = state.fieldCatalog[0] || "merchant_name";
      state.template.columns.push({
        name: `column_${state.template.columns.length + 1}`,
        source,
        source_candidates: [source],
        candidate_strategy: "first_non_empty",
        transform: "as_is",
        default: null,
        required: false
      });
      renderEditor();
      computePreviewRows();
      renderPreview();
    }

    function renderEditor() {
      const rows = state.template.columns.map((col, index) => {
        const sourceOptions = state.fieldCatalog.map((field) => {
          const selected = field === col.source ? "selected" : "";
          return `<option value="${field}" ${selected}>${field}</option>`;
        }).join("");
        const candidates = getCandidates(col);
        const candidatesHtml = candidates.length
          ? candidates.map((item, candidateIndex) => candidateRowTemplate(index, candidateIndex, item)).join("")
          : "<div class='muted sourceCandidatesList'>No candidates configured</div>";
        const transformOptions = transformWhitelist.map((item) => {
          const selected = item === col.transform ? "selected" : "";
          return `<option value="${item}" ${selected}>${item}</option>`;
        }).join("");
        const strategyOptions = ["first_non_empty", "prefer_primary_source", "highest_confidence"].map((item) => {
          const selected = item === (col.candidate_strategy || "first_non_empty") ? "selected" : "";
          return `<option value="${item}" ${selected}>${item}</option>`;
        }).join("");
        const defaultValue = col.default === null || col.default === undefined ? "" : String(col.default);
        const requiredChecked = col.required ? "checked" : "";
        return `
          <div class="row" data-index="${index}">
            <div><strong>#${index + 1}</strong></div>
            <label>Name</label>
            <input value="${String(col.name || "")}" data-key="name" />
            <label>Source</label>
            <select data-key="source">${sourceOptions}</select>
            <label>Source Candidates</label>
            <div>${candidatesHtml}</div>
            <button class="addCandidateBtn" data-action="add-candidate">Add Candidate</button>
            <label>Candidate Strategy</label>
            <select data-key="candidate_strategy">${strategyOptions}</select>
            <label>Transform</label>
            <select data-key="transform">${transformOptions}</select>
            <label>Default</label>
            <input value="${defaultValue}" data-key="default" />
            <label><input type="checkbox" data-key="required" ${requiredChecked}/> Required</label>
            <div class="toolbar">
              <button data-action="up">Up</button>
              <button data-action="down">Down</button>
              <button data-action="remove" class="danger">Remove</button>
            </div>
            <hr/>
          </div>
        `;
      }).join("");
      editorEl.innerHTML = rows || "<div class='muted'>No columns. Click Add Column.</div>";

      editorEl.querySelectorAll("input,select").forEach((el) => {
        el.addEventListener("change", (evt) => {
          const target = evt.target;
          const wrapper = target.closest("[data-index]");
          if (!wrapper) return;
          const idx = Number(wrapper.getAttribute("data-index"));
          const key = target.getAttribute("data-key");
          if (!key) return;
          if (key === "required") {
            setColumnValue(idx, key, Boolean(target.checked));
            return;
          }
          if (key === "default") {
            setColumnValue(idx, key, parseDefaultValue(target.value));
            return;
          }
          if (key === "source") {
            const currentCandidates = getCandidates(state.template.columns[idx]);
            if (currentCandidates.length === 0) {
              setSourceCandidates(idx, [target.value]);
            } else {
              currentCandidates[0] = target.value;
              setSourceCandidates(idx, currentCandidates);
            }
            return;
          }
          if (key === "transform" && !transformWhitelist.includes(target.value)) return;
          setColumnValue(idx, key, target.value);
        });
      });

      editorEl.querySelectorAll("button[data-action]").forEach((btn) => {
        btn.addEventListener("click", (evt) => {
          evt.preventDefault();
          const target = evt.target;
          const wrapper = target.closest("[data-index]");
          if (!wrapper) return;
          const idx = Number(wrapper.getAttribute("data-index"));
          const action = target.getAttribute("data-action");
          if (action === "up") moveColumn(idx, -1);
          if (action === "down") moveColumn(idx, 1);
          if (action === "remove") removeColumn(idx);
          if (action === "add-candidate") {
            const list = getCandidates(state.template.columns[idx]);
            const fallback = state.fieldCatalog[0] || "merchant_name";
            list.push(fallback);
            setSourceCandidates(idx, list);
            renderEditor();
          }
        });
      });

      editorEl.querySelectorAll("[data-candidate-action]").forEach((btn) => {
        btn.addEventListener("click", (evt) => {
          evt.preventDefault();
          const target = evt.target;
          const wrapper = target.closest("[data-index][data-candidate-index]");
          if (!wrapper) return;
          const idx = Number(wrapper.getAttribute("data-index"));
          const candidateIndex = Number(wrapper.getAttribute("data-candidate-index"));
          const action = target.getAttribute("data-candidate-action");
          const list = getCandidates(state.template.columns[idx]);
          if (action === "up" && candidateIndex > 0) {
            const tmp = list[candidateIndex - 1];
            list[candidateIndex - 1] = list[candidateIndex];
            list[candidateIndex] = tmp;
          } else if (action === "down" && candidateIndex < list.length - 1) {
            const tmp = list[candidateIndex + 1];
            list[candidateIndex + 1] = list[candidateIndex];
            list[candidateIndex] = tmp;
          } else if (action === "remove") {
            list.splice(candidateIndex, 1);
          }
          setSourceCandidates(idx, list);
          renderEditor();
        });
      });

      editorEl.querySelectorAll("[data-candidate-field='value']").forEach((selectEl) => {
        selectEl.addEventListener("change", (evt) => {
          const target = evt.target;
          const wrapper = target.closest("[data-index][data-candidate-index]");
          if (!wrapper) return;
          const idx = Number(wrapper.getAttribute("data-index"));
          const candidateIndex = Number(wrapper.getAttribute("data-candidate-index"));
          const list = getCandidates(state.template.columns[idx]);
          list[candidateIndex] = target.value;
          setSourceCandidates(idx, list);
        });
      });
    }

    function syncTemplateMeta() {
      state.template.template_id = templateIdEl.value || "export_template";
      state.template.version = templateVersionEl.value || "1.0.0";
      state.template.description = templateDescriptionEl.value || "";
    }

    function currentTemplateSpec() {
      syncTemplateMeta();
      const columns = state.template.columns.map((col) => ({
        name: String(col.name || "").trim(),
        source: String(col.source || "").trim(),
        source_candidates: getCandidates(col),
        candidate_strategy: ["first_non_empty", "prefer_primary_source", "highest_confidence"].includes(col.candidate_strategy)
          ? col.candidate_strategy
          : "first_non_empty",
        transform: transformWhitelist.includes(col.transform) ? col.transform : "as_is",
        default: col.default === undefined ? null : col.default,
        required: Boolean(col.required)
      }));
      return {
        template_id: state.template.template_id,
        version: state.template.version,
        description: state.template.description,
        columns
      };
    }

    function download(name, payload) {
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = name;
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1500);
    }

    document.getElementById("addColumn").addEventListener("click", (evt) => {
      evt.preventDefault();
      addColumn();
    });

    document.getElementById("downloadUpdate").addEventListener("click", (evt) => {
      evt.preventDefault();
      download("export_template_update.json", currentTemplateSpec());
    });

    document.getElementById("downloadReport").addEventListener("click", (evt) => {
      evt.preventDefault();
      const spec = currentTemplateSpec();
      download("wizard_refine_report.json", {
        template_id: spec.template_id,
        columns: spec.columns.length,
        preview_rows: state.previewRows.length,
        transforms: transformWhitelist
      });
    });

    templateIdEl.addEventListener("change", syncTemplateMeta);
    templateVersionEl.addEventListener("change", syncTemplateMeta);
    templateDescriptionEl.addEventListener("change", syncTemplateMeta);

    async function boot() {
      const templatePayload = await loadJson("export_template.json", { template_id: "export_template", version: "1.0.0", description: "", columns: [] });
      const samplePayload = await loadJson("sample_records.json", { rows: [] });
      const fieldPayload = await loadJson("field_catalog.json", { fields: [] });
      state.template = templatePayload;
      state.samples = Array.isArray(samplePayload.rows) ? samplePayload.rows : [];
      state.fieldCatalog = Array.isArray(fieldPayload.fields) ? fieldPayload.fields : [];
      if (!Array.isArray(state.template.columns)) state.template.columns = [];
      state.template.columns = state.template.columns.map((col) => {
        const item = { ...col };
        const candidates = Array.isArray(item.source_candidates)
          ? item.source_candidates.filter((v) => String(v || "").trim() !== "")
          : [];
        if (candidates.length === 0 && item.source) {
          item.source_candidates = [item.source];
        } else {
          item.source_candidates = candidates;
        }
        if (!["first_non_empty", "prefer_primary_source", "highest_confidence"].includes(item.candidate_strategy)) {
          item.candidate_strategy = "first_non_empty";
        }
        return item;
      });
      templateIdEl.value = state.template.template_id || "export_template";
      templateVersionEl.value = state.template.version || "1.0.0";
      templateDescriptionEl.value = state.template.description || "";
      renderEditor();
      computePreviewRows();
      renderPreview();
    }
    boot();
  </script>
</body>
</html>
"""


def write_wizard_bundle(
    *,
    records: list[InvoiceRecord],
    base_template: ExportTemplateSpec,
    out_dir: Path,
    preview_rows: int = 20,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [record.to_dict() for record in records[:max(0, preview_rows)]]
    field_catalog = build_field_catalog(records)
    (out_dir / "export_template.json").write_text(
        json.dumps(base_template.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "sample_records.json").write_text(
        json.dumps({"rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "field_catalog.json").write_text(
        json.dumps({"fields": field_catalog, "transforms": list(TRANSFORM_WHITELIST)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "wizard.html").write_text(wizard_html(), encoding="utf-8")
    report = {
        "template_id": base_template.template_id,
        "rows": len(rows),
        "total_records": len(records),
        "columns": len(base_template.columns),
        "transforms": list(TRANSFORM_WHITELIST),
    }
    (out_dir / "wizard_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
