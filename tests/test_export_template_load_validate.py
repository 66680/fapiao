from __future__ import annotations

from invstruct.export_templates.loader import get_export_template, load_export_templates


def test_export_template_load_validate() -> None:
    templates = load_export_templates("configs/export_templates")
    assert templates
    template_ids = {item.template_id for item in templates}
    assert "generic_expense_v1" in template_ids
    assert "generic_expense_minimal_v1" in template_ids

    selected = get_export_template("generic_expense_v1", "configs/export_templates")
    assert selected is not None
    assert selected.template_id == "generic_expense_v1"
    assert len(selected.columns) >= 3
