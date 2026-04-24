"""Status popup MVP implementation."""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from app.state import AppState


class StatusPopup:
    """Display lightweight status message dialogs."""

    def show_state(self, state: AppState) -> None:
        """Show the current state in a minimal QMessageBox."""
        QMessageBox.information(None, "現在の状態", f"現在状態: {state.name}")
