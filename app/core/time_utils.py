"""Datetime helpers for work-session scheduling."""

from __future__ import annotations

from datetime import datetime, timedelta


def calculate_next_break_datetime(work_minutes: int, now: datetime | None = None) -> datetime:
    """Return the absolute datetime when the next break should start."""
    base_time = now or datetime.now()
    return base_time + timedelta(minutes=max(1, int(work_minutes)))


def format_clock_time(value: datetime) -> str:
    """Format a datetime as 24-hour clock text."""
    return f"{value:%H:%M}"
