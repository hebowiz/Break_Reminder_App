"""Configuration loading for MVP."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class AppConfig:
    """Application settings used by the current MVP."""

    work_minutes: int = 1
    snooze_minutes: int = 1
    notification_level: int = 2
    min_break_seconds: int = 30


def _coerce_positive_int(value: Any, default: int) -> int:
    """Convert config value to positive int, falling back to default."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed <= 0:
        return default
    return parsed


def load_config(path: Path | None = None) -> AppConfig:
    """Load config.json when available, otherwise return defaults."""
    config_path = path or Path("config.json")
    if not config_path.exists():
        return AppConfig()

    try:
        with config_path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return AppConfig()

    if not isinstance(raw, dict):
        return AppConfig()

    default = AppConfig()
    return AppConfig(
        work_minutes=_coerce_positive_int(raw.get("work_minutes"), default.work_minutes),
        snooze_minutes=_coerce_positive_int(raw.get("snooze_minutes"), default.snooze_minutes),
        notification_level=_coerce_positive_int(raw.get("notification_level"), default.notification_level),
        min_break_seconds=_coerce_positive_int(
            raw.get("min_break_seconds"),
            default.min_break_seconds,
        ),
    )
