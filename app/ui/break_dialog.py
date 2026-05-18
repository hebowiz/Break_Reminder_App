"""Break prompt dialog for MVP."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QCloseEvent, QHideEvent, QKeyEvent
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)
from app.core.time_utils import calculate_next_break_datetime, format_clock_time
from app.infra.idle_tracker import IdleTracker
from app.ui.screen_utils import get_screen_at_cursor


def format_next_break_time(minutes: int) -> str:
    """Return the next break clock time for a work duration."""
    return format_clock_time(calculate_next_break_datetime(minutes))


class WorkDurationDialog(QDialog):
    """Ask for the work duration used by the next session."""

    def __init__(self, parent: QDialog | None = None) -> None:
        super().__init__(parent)
        self._duration_spin: QSpinBox | None = None
        self._next_break_label: QLabel | None = None
        self._setup_ui()

    def ask(self, default_minutes: int) -> tuple[bool, int]:
        """Show duration input dialog and return (accepted, minutes)."""
        default_value = max(1, int(default_minutes))
        if self._duration_spin is not None:
            self._duration_spin.setValue(default_value)
        self._update_next_break_time(default_value)
        accepted = self.exec() == QDialog.DialogCode.Accepted
        minutes = default_value
        if self._duration_spin is not None:
            minutes = int(self._duration_spin.value())
        return accepted, minutes

    def _setup_ui(self) -> None:
        """Build work duration input UI."""
        self.setWindowTitle("作業時間")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setMinimumWidth(300)

        self._duration_spin = QSpinBox(self)
        self._duration_spin.setRange(1, 240)
        self._duration_spin.setSingleStep(1)
        self._duration_spin.setSuffix(" 分")
        self._duration_spin.valueChanged.connect(self._update_next_break_time)

        self._next_break_label = QLabel(self)
        self._next_break_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("作業時間", self._duration_spin)
        form.addRow("", self._next_break_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _update_next_break_time(self, minutes: int) -> None:
        """Refresh next break time preview."""
        if self._next_break_label is None:
            return
        self._next_break_label.setText(f"次の休憩: {format_next_break_time(minutes)}")


class EndWorkConfirmDialog(QDialog):
    """Confirmation dialog to prevent accidental work-end action."""

    def __init__(self, end_confirm_message: str, parent: QDialog | None = None) -> None:
        super().__init__(parent)
        self._confirmed = False
        self._end_confirm_message = end_confirm_message
        self._memo_input: QLineEdit | None = None
        self._setup_ui()

    def ask(self) -> tuple[bool, str]:
        """Show confirmation dialog and return (confirmed, memo)."""
        self._confirmed = False
        if self._memo_input is not None:
            self._memo_input.clear()
        self.exec()
        memo = ""
        if self._memo_input is not None:
            memo = self._memo_input.text().strip()
        return self._confirmed, memo

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """Ignore Enter/Escape to avoid accidental confirmation/close."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Escape):
            event.ignore()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Treat close button as 'continue working'."""
        self._confirmed = False
        event.accept()

    def _setup_ui(self) -> None:
        """Build minimal confirmation UI."""
        self.setWindowTitle("終了確認")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        label = QLabel(self._end_confirm_message, self)
        label.setWordWrap(True)
        layout.addWidget(label)

        confirm_button = QPushButton("本当に終了", self)
        continue_button = QPushButton("作業を続ける", self)

        for button in (confirm_button, continue_button):
            button.setAutoDefault(False)
            button.setDefault(False)

        confirm_button.clicked.connect(self._confirm_end_work)
        continue_button.clicked.connect(self._continue_work)

        layout.addWidget(confirm_button)
        layout.addWidget(continue_button)

        self._memo_input = QLineEdit(self)
        self._memo_input.setPlaceholderText("終了理由やメモ（任意）")
        layout.addWidget(self._memo_input)

    def _confirm_end_work(self) -> None:
        """Confirm end-work request."""
        self._confirmed = True
        self.accept()

    def _continue_work(self) -> None:
        """Cancel end-work request and continue break flow."""
        self._confirmed = False
        self.reject()


class BreakDialog(QDialog):
    """Display break prompt actions without blocking the app."""

    ALREADY_IDLE_THRESHOLD_SECONDS = 30

    ACTION_BREAK_DONE = "break_done"
    ACTION_END_WORK = "end_work"

    MESSAGE_NORMAL = "normal"
    MESSAGE_TOO_SHORT = "too_short"

    def __init__(
        self,
        on_decision: Callable[[str, str | None, int | None], None],
        break_normal_message: str,
        break_too_short_message: str,
        end_confirm_message: str,
        default_work_minutes: int,
        min_break_seconds: int,
        idle_tracker: IdleTracker | None = None,
        on_break_satisfied: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(None)
        self._on_decision = on_decision
        self._on_break_satisfied = on_break_satisfied
        self._break_normal_message = break_normal_message
        self._break_too_short_message = break_too_short_message
        self._default_work_minutes = max(1, int(default_work_minutes))
        self._min_break_seconds = max(1, int(min_break_seconds))
        self._idle_tracker = idle_tracker
        self._message_label: QLabel | None = None
        self._idle_label: QLabel | None = None
        self._duration_spin: QSpinBox | None = None
        self._next_break_label: QLabel | None = None
        self._break_done_button: QPushButton | None = None
        self._break_satisfied = False
        self._was_already_idle = False
        self._waiting_for_return_after_satisfied = False
        self._fallback_elapsed_seconds = 0

        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(1000)
        self._idle_timer.timeout.connect(self._refresh_idle_info)

        self._confirm_dialog = EndWorkConfirmDialog(end_confirm_message, self)
        self._setup_ui()

    def open_prompt(self, message_kind: str = MESSAGE_NORMAL) -> None:
        """Open the dialog in non-modal mode and keep it on top."""
        self._apply_message(message_kind)
        self._reset_work_duration()
        self._break_satisfied = False
        self._was_already_idle = self._detect_already_idle()
        self._waiting_for_return_after_satisfied = False
        self._fallback_elapsed_seconds = 0
        if self._break_done_button is not None:
            self._break_done_button.setEnabled(False)
        if self._idle_tracker is not None:
            self._idle_tracker.reset()
        self._refresh_idle_info()
        if not self._idle_timer.isActive():
            self._idle_timer.start()
        self._place_on_cursor_screen()
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.show()
        self.raise_()

    def hideEvent(self, event: QHideEvent) -> None:  # noqa: N802
        """Stop sampling loop when dialog is hidden."""
        self._idle_timer.stop()
        super().hideEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """Ignore Enter/Escape to avoid accidental action."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Escape):
            event.ignore()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Disable close via title-bar close button for MVP."""
        event.ignore()

    def _setup_ui(self) -> None:
        """Create minimum break prompt UI with two actions."""
        self.setWindowTitle("休憩の時間です")
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)
        self._message_label = QLabel(self)
        self._message_label.setWordWrap(True)
        layout.addWidget(self._message_label)

        self._idle_label = QLabel(self)
        self._idle_label.setWordWrap(True)
        layout.addWidget(self._idle_label)

        self._duration_spin = QSpinBox(self)
        self._duration_spin.setRange(1, 240)
        self._duration_spin.setSingleStep(1)
        self._duration_spin.setSuffix(" 分")
        self._duration_spin.valueChanged.connect(self._update_next_break_time)

        self._next_break_label = QLabel(self)
        self._next_break_label.setWordWrap(True)

        duration_form = QFormLayout()
        duration_form.addRow("作業時間", self._duration_spin)
        duration_form.addRow("", self._next_break_label)
        layout.addLayout(duration_form)

        break_done_button = QPushButton("作業再開", self)
        end_work_button = QPushButton("今日は終了", self)

        for button in (break_done_button, end_work_button):
            button.setAutoDefault(False)
            button.setDefault(False)

        break_done_button.clicked.connect(lambda: self._decide(self.ACTION_BREAK_DONE))
        end_work_button.clicked.connect(self._confirm_end_work)
        self._break_done_button = break_done_button

        layout.addWidget(break_done_button)
        layout.addWidget(end_work_button)

        self._apply_message(self.MESSAGE_NORMAL)
        self._reset_work_duration()

    def _apply_message(self, message_kind: str) -> None:
        """Update prompt text according to message context."""
        if self._message_label is None:
            return
        if message_kind == self.MESSAGE_TOO_SHORT:
            self._message_label.setText(self._break_too_short_message)
            return
        self._message_label.setText(self._break_normal_message)

    def _refresh_idle_info(self) -> None:
        """Update idle status text while the break dialog is open."""
        if self._idle_label is None:
            return
        if self._break_satisfied:
            self._idle_label.setText("")
            if self._break_done_button is not None:
                self._break_done_button.setEnabled(True)
            if self._waiting_for_return_after_satisfied and self._has_user_returned():
                self._waiting_for_return_after_satisfied = False
                self._idle_timer.stop()
                if self._on_break_satisfied is not None:
                    self._on_break_satisfied()
            return
        if self._idle_tracker is None:
            self._fallback_elapsed_seconds += 1
            remaining = max(0, self._min_break_seconds - self._fallback_elapsed_seconds)
            if self._fallback_elapsed_seconds >= self._min_break_seconds:
                self._mark_break_satisfied()
                return
            self._idle_label.setText(f"休憩判定まで：あと {remaining} 秒")
            return

        self._idle_tracker.update()
        idle_seconds = self._idle_tracker.get_idle_seconds()
        if idle_seconds is None:
            self._fallback_elapsed_seconds += 1
            remaining = max(0, self._min_break_seconds - self._fallback_elapsed_seconds)
            if self._fallback_elapsed_seconds >= self._min_break_seconds:
                self._mark_break_satisfied()
                return
            self._idle_label.setText(f"休憩判定まで：あと {remaining} 秒")
            return

        idle_int = max(0, int(idle_seconds))
        remaining = max(0, self._min_break_seconds - idle_int)
        if idle_int >= self._min_break_seconds:
            self._mark_break_satisfied()
            return
        self._idle_label.setText(f"休憩判定まで：あと {remaining} 秒")

    def is_break_satisfied(self) -> bool:
        """Return whether this break has already satisfied the requirement."""
        return self._break_satisfied

    def _decide(self, action: str, memo: str | None = None) -> None:
        """Notify decision and hide dialog."""
        work_minutes = None
        if action == self.ACTION_BREAK_DONE and self._duration_spin is not None:
            work_minutes = int(self._duration_spin.value())
        self._idle_timer.stop()
        self.hide()
        self._on_decision(action, memo, work_minutes)

    def _mark_break_satisfied(self) -> None:
        """Latch break-satisfied state and notify observer once."""
        if self._break_satisfied:
            return
        self._break_satisfied = True
        if self._idle_label is not None:
            self._idle_label.setText("")
        if self._break_done_button is not None:
            self._break_done_button.setEnabled(True)
        if self._was_already_idle:
            self._waiting_for_return_after_satisfied = True
            return
        self._idle_timer.stop()
        if self._on_break_satisfied is not None:
            self._on_break_satisfied()

    def _confirm_end_work(self) -> None:
        """Ask for confirmation before ending today's work."""
        confirmed, memo = self._confirm_dialog.ask()
        if confirmed:
            self._decide(self.ACTION_END_WORK, memo)
            return

    def _reset_work_duration(self) -> None:
        """Reset work duration input to settings default."""
        if self._duration_spin is None:
            return
        self._duration_spin.setValue(self._default_work_minutes)
        self._update_next_break_time(self._default_work_minutes)

    def _update_next_break_time(self, minutes: int) -> None:
        """Refresh next break time preview."""
        if self._next_break_label is None:
            return
        self._next_break_label.setText(f"次の休憩: {format_next_break_time(minutes)}")

    def _detect_already_idle(self) -> bool:
        """Return whether user was already idle when the break prompt opened."""
        if self._idle_tracker is None:
            return False
        idle_seconds = self._idle_tracker.get_system_idle_seconds()
        if idle_seconds is None:
            return False
        return idle_seconds >= self.ALREADY_IDLE_THRESHOLD_SECONDS

    def _has_user_returned(self) -> bool:
        """Return whether input was detected after an already-idle break satisfied."""
        if self._idle_tracker is None:
            return False
        self._idle_tracker.update()
        idle_seconds = self._idle_tracker.get_idle_seconds()
        return idle_seconds is not None and idle_seconds < 1

    def _place_on_cursor_screen(self) -> None:
        """Place dialog near center of the screen where cursor is located."""
        screen = get_screen_at_cursor()
        if screen is None:
            return
        target_rect = screen.geometry()
        self.adjustSize()
        x = target_rect.x() + (target_rect.width() - self.width()) // 2
        y = target_rect.y() + (target_rect.height() - self.height()) // 2
        self.move(x, y)
