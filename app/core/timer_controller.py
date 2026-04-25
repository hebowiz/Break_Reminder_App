"""Timer control logic for MVP."""

from __future__ import annotations

import math
import time
from collections.abc import Callable

from PySide6.QtCore import QTimer

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
        self._break_started_at: float | None = None
        self._notification_shown_at: float | None = None
        self._active_session_id: int | None = None

        self._work_timer = QTimer()
        self._work_timer.setSingleShot(True)
        self._work_timer.timeout.connect(self._handle_work_timer_elapsed)

    @property
    def state(self) -> AppState:
        """Return current app state."""
        return self._state

    def start_work(self) -> None:
        """Start a work session timer."""
        self._start_work_timer(self._work_minutes)
        self._break_started_at = None
        self._notification_shown_at = None
        self._state = AppState.WORKING
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
        self._break_started_at = None
        self._notification_shown_at = None
        self._state = AppState.STOPPED

    def break_started(self) -> None:
        """Switch to break state and reset break start time to now."""
        self._work_timer.stop()
        now = time.monotonic()
        self._break_started_at = now
        self._notification_shown_at = now
        self._state = AppState.BREAKING

    def resume_work(self) -> None:
        """Resume work by starting a new configured work session."""
        if self._logger is not None and self._active_session_id is not None:
            self._logger.mark_work_resumed(self._active_session_id)
        self.start_work()

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
        if self._state != AppState.WORKING:
            return None
        remaining_ms = self._work_timer.remainingTime()
        if remaining_ms < 0:
            return None
        return max(0, math.ceil(remaining_ms / 1000))

    def _start_work_timer(self, minutes: int) -> None:
        """Start single-shot timer for the given minutes."""
        duration_ms = max(1, int(minutes)) * 60 * 1000
        self._work_timer.start(duration_ms)

    def _handle_work_timer_elapsed(self) -> None:
        """Stop work and request break UI when timer completes."""
        if self._logger is not None and self._active_session_id is not None:
            self._logger.mark_timer_fired(self._active_session_id)
        self.break_started()
        if self._notifier is not None:
            self._notifier.send_break_notification()
        if self._on_work_timer_elapsed is not None:
            self._on_work_timer_elapsed()
