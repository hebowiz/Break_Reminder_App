"""Configuration loading for MVP."""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class AppConfig:
    """Application settings used by the current MVP."""

    work_minutes: int = 25
    min_break_seconds: int = 30
    ntfy_enabled: bool = False
    ntfy_topic: str = ""
    notification_level: int = 2
    effects_enabled: bool = False


def _parse_positive_int(value: Any, field_name: str, default: int) -> int:
    """Parse positive int value; raise when invalid."""
    if value is None:
        return default
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{field_name} must be > 0")
    return parsed


def _parse_bool(value: Any, field_name: str, default: bool) -> bool:
    """Parse bool with basic string compatibility; raise when invalid."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise TypeError(f"{field_name} must be bool")


def _parse_str(value: Any, field_name: str, default: str) -> str:
    """Parse string value; raise when invalid."""
    if value is None:
        return default
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be str")
    return value.strip()


def load_config(path: Path | None = None) -> AppConfig:
    """Load config.json when available, otherwise return defaults."""
    default = AppConfig()
    config_path = path or Path("config.json")
    if not config_path.exists():
        return default

    try:
        with config_path.open("r", encoding="utf-8-sig") as fh:
            raw = json.load(fh)

        if not isinstance(raw, dict):
            raise TypeError("config root must be object")

        return AppConfig(
            work_minutes=_parse_positive_int(raw.get("work_minutes"), "work_minutes", default.work_minutes),
            min_break_seconds=_parse_positive_int(
                raw.get("min_break_seconds"),
                "min_break_seconds",
                default.min_break_seconds,
            ),
            ntfy_enabled=_parse_bool(raw.get("ntfy_enabled"), "ntfy_enabled", default.ntfy_enabled),
            ntfy_topic=_parse_str(raw.get("ntfy_topic"), "ntfy_topic", default.ntfy_topic),
            notification_level=_parse_positive_int(
                raw.get("notification_level"),
                "notification_level",
                default.notification_level,
            ),
            effects_enabled=_parse_bool(
                raw.get("effects_enabled"),
                "effects_enabled",
                default.effects_enabled,
            ),
        )
    except Exception:
        traceback.print_exc()
        return default
