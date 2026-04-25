"""Status popup MVP implementation."""

from __future__ import annotations

from app.state import AppState

from PySide6.QtWidgets import QMessageBox


class StatusPopup:
    """Display lightweight status message dialogs."""

    def show_state(self, state: AppState, remaining_seconds: int | None = None) -> None:
        """Show current state and optional remaining time."""
        state_labels = {
            AppState.STOPPED: "停止中",
            AppState.WORKING: "作業中",
            AppState.NOTIFYING: "通知中",
            AppState.BREAKING: "休憩中",
        }
        message = f"現在状態: {state_labels.get(state, state.name)}"
        if remaining_seconds is not None:
            minutes, seconds = divmod(remaining_seconds, 60)
            message += f"\n残り時間: {minutes:02d}:{seconds:02d}"
        QMessageBox.information(None, "現在の状態", message)
