"""Configuration loading and saving for MVP."""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class AppConfig:
    """Application settings used by the current MVP."""

    work_minutes: float = 25.0
    min_break_seconds: int = 30
    ntfy_enabled: bool = False
    ntfy_topic: str = ""
    notification_level: int = 2
    effects_enabled: bool = False


def _as_float(value: Any, default: float, min_value: float) -> float:
    """Convert value to float with minimum clamp and fallback."""
    if value is None:
        return default
    try:
        parsed = float(value)
        if parsed < min_value:
            raise ValueError(f"must be >= {min_value}")
    except (TypeError, ValueError):
        traceback.print_exc()
        return default
    return parsed


def _as_int(value: Any, default: int, min_value: int) -> int:
    """Convert value to int with minimum clamp and fallback."""
    if value is None:
        return default
    try:
        parsed = int(value)
        if parsed < min_value:
            raise ValueError(f"must be >= {min_value}")
    except (TypeError, ValueError):
        traceback.print_exc()
        return default
    return parsed


def _as_bool(value: Any, default: bool) -> bool:
    """Convert config value to bool with string support."""
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
    try:
        raise TypeError("must be bool")
    except Exception:
        traceback.print_exc()
    return default


def _as_str(value: Any, default: str) -> str:
    """Convert config value to str with trim."""
    if value is None:
        return default
    if not isinstance(value, str):
        try:
            raise TypeError("must be str")
        except Exception:
            traceback.print_exc()
        return default
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
    except Exception:
        traceback.print_exc()
        return default

    if not isinstance(raw, dict):
        try:
            raise TypeError("config root must be object")
        except Exception:
            traceback.print_exc()
            return default

    try:
        return AppConfig(
            work_minutes=_as_float(raw.get("work_minutes"), default.work_minutes, min_value=0.1),
            min_break_seconds=_as_int(
                raw.get("min_break_seconds"),
                default.min_break_seconds,
                min_value=5,
            ),
            ntfy_enabled=_as_bool(raw.get("ntfy_enabled"), default.ntfy_enabled),
            ntfy_topic=_as_str(raw.get("ntfy_topic"), default.ntfy_topic),
            notification_level=_as_int(
                raw.get("notification_level"),
                default.notification_level,
                min_value=1,
            ),
            effects_enabled=_as_bool(raw.get("effects_enabled"), default.effects_enabled),
        )
    except Exception:
        traceback.print_exc()
        return default


def save_config(config: AppConfig, path: Path | None = None) -> bool:
    """Save config.json without BOM. Returns True when successful."""
    config_path = path or Path("config.json")
    payload = {
        "work_minutes": round(float(config.work_minutes), 1),
        "min_break_seconds": int(config.min_break_seconds),
        "ntfy_enabled": bool(config.ntfy_enabled),
        "ntfy_topic": str(config.ntfy_topic),
        "notification_level": int(config.notification_level),
        "effects_enabled": bool(config.effects_enabled),
    }

    try:
        with config_path.open("w", encoding="utf-8", newline="\n") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        return True
    except Exception:
        traceback.print_exc()
        return False
