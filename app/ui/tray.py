"""System tray controller MVP implementation."""

from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QStyle, QSystemTrayIcon

from app.config import AppConfig, load_config
from app.core.timer_controller import TimerController
from app.effects.effect_manager import EffectManager
from app.infra.hotkey import GlobalHotkeyManager
from app.infra.idle_tracker import IdleTracker
from app.infra.logger import SQLiteLogger
from app.infra.ntfy_notifier import NtfyNotifier
from app.infra.startup import apply_startup_setting
from app.state import AppState
from app.ui.break_dialog import BreakDialog, EndWorkConfirmDialog
from app.ui.log_viewer import LogViewerDialog
from app.ui.settings_dialog import SettingsDialog
from app.ui.status_popup import StatusPopup


class TrayController:
    """Manage tray icon, timer flow, and tray menu actions."""

    def __init__(self, app: QApplication) -> None:
        self._app = app
        self._config: AppConfig = load_config()
        self._is_break_dialog_open = False
        self._logger = self._create_logger()
        self._notifier = self._create_notifier()
        self._idle_tracker = IdleTracker()
        self._hotkey_manager = GlobalHotkeyManager(self._app, self._on_hotkey_start_work)
        self._effect_manager = EffectManager(
            enabled=self._config.effects_enabled,
            effect_image_path=self._config.effect_image_path,
        )
        self._log_viewer: LogViewerDialog | None = None

        self._timer_controller = TimerController(
            work_minutes=self._config.work_minutes,
            on_work_timer_elapsed=self._on_work_timer_elapsed,
            logger=self._logger,
            notifier=self._notifier,
        )
        self._status_popup = StatusPopup(
            state_provider=lambda: self._timer_controller.state,
            remaining_provider=self._timer_controller.get_remaining_seconds,
        )
        self._break_dialog = BreakDialog(
            on_decision=self._on_break_decision,
            break_normal_message=self._config.messages["break_normal"],
            break_too_short_message=self._config.messages["break_too_short"],
            end_confirm_message=self._config.messages["end_confirm"],
            min_break_seconds=self._config.min_break_seconds,
            idle_tracker=self._idle_tracker,
            on_break_satisfied=self._on_break_satisfied,
        )
        self._stop_confirm_dialog = EndWorkConfirmDialog(
            end_confirm_message=self._config.messages["end_confirm"],
        )

        self._tray_icon = QSystemTrayIcon(self._build_icon(), app)
        self._menu = QMenu()

        self._start_or_resume_action = QAction("作業開始", self._menu)
        self._stop_action = QAction("作業停止", self._menu)
        self._status_action = QAction("状態表示", self._menu)
        self._show_logs_action = QAction("ログを表示", self._menu)
        self._settings_action = QAction("設定", self._menu)
        self._quit_action = QAction("終了", self._menu)

    def setup(self) -> None:
        """Create tray menu and display tray icon."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(None, "エラー", "システムトレイが利用できません。")
            self._app.quit()
            return

        self._start_or_resume_action.triggered.connect(
            lambda checked=False: self._handle_start_or_resume(checked)
        )
        self._stop_action.triggered.connect(lambda checked=False: self.stop_work(checked))
        self._status_action.triggered.connect(lambda checked=False: self.show_status(checked))
        self._settings_action.triggered.connect(lambda checked=False: self.show_settings(checked))
        self._show_logs_action.triggered.connect(lambda checked=False: self.show_logs(checked))
        self._quit_action.triggered.connect(lambda checked=False: self.quit_app(checked))

        self._menu.addAction(self._start_or_resume_action)
        self._menu.addAction(self._stop_action)
        self._menu.addSeparator()
        self._menu.addAction(self._status_action)
        self._menu.addAction(self._settings_action)
        self._menu.addAction(self._show_logs_action)
        self._menu.addSeparator()
        self._menu.addAction(self._quit_action)

        self._tray_icon.setContextMenu(self._menu)
        self._tray_icon.setToolTip("Break Reminder")
        self._tray_icon.show()
        self._apply_windows_startup(notify=False)
        self._apply_hotkey_settings(notify=False)
        self._update_action_state()

    def start_work(self, checked: bool = False) -> None:
        """Start work timer via TimerController."""
        try:
            _ = checked
            self._break_dialog.hide()
            self._effect_manager.hide_break_effect()
            self._is_break_dialog_open = False
            self._timer_controller.start_work()
            self._update_action_state()
        except Exception:
            traceback.print_exc()

    def stop_work(self, checked: bool = False) -> None:
        """Ask confirmation and stop work timer when confirmed."""
        try:
            _ = checked
            confirmed, memo = self._stop_confirm_dialog.ask()
            if not confirmed:
                return

            end_reason = memo if memo else "stopped"
            self._break_dialog.hide()
            self._effect_manager.hide_break_effect()
            self._is_break_dialog_open = False
            self._timer_controller.stop_work(end_reason=end_reason)
            self._update_action_state()
        except Exception:
            traceback.print_exc()

    def resume_work(self, checked: bool = False) -> None:
        """Resume work timer from break state."""
        try:
            _ = checked
            self._break_dialog.hide()
            self._effect_manager.hide_break_effect()
            self._is_break_dialog_open = False
            self._timer_controller.resume_work()
            self._update_action_state()
        except Exception:
            traceback.print_exc()

    def show_status(self, checked: bool = False) -> None:
        """Show realtime status dialog."""
        try:
            _ = checked
            self._status_popup.show_dialog()
        except Exception:
            traceback.print_exc()

    def show_logs(self, checked: bool = False) -> None:
        """Open app-internal log viewer dialog."""
        try:
            _ = checked
            if self._logger is None:
                QMessageBox.warning(None, "エラー", "ログ機能を初期化できませんでした。")
                return
            if self._log_viewer is None:
                self._log_viewer = LogViewerDialog(self._logger)
            self._log_viewer.refresh()
            self._log_viewer.show()
            self._log_viewer.raise_()
            self._log_viewer.activateWindow()
        except Exception:
            traceback.print_exc()

    def show_settings(self, checked: bool = False) -> None:
        """Open settings dialog and apply saved values."""
        try:
            _ = checked
            dialog = SettingsDialog()
            if dialog.exec() != SettingsDialog.DialogCode.Accepted:
                return
            saved = dialog.saved_config
            if saved is None:
                return

            self._config = saved
            self._notifier = self._create_notifier()
            self._timer_controller.update_settings(
                work_minutes=self._config.work_minutes,
                notifier=self._notifier,
            )
            self._break_dialog = BreakDialog(
                on_decision=self._on_break_decision,
                break_normal_message=self._config.messages["break_normal"],
                break_too_short_message=self._config.messages["break_too_short"],
                end_confirm_message=self._config.messages["end_confirm"],
                min_break_seconds=self._config.min_break_seconds,
                idle_tracker=self._idle_tracker,
                on_break_satisfied=self._on_break_satisfied,
            )
            self._effect_manager.update_settings(
                enabled=self._config.effects_enabled,
                effect_image_path=self._config.effect_image_path,
            )
            self._apply_windows_startup(notify=True)
            self._apply_hotkey_settings(notify=True)
            self._stop_confirm_dialog = EndWorkConfirmDialog(
                end_confirm_message=self._config.messages["end_confirm"],
            )

            if self._timer_controller.state == AppState.WORKING:
                QMessageBox.information(
                    None,
                    "設定を保存しました",
                    "作業中のため、新しい設定は次回タイマー開始から反映されます。",
                )
        except Exception:
            traceback.print_exc()

    def quit_app(self, checked: bool = False) -> None:
        """Quit the application explicitly from tray menu."""
        try:
            _ = checked
            self._break_dialog.hide()
            self._effect_manager.hide_break_effect()
            self._hotkey_manager.shutdown()
            self._tray_icon.hide()
            self._app.quit()
        except Exception:
            traceback.print_exc()

    def _handle_start_or_resume(self, checked: bool = False) -> None:
        """Handle context-aware action: start from STOPPED or resume from BREAKING."""
        if self._is_break_dialog_open:
            return
        state = self._timer_controller.state
        if state == AppState.BREAKING:
            self.resume_work(checked)
        elif state == AppState.STOPPED:
            self.start_work(checked)

    def _on_work_timer_elapsed(self) -> None:
        """Show break dialog when work timer reaches timeout."""
        try:
            self._is_break_dialog_open = True
            self._update_action_state()
            self._effect_manager.update_settings(
                enabled=self._config.effects_enabled,
                effect_image_path=self._config.effect_image_path,
            )
            self._effect_manager.show_break_effect(effect_image_path=self._config.effect_image_path)
            self._break_dialog.open_prompt(BreakDialog.MESSAGE_NORMAL)
        except Exception:
            traceback.print_exc()

    def _on_break_decision(self, action: str, memo: str | None = None) -> None:
        """Apply user decision from break dialog."""
        try:
            self._is_break_dialog_open = False
            self._effect_manager.hide_break_effect()
            if action == BreakDialog.ACTION_BREAK_DONE:
                self._timer_controller.resume_work()
            elif action == BreakDialog.ACTION_END_WORK:
                end_reason = memo if memo else "user_ended"
                self._timer_controller.stop_work(end_reason=end_reason)
            self._update_action_state()
        except Exception:
            traceback.print_exc()

    def _on_break_satisfied(self) -> None:
        """Hide overlay once break requirement is satisfied."""
        self._effect_manager.hide_break_effect()

    def _on_hotkey_start_work(self) -> None:
        """Start work via global hotkey only from STOPPED state."""
        try:
            if self._timer_controller.state != AppState.STOPPED:
                return
            self.start_work()
        except Exception:
            traceback.print_exc()

    def _update_action_state(self) -> None:
        """Update menu labels and enabled states according to app state."""
        state = self._timer_controller.state

        if state == AppState.BREAKING:
            self._start_or_resume_action.setText("作業再開")
            self._start_or_resume_action.setEnabled(not self._is_break_dialog_open)
        else:
            self._start_or_resume_action.setText("作業開始")
            self._start_or_resume_action.setEnabled(state == AppState.STOPPED)

        self._stop_action.setEnabled(state in (AppState.WORKING, AppState.NOTIFYING, AppState.BREAKING))

    def _build_icon(self) -> QIcon:
        """Use a standard Qt icon to guarantee tray visibility in MVP."""
        style = self._app.style()
        return style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)

    def _create_logger(self) -> SQLiteLogger | None:
        """Create SQLite logger. Return None when initialization fails."""
        try:
            return SQLiteLogger()
        except Exception:
            traceback.print_exc()
            return None

    def _create_notifier(self) -> NtfyNotifier:
        """Create ntfy notifier from app config."""
        return NtfyNotifier(
            enabled=self._config.ntfy_enabled,
            topic=self._config.ntfy_topic,
            message=self._config.messages["break_normal"],
        )

    def _apply_windows_startup(self, notify: bool) -> None:
        """Apply startup shortcut setting for current config."""
        ok = apply_startup_setting(
            enabled=self._config.start_with_windows,
            app_root=Path(__file__).resolve().parents[2],
        )
        if notify and not ok:
            QMessageBox.warning(
                None,
                "自動起動設定エラー",
                "Windows起動時の自動起動設定に失敗しました。",
            )

    def _apply_hotkey_settings(self, notify: bool) -> None:
        """Apply global hotkey setting for current config."""
        ok = self._hotkey_manager.apply_settings(
            enabled=self._config.hotkey_enabled,
            hotkey_text=self._config.hotkey_start_work,
        )
        if notify and not ok and self._config.hotkey_enabled:
            QMessageBox.warning(
                None,
                "ホットキー設定エラー",
                "作業開始ショートカットの登録に失敗しました。",
            )
