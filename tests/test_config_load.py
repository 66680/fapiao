from pathlib import Path

from invstruct.config import load_settings


def test_load_yaml_settings(tmp_path: Path) -> None:
    cfg = tmp_path / "app.yaml"
    cfg.write_text(
        "\n".join(
            [
                "locale: en-US",
                "currency: USD",
                "template_dir: configs/custom_templates",
                "log_level: DEBUG",
                "low_conf: 0.8",
                "anomalies:",
                "  amount_mismatch:",
                "    tolerance: 0.02",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_settings(cfg)
    assert settings.locale == "en-US"
    assert settings.currency == "USD"
    assert settings.template_dir == "configs/custom_templates"
    assert settings.log_level == "DEBUG"
    assert settings.low_conf == 0.8
    assert settings.anomalies.low_conf.threshold == 0.8
    assert settings.anomalies.amount_mismatch.tolerance == 0.02
