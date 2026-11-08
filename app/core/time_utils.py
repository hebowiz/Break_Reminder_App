"""Datetime helpers for work-session scheduling."""

from __future__ import annotations

import math
from datetime import datetime, time, timedelta


def calculate_next_break_datetime(work_minutes: int, now: datetime | None = None) -> datetime:
    """Return the absolute datetime when the next break should start."""
    base_time = now or datetime.now()
    return base_time + timedelta(minutes=max(1, int(work_minutes)))


def format_clock_time(value: datetime) -> str:
    """Format a datetime as 24-hour clock text."""
    return f"{value:%H:%M}"


def resolve_next_break_datetime(clock_time: time, now: datetime | None = None) -> datetime:
    """Resolve a minute-precision clock time to its next strictly future occurrence."""
    base_time = now or datetime.now()
    target = base_time.replace(
        hour=clock_time.hour, minute=clock_time.minute, second=0, microsecond=0
    )
    if target <= base_time:
        target += timedelta(days=1)
    return target


def remaining_minutes(target: datetime, now: datetime | None = None) -> int:
    """Round remaining time up to whole minutes, clamping elapsed targets to zero."""
    return max(0, math.ceil((target - (now or datetime.now())).total_seconds() / 60))
