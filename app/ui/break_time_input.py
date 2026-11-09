"""Shared clock-time input for starting and resuming work."""

from __future__ import annotations

from datetime import datetime, time

from PySide6.QtCore import QTimer
from PySide6.QtGui import QHideEvent, QShowEvent
from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QLabel, QSpinBox, QWidget

from app.core.time_utils import (
    calculate_next_break_datetime,
    remaining_minutes,
    resolve_next_break_datetime,
)


class TwoDigitSpinBox(QSpinBox):
    """Independent, wrapping clock field displayed with two digits."""

    def __init__(self, maximum: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setRange(0, maximum)
        self.setSingleStep(1)
        self.setWrapping(True)

    def textFromValue(self, value: int) -> str:  # noqa: N802
        return f"{value:02d}"


class BreakTimeInput(QWidget):
    """Resolve the selected clock time at confirmation, retaining its date thereafter."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.hour_spin = TwoDigitSpinBox(23, self)
        self.minute_spin = TwoDigitSpinBox(59, self)
        time_fields = QHBoxLayout()
        time_fields.setContentsMargins(0, 0, 0, 0)
        time_fields.addWidget(self.hour_spin)
        time_fields.addWidget(QLabel("時", self))
        time_fields.addWidget(self.minute_spin)
        time_fields.addWidget(QLabel("分", self))
        self.remaining_label = QLabel(self)
        self.remaining_label.setWordWrap(True)
        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow("次の休憩", time_fields)
        form.addRow("休憩まで", self.remaining_label)
        self.hour_spin.valueChanged.connect(self.refresh)
        self.minute_spin.valueChanged.connect(self.refresh)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(1000)
        self._refresh_timer.timeout.connect(self.refresh)

    def reset(self, default_minutes: int) -> None:
        """Use the settings duration and current time each time the dialog opens."""
        target = calculate_next_break_datetime(default_minutes)
        self.hour_spin.setValue(target.hour)
        self.minute_spin.setValue(target.minute)
        self.refresh()

    def selected_datetime(self, now: datetime | None = None) -> datetime:
        """Return the next occurrence of the selected minute with its full date."""
        selected = time(self.hour_spin.value(), self.minute_spin.value())
        return resolve_next_break_datetime(selected, now)

    def refresh(self) -> None:
        """Keep the preview current even while a dialog remains open."""
        now = datetime.now()
        minutes = remaining_minutes(self.selected_datetime(now), now)
        self.remaining_label.setText(f"{minutes}分後")

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()
        self._refresh_timer.start()

    def hideEvent(self, event: QHideEvent) -> None:  # noqa: N802
        self._refresh_timer.stop()
        super().hideEvent(event)
