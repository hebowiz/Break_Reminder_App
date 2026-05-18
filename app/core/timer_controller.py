"""Timer control logic for MVP."""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import QTimer

from app.core.time_utils import calculate_next_break_datetime
from app.infra.logger import SQLiteLogger
from app.infra.ntfy_notifier import NtfyNotifier
from app.state import AppState


class TimerController:
    """Control work/break state transitions and work timer lifecycle."""

    def __init__(
        self,
        work_minutes: int,
        on_work_timer_elapsed: Callable[[], None] | None = None,
        logger: SQLiteLogger | None = None,
        notifier: NtfyNotifier | None = None,
    ) -> None:
        self._work_minutes = max(1, int(work_minutes))
        self._on_work_timer_elapsed = on_work_timer_elapsed
        self._logger = logger
        self._notifier = notifier

        self._state = AppState.STOPPED
        self.current_work_duration_minutes = self._work_minutes
        self.next_break_datetime: datetime | None = None
        self._break_started_at: float | None = None
        self._notification_shown_at: float | None = None
        self._active_session_id: int | None = None

        self._work_timer = QTimer()
        self._work_timer.setInterval(1000)
        self._work_timer.setSingleShot(False)
        self._work_timer.timeout.connect(self._handle_work_timer_elapsed)

    @property
    def state(self) -> AppState:
        """Return current app state."""
        return self._state

    def start_work(self, work_minutes: int | None = None) -> None:
        """Start a work session timer."""
        self.current_work_duration_minutes = max(
            1,
            int(self._work_minutes if work_minutes is None else work_minutes),
        )
        self.next_break_datetime = calculate_next_break_datetime(
            self.current_work_duration_minutes
        )
        self._break_started_at = None
        self._notification_shown_at = None
        self._state = AppState.WORKING
        self._start_work_timer()
        if self._logger is not None:
            self._active_session_id = self._logger.create_session()

    def update_settings(self, work_minutes: int, notifier: NtfyNotifier | None) -> None:
        """Update timer-related settings for future work sessions."""
        self._work_minutes = max(1, int(work_minutes))
        self._notifier = notifier

    def stop_work(self, end_reason: str = "stopped") -> None:
        """Stop all active timers and return to stopped state."""
        self._work_timer.stop()
        if self._logger is not None and self._active_session_id is not None:
            self._logger.end_session(self._active_session_id, end_reason)
        self._active_session_id = None
        self.next_break_datetime = None
        self._break_started_at = None
        self._notification_shown_at = None
        self._state = AppState.STOPPED

    def break_started(self) -> None:
        """Switch to break state and reset break start time to now."""
        self._work_timer.stop()
        self.next_break_datetime = None
        now = time.monotonic()
        self._break_started_at = now
        self._notification_shown_at = now
        self._state = AppState.BREAKING

    def resume_work(self, work_minutes: int | None = None) -> None:
        """Resume work by starting a new configured work session."""
        if self._logger is not None and self._active_session_id is not None:
            self._logger.mark_work_resumed(self._active_session_id)
        self.start_work(work_minutes)

    def get_break_elapsed_seconds(self) -> int:
        """Return elapsed break seconds since latest break start."""
        if self._break_started_at is None:
            return 0
        return max(0, int(time.monotonic() - self._break_started_at))

    def is_break_short(self, min_break_seconds: int) -> bool:
        """Return True when break duration is shorter than configured minimum."""
        return self.get_break_elapsed_seconds() < max(1, int(min_break_seconds))

    def get_remaining_seconds(self) -> int | None:
        """Return remaining seconds for active work timer, if any."""
        if self._state != AppState.WORKING or self.next_break_datetime is None:
            return None
        remaining_seconds = (self.next_break_datetime - datetime.now()).total_seconds()
        return max(0, math.ceil(remaining_seconds))

    def _start_work_timer(self) -> None:
        """Start periodic checks against the absolute next-break datetime."""
        self._work_timer.start()

    def _handle_work_timer_elapsed(self) -> None:
        """Stop work and request break UI when the absolute target is reached."""
        if self._state != AppState.WORKING or self.next_break_datetime is None:
            self._work_timer.stop()
            return
        if datetime.now() < self.next_break_datetime:
            return

        if self._logger is not None and self._active_session_id is not None:
            self._logger.mark_timer_fired(self._active_session_id)
        self.break_started()
        if self._notifier is not None:
            self._notifier.send_break_notification()
        if self._on_work_timer_elapsed is not None:
            self._on_work_timer_elapsed()
