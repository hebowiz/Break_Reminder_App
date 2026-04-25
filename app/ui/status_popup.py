"""Realtime status dialog for MVP."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from app.state import AppState


class StatusPopup(QDialog):
    """Show current app state with realtime updates."""

    def __init__(
        self,
        state_provider: Callable[[], AppState],
        remaining_provider: Callable[[], int | None],
        parent: QDialog | None = None,
    ) -> None:
        super().__init__(parent)
        self._state_provider = state_provider
        self._remaining_provider = remaining_provider

        self._update_timer = QTimer(self)
        self._update_timer.setInterval(1000)
        self._update_timer.timeout.connect(self._refresh)

        self._state_label = QLabel(self)
        self._remaining_label = QLabel(self)

        self._setup_ui()

    def show_dialog(self) -> None:
        """Open and start realtime update loop."""
        self._refresh()
        self.show()
        self.raise_()
        self.activateWindow()
        if not self._update_timer.isActive():
            self._update_timer.start()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Stop periodic updates when dialog is closed."""
        self._update_timer.stop()
        super().closeEvent(event)

    def _setup_ui(self) -> None:
        """Build status dialog UI."""
        self.setWindowTitle("現在の状態")
        self.setMinimumWidth(280)

        close_button = QPushButton("閉じる", self)
        close_button.setAutoDefault(False)
        close_button.setDefault(False)
        close_button.clicked.connect(self.close)

        layout = QVBoxLayout(self)
        layout.addWidget(self._state_label)
        layout.addWidget(self._remaining_label)
        layout.addWidget(close_button)

    def _refresh(self) -> None:
        """Refresh labels from current app state."""
        state = self._state_provider()
        remaining = self._remaining_provider()

        state_labels = {
            AppState.STOPPED: "停止中",
            AppState.WORKING: "作業中",
            AppState.NOTIFYING: "通知中",
            AppState.BREAKING: "休憩中",
        }
        state_text = state_labels.get(state, state.name)
        self._state_label.setText(f"状態：{state_text}")

        if state == AppState.WORKING and remaining is not None:
            minutes, seconds = divmod(max(0, remaining), 60)
            self._remaining_label.setText(f"残り時間：{minutes:02d}:{seconds:02d}")
            return

        if state == AppState.BREAKING:
            self._remaining_label.setText("休憩中です。ダイアログで操作してください。")
            return

        if state == AppState.NOTIFYING:
            self._remaining_label.setText("休憩通知を表示しています。")
            return

        self._remaining_label.setText("")
