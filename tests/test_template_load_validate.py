from pathlib import Path

from invstruct.templates.loader import load_template


def test_load_template_from_yaml(tmp_path: Path) -> None:
    template_file = tmp_path / "simple.yaml"
    template_file.write_text(
        "\n".join(
            [
                "template_id: simple_receipt",
                "version: 1.0.0",
                "locale: zh-CN",
                "doc_type: receipt",
                "aliases:",
                "  total_amount_gross: [\"合计\", \"总计\"]",
                "regex:",
                "  total_amount_gross: \"([¥￥]?\\\\s?\\\\d+[\\\\.,]?\\\\d{0,2})\"",
                "anomalies:",
                "  duplicate:",
                "    enabled: false",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_template(template_file)
    assert spec.template_id == "simple_receipt"
    assert spec.doc_type == "receipt"
    assert "total_amount_gross" in spec.aliases
    assert spec.anomalies is not None
    assert spec.anomalies.duplicate is not None
    assert spec.anomalies.duplicate.enabled is False
