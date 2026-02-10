from __future__ import annotations

from pathlib import Path

import yaml

from invstruct.export_templates.models import ExportTemplateSpec


def load_export_template(path: str | Path) -> ExportTemplateSpec:
    template_path = Path(path)
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        payload = {}
    return ExportTemplateSpec.model_validate(payload)


def load_export_templates(template_dir: str | Path) -> list[ExportTemplateSpec]:
    root = Path(template_dir)
    if not root.exists():
        return []
    templates: list[ExportTemplateSpec] = []
    for path in sorted(root.glob("*.yaml")):
        templates.append(load_export_template(path))
    for path in sorted(root.glob("*.yml")):
        templates.append(load_export_template(path))
    return templates


def get_export_template(template_ref: str, template_dir: str | Path) -> ExportTemplateSpec | None:
    candidate = Path(template_ref)
    if candidate.exists():
        return load_export_template(candidate)
    for template in load_export_templates(template_dir):
        if template.template_id == template_ref:
            return template
    return None
