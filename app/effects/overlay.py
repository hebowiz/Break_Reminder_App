"""Fullscreen translucent overlay effect for break prompts."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from app.ui.screen_utils import get_screen_at_cursor


class FullscreenOverlay(QWidget):
    """Primary-screen overlay with translucent background and center text."""

    def __init__(self, text: str = "休憩時間です") -> None:
        super().__init__(None)
        self._text = text
        self._alpha = 145
        self._alpha_step = 6

        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(120)
        self._pulse_timer.timeout.connect(self._tick_pulse)

        self._setup_window()
        self._setup_ui()

    def set_text(self, text: str) -> None:
        """Update center text shown on overlay."""
        self._text = text
        self._label.setText(text)

    def show_on_cursor_screen(self) -> None:
        """Show overlay on the screen where cursor currently exists."""
        screen = get_screen_at_cursor()
        if screen is None:
            return

        self.setGeometry(screen.geometry())
        if not self._pulse_timer.isActive():
            self._pulse_timer.start()
        self.show()

    def hide_overlay(self) -> None:
        """Hide overlay and stop animation."""
        self._pulse_timer.stop()
        self.hide()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        """Paint translucent fullscreen background."""
        _ = event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, self._alpha))

    def _setup_window(self) -> None:
        """Configure transparent always-on-top overlay window."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

    def _setup_ui(self) -> None:
        """Build centered label."""
        self._label = QLabel(self._text, self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet(
            "color: white; font-size: 52px; font-weight: 700;"
            "padding: 24px; background-color: rgba(0, 0, 0, 0);"
        )

        layout = QVBoxLayout(self)
        layout.addStretch(1)
        layout.addWidget(self._label)
        layout.addStretch(1)

    def _tick_pulse(self) -> None:
        """Run subtle pulse on background alpha."""
        self._alpha += self._alpha_step
        if self._alpha > 170:
            self._alpha = 170
            self._alpha_step = -6
        elif self._alpha < 125:
            self._alpha = 125
            self._alpha_step = 6
        self.update()
