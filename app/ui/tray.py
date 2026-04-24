"""System tray controller MVP implementation."""

from __future__ import annotations

import traceback

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QStyle, QSystemTrayIcon

from app.state import AppState
from app.ui.status_popup import StatusPopup


class TrayController:
    """Manage tray icon, state transitions, and tray menu actions."""

    def __init__(self, app: QApplication) -> None:
        self._app = app
        self._state = AppState.STOPPED
        self._status_popup = StatusPopup()

        self._tray_icon = QSystemTrayIcon(self._build_icon(), app)
        self._menu = QMenu()

        self._start_action = QAction("作業開始", self._menu)
        self._stop_action = QAction("作業停止", self._menu)
        self._status_action = QAction("状態表示", self._menu)
        self._quit_action = QAction("終了", self._menu)

    def setup(self) -> None:
        """Create tray menu and display tray icon."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(None, "エラー", "システムトレイが利用できません。")
            self._app.quit()
            return

        self._start_action.triggered.connect(lambda checked=False: self.start_work(checked))
        self._stop_action.triggered.connect(lambda checked=False: self.stop_work(checked))
        self._status_action.triggered.connect(lambda checked=False: self.show_status(checked))
        self._quit_action.triggered.connect(lambda checked=False: self.quit_app(checked))

        self._menu.addAction(self._start_action)
        self._menu.addAction(self._stop_action)
        self._menu.addSeparator()
        self._menu.addAction(self._status_action)
        self._menu.addSeparator()
        self._menu.addAction(self._quit_action)

        self._tray_icon.setContextMenu(self._menu)
        self._tray_icon.setToolTip("Break Reminder")
        self._tray_icon.show()
        self._update_action_state()

    def start_work(self, checked: bool = False) -> None:
        """Move to WORKING state for MVP start action."""
        try:
            _ = checked
            self._state = AppState.WORKING
            self._update_action_state()
        except Exception:
            traceback.print_exc()

    def stop_work(self, checked: bool = False) -> None:
        """Move back to STOPPED state for MVP stop action."""
        try:
            _ = checked
            self._state = AppState.STOPPED
            self._update_action_state()
        except Exception:
            traceback.print_exc()

    def show_status(self, checked: bool = False) -> None:
        """Show current app state in a minimal popup."""
        try:
            _ = checked
            self._status_popup.show_state(self._state)
        except Exception:
            traceback.print_exc()

    def quit_app(self, checked: bool = False) -> None:
        """Quit the application explicitly from tray menu."""
        try:
            _ = checked
            self._tray_icon.hide()
            self._app.quit()
        except Exception:
            traceback.print_exc()

    def _update_action_state(self) -> None:
        """Toggle start/stop action availability based on current state."""
        is_stopped = self._state == AppState.STOPPED
        self._start_action.setEnabled(is_stopped)
        self._stop_action.setEnabled(not is_stopped)

    def _build_icon(self) -> QIcon:
        """Use a standard Qt icon to guarantee tray visibility in MVP."""
        style = self._app.style()
        return style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
