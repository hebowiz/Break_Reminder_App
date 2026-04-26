"""Break prompt dialog for MVP."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QCloseEvent, QHideEvent, QKeyEvent
from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout
from app.infra.idle_tracker import IdleTracker
from app.ui.screen_utils import get_screen_at_cursor


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

    ACTION_BREAK_DONE = "break_done"
    ACTION_END_WORK = "end_work"

    MESSAGE_NORMAL = "normal"
    MESSAGE_TOO_SHORT = "too_short"

    def __init__(
        self,
        on_decision: Callable[[str, str | None], None],
        break_normal_message: str,
        break_too_short_message: str,
        end_confirm_message: str,
        min_break_seconds: int,
        idle_tracker: IdleTracker | None = None,
        on_break_satisfied: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(None)
        self._on_decision = on_decision
        self._on_break_satisfied = on_break_satisfied
        self._break_normal_message = break_normal_message
        self._break_too_short_message = break_too_short_message
        self._min_break_seconds = max(1, int(min_break_seconds))
        self._idle_tracker = idle_tracker
        self._message_label: QLabel | None = None
        self._idle_label: QLabel | None = None
        self._break_done_button: QPushButton | None = None
        self._break_satisfied = False
        self._fallback_elapsed_seconds = 0

        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(1000)
        self._idle_timer.timeout.connect(self._refresh_idle_info)

        self._confirm_dialog = EndWorkConfirmDialog(end_confirm_message, self)
        self._setup_ui()

    def open_prompt(self, message_kind: str = MESSAGE_NORMAL) -> None:
        """Open the dialog in non-modal mode and keep it on top."""
        self._apply_message(message_kind)
        self._break_satisfied = False
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

        break_done_button = QPushButton("休憩完了", self)
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
            self._idle_label.setText("休憩OKです。作業を再開できます。")
            if self._break_done_button is not None:
                self._break_done_button.setEnabled(True)
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
        self._idle_timer.stop()
        self.hide()
        self._on_decision(action, memo)

    def _mark_break_satisfied(self) -> None:
        """Latch break-satisfied state and notify observer once."""
        if self._break_satisfied:
            return
        self._break_satisfied = True
        self._idle_timer.stop()
        if self._idle_label is not None:
            self._idle_label.setText("休憩OKです。作業を再開できます。")
        if self._break_done_button is not None:
            self._break_done_button.setEnabled(True)
        if self._on_break_satisfied is not None:
            self._on_break_satisfied()

    def _confirm_end_work(self) -> None:
        """Ask for confirmation before ending today's work."""
        confirmed, memo = self._confirm_dialog.ask()
        if confirmed:
            self._decide(self.ACTION_END_WORK, memo)
            return

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
