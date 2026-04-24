"""Configuration loading and validation stubs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppConfig:
    work_minutes: int = 50
    snooze_minutes: int = 5
    ntfy_enabled: bool = False
    ntfy_topic: str = "your-topic"
    notification_level: str = "info"
    effects_enabled: bool = True


def load_config(path: Path) -> AppConfig:
    """Load configuration from JSON in a future implementation."""
    _ = path
    return AppConfig()
