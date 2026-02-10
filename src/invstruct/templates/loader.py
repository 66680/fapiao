from __future__ import annotations

from pathlib import Path

import yaml

from invstruct.templates.models import TemplateSpec


def load_template(path: str | Path) -> TemplateSpec:
    template_path = Path(path)
    data = yaml.safe_load(template_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        data = {}
    return TemplateSpec(**data)


def load_templates(template_dir: str | Path) -> list[TemplateSpec]:
    root = Path(template_dir)
    if not root.exists():
        return []
    specs: list[TemplateSpec] = []
    for path in sorted(root.glob("*.yaml")):
        specs.append(load_template(path))
    for path in sorted(root.glob("*.yml")):
        specs.append(load_template(path))
    return specs

