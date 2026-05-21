"""Passive always-on-top status widget for the current work session."""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from app.core.time_utils import format_clock_time
from app.state import AppState


class StatusWidget(QWidget):
    """Small transparent-for-input overlay showing the next break time."""

    def __init__(
        self,
        state_provider: Callable[[], AppState],
        next_break_provider: Callable[[], datetime | None],
        enabled: bool,
    ) -> None:
        super().__init__(None)
        self._state_provider = state_provider
        self._next_break_provider = next_break_provider
        self._enabled = bool(enabled)

        self._background = QWidget(self)
        self._title_label = QLabel("次の休憩", self._background)
        self._time_label = QLabel(self._background)

        self._update_timer = QTimer(self)
        self._update_timer.setInterval(1000)
        self._update_timer.timeout.connect(self.refresh)

        self._setup_ui()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the passive status widget."""
        self._enabled = bool(enabled)
        self.refresh()

    def refresh(self) -> None:
        """Refresh displayed content and visibility."""
        if not self._enabled:
            self.hide()
            return

        next_break_datetime = self._next_break_provider()
        if self._state_provider() != AppState.WORKING or next_break_datetime is None:
            self.hide()
            return

        remaining_seconds = max(0.0, (next_break_datetime - datetime.now()).total_seconds())
        remaining_minutes = max(0, math.ceil(remaining_seconds / 60))
        self._time_label.setText(
            f"{format_clock_time(next_break_datetime)} ({remaining_minutes}分後)"
        )
        self.adjustSize()
        self._move_to_primary_screen_top_right()
        if not self.isVisible():
            self.show()
        if not self._update_timer.isActive():
            self._update_timer.start()

    def hideEvent(self, event) -> None:  # noqa: N802, ANN001
        """Stop updates while the widget is hidden."""
        if self._state_provider() != AppState.WORKING or not self._enabled:
            self._update_timer.stop()
        super().hideEvent(event)

    def _setup_ui(self) -> None:
        """Create the small frameless translucent overlay UI."""
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._background.setObjectName("statusWidgetBackground")
        self.setStyleSheet(
            """
            QWidget#statusWidgetBackground {
                background-color: rgba(0, 0, 0, 160);
                border-radius: 8px;
            }
            QLabel {
                color: white;
                font-family: "Segoe UI", sans-serif;
            }
            """
        )

        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet("font-size: 11px; font-weight: 600;")
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._time_label.setStyleSheet("font-size: 14px; font-weight: 700;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._background)

        background_layout = QVBoxLayout(self._background)
        background_layout.setContentsMargins(14, 10, 14, 10)
        background_layout.setSpacing(2)
        background_layout.addWidget(self._title_label)
        background_layout.addWidget(self._time_label)

    def _move_to_primary_screen_top_right(self) -> None:
        """Place the widget near the top-right of the primary screen."""
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        rect = screen.availableGeometry()
        margin_x = 130
        margin_y = 0
        x = rect.x() + rect.width() - self.width() - margin_x
        y = rect.y() + margin_y
        self.move(x, y)
