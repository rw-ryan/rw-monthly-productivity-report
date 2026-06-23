"""Shared paths and report-month settings for monthly productivity scripts."""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("PRODUCTIVITY_DATA_DIR", REPO_ROOT / "data"))


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def load_config() -> dict:
    config_path = DATA_DIR / "config.json"
    if config_path.exists():
        cfg = json.loads(config_path.read_text())
    else:
        example = REPO_ROOT / "config.example.json"
        if example.exists():
            cfg = json.loads(example.read_text())
        else:
            raise FileNotFoundError(
                f"Missing {config_path}. Copy config.example.json to data/config.json and edit."
            )

    month_start = _parse_date(cfg["report_month_start"])
    month_end = _parse_date(cfg["report_month_end"])
    next_month_start = _parse_date(cfg["next_month_start"])

    data_dir = Path(cfg.get("data_dir", DATA_DIR))
    if not data_dir.is_absolute():
        data_dir = REPO_ROOT / data_dir

    return {
        **cfg,
        "data_dir": data_dir,
        "report_month_start": month_start,
        "report_month_end": month_end,
        "next_month_start": next_month_start,
        "csv_file": data_dir / cfg["csv_file"],
        "cache_dir": data_dir / cfg.get("cache_dir", "epic-cache"),
        "universe_file": data_dir / cfg["universe_file"],
        "report_file": data_dir / cfg.get("report_file", "epic-report.json"),
        "attention_file": data_dir / cfg.get("attention_file", "confluence-attention.json"),
        "adf_output": data_dir / cfg.get("adf_output", "productivity-update-confluence.adf.json"),
        "jql_urls_output": data_dir / cfg.get("jql_urls_output", "jira-work-item-urls.txt"),
    }


def month_short_name(report_month_label: str) -> str:
    """'May 2026' -> 'May'."""
    return report_month_label.split()[0]


def next_month_short_name(next_month_start: date) -> str:
    return next_month_start.strftime("%B")
