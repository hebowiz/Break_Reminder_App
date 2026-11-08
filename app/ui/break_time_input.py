"""Shared clock-time input for starting and resuming work."""

from __future__ import annotations

from datetime import datetime, time

from PySide6.QtCore import QTime, QTimer
from PySide6.QtGui import QHideEvent, QShowEvent
from PySide6.QtWidgets import QFormLayout, QLabel, QTimeEdit, QWidget

from app.core.time_utils import (
    calculate_next_break_datetime,
    remaining_minutes,
    resolve_next_break_datetime,
)


class BreakTimeInput(QWidget):
    """Resolve the selected clock time at confirmation, retaining its date thereafter."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.time_edit = QTimeEdit(self)
        self.time_edit.setDisplayFormat("HH:mm")
        self.remaining_label = QLabel(self)
        self.remaining_label.setWordWrap(True)
        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow("次の休憩", self.time_edit)
        form.addRow("", self.remaining_label)
        self.time_edit.timeChanged.connect(self.refresh)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(1000)
        self._refresh_timer.timeout.connect(self.refresh)

    def reset(self, default_minutes: int) -> None:
        """Use the settings duration and current time each time the dialog opens."""
        target = calculate_next_break_datetime(default_minutes)
        self.time_edit.setTime(QTime(target.hour, target.minute))
        self.refresh()

    def selected_datetime(self, now: datetime | None = None) -> datetime:
        """Return the next occurrence of the selected minute with its full date."""
        selected = self.time_edit.time()
        return resolve_next_break_datetime(time(selected.hour(), selected.minute()), now)

    def refresh(self) -> None:
        """Keep the preview current even while a dialog remains open."""
        now = datetime.now()
        minutes = remaining_minutes(self.selected_datetime(now), now)
        self.remaining_label.setText(f"休憩まで: {minutes}分後")

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()
        self._refresh_timer.start()

    def hideEvent(self, event: QHideEvent) -> None:  # noqa: N802
        self._refresh_timer.stop()
        super().hideEvent(event)
