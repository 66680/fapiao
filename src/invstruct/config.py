from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DuplicateConfig(BaseModel):
    enabled: bool = True
    use_sha256: bool = True
    use_business_key: bool = True
    business_key_fields: list[str] = Field(
        default_factory=lambda: ["invoice_number", "issue_date", "total_amount_gross", "merchant_tax_id"]
    )


class AmountMismatchConfig(BaseModel):
    enabled: bool = True
    tolerance: float = 0.01


class LowConfConfig(BaseModel):
    enabled: bool = True
    threshold: float = 0.75
    require_core_fields: bool = True
    missing_severity: Literal["info", "warning", "critical"] = "warning"


class AnomalyConfig(BaseModel):
    duplicate: DuplicateConfig = Field(default_factory=DuplicateConfig)
    amount_mismatch: AmountMismatchConfig = Field(default_factory=AmountMismatchConfig)
    low_conf: LowConfConfig = Field(default_factory=LowConfConfig)


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INVSTRUCT_", extra="ignore")

    locale: str = "zh-CN"
    currency: str = "CNY"
    template_dir: str = "configs/templates"
    export_template_dir: str = "configs/export_templates"
    log_level: str = "INFO"
    low_conf: float = 0.75
    ocr_engine: str = "mock"
    pdf_mode: str = "merge"
    max_pdf_pages: int = 50
    pdf_enable_line_merge: bool = True
    pdf_line_merge_y_tol: float = 3.0
    rules_amount_keyword_window: int = 1
    rules_amount_prefer_keyword: bool = True
    rules_date_prefer_issue_keywords: bool = True
    rules_enable_text_normalize: bool = True
    rules_debug_top_k: int = 5
    anomalies: AnomalyConfig = Field(default_factory=AnomalyConfig)
    job_dir: str = "out/jobs"
    job_retention_days: int = 30
    job_keep_last: int = 100
    job_cleanup_on_startup: bool = False


def load_yaml(path: str | Path) -> dict[str, Any]:
    yaml_path = Path(path)
    if not yaml_path.exists():
        return {}
    content = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    return content if isinstance(content, dict) else {}


def _has_nested(data: dict[str, Any], *path: str) -> bool:
    cursor: Any = data
    for key in path:
        if not isinstance(cursor, dict) or key not in cursor:
            return False
        cursor = cursor[key]
    return True


def load_settings(path: str | Path | None = None) -> AppSettings:
    data = load_yaml(path) if path else {}
    settings = AppSettings(**data)
    has_yaml_anomaly_threshold = _has_nested(data, "anomalies", "low_conf", "threshold")

    if not has_yaml_anomaly_threshold:
        settings = settings.model_copy(
            update={
                "anomalies": settings.anomalies.model_copy(
                    update={"low_conf": settings.anomalies.low_conf.model_copy(update={"threshold": settings.low_conf})}
                )
            }
        )

    overrides: dict[str, Any] = {}
    env_map = {
        "locale": "INVSTRUCT_LOCALE",
        "currency": "INVSTRUCT_CURRENCY",
        "template_dir": "INVSTRUCT_TEMPLATE_DIR",
        "export_template_dir": "INVSTRUCT_EXPORT_TEMPLATE_DIR",
        "log_level": "INVSTRUCT_LOG_LEVEL",
        "low_conf": "INVSTRUCT_LOW_CONF",
        "ocr_engine": "INVSTRUCT_OCR_ENGINE",
        "pdf_mode": "INVSTRUCT_PDF_MODE",
        "max_pdf_pages": "INVSTRUCT_MAX_PDF_PAGES",
        "pdf_enable_line_merge": "INVSTRUCT_PDF_ENABLE_LINE_MERGE",
        "pdf_line_merge_y_tol": "INVSTRUCT_PDF_LINE_MERGE_Y_TOL",
        "rules_amount_keyword_window": "INVSTRUCT_RULES_AMOUNT_KEYWORD_WINDOW",
        "rules_amount_prefer_keyword": "INVSTRUCT_RULES_AMOUNT_PREFER_KEYWORD",
        "rules_date_prefer_issue_keywords": "INVSTRUCT_RULES_DATE_PREFER_ISSUE_KEYWORDS",
        "rules_enable_text_normalize": "INVSTRUCT_RULES_ENABLE_TEXT_NORMALIZE",
        "rules_debug_top_k": "INVSTRUCT_RULES_DEBUG_TOP_K",
        "job_dir": "INVSTRUCT_JOB_DIR",
        "job_retention_days": "INVSTRUCT_JOB_RETENTION_DAYS",
        "job_keep_last": "INVSTRUCT_JOB_KEEP_LAST",
        "job_cleanup_on_startup": "INVSTRUCT_JOB_CLEANUP_ON_STARTUP",
    }
    for field_name, env_name in env_map.items():
        value = os.getenv(env_name)
        if value is None:
            continue
        if field_name == "low_conf":
            overrides[field_name] = float(value)
        elif field_name == "pdf_line_merge_y_tol":
            overrides[field_name] = float(value)
        elif field_name in {"max_pdf_pages", "rules_amount_keyword_window", "rules_debug_top_k"}:
            overrides[field_name] = int(value)
        elif field_name in {"job_retention_days", "job_keep_last"}:
            overrides[field_name] = int(value)
        elif field_name in {
            "job_cleanup_on_startup",
            "pdf_enable_line_merge",
            "rules_amount_prefer_keyword",
            "rules_date_prefer_issue_keywords",
            "rules_enable_text_normalize",
        }:
            overrides[field_name] = str(value).strip().lower() in {"1", "true", "yes", "on"}
        else:
            overrides[field_name] = value

    if overrides:
        settings = settings.model_copy(update=overrides)

    low_conf_env = os.getenv("INVSTRUCT_LOW_CONF")
    if low_conf_env is not None:
        threshold = float(low_conf_env)
        settings = settings.model_copy(
            update={
                "low_conf": threshold,
                "anomalies": settings.anomalies.model_copy(
                    update={"low_conf": settings.anomalies.low_conf.model_copy(update={"threshold": threshold})}
                ),
            }
        )
    elif not has_yaml_anomaly_threshold:
        settings = settings.model_copy(
            update={
                "anomalies": settings.anomalies.model_copy(
                    update={"low_conf": settings.anomalies.low_conf.model_copy(update={"threshold": settings.low_conf})}
                )
            }
        )

    amount_tolerance_env = os.getenv("INVSTRUCT_AMOUNT_TOLERANCE")
    if amount_tolerance_env is not None:
        tolerance = float(amount_tolerance_env)
        settings = settings.model_copy(
            update={
                "anomalies": settings.anomalies.model_copy(
                    update={
                        "amount_mismatch": settings.anomalies.amount_mismatch.model_copy(update={"tolerance": tolerance})
                    }
                )
            }
        )

    return settings
