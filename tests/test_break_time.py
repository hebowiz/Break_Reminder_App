"""Clock scheduling and Qt flow regressions, without real notifications or log writes."""

from __future__ import annotations

import os
import unittest
from datetime import datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTime, QTimer
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QTimeEdit

from app.core.time_utils import remaining_minutes, resolve_next_break_datetime
from app.core.timer_controller import TimerController
from app.state import AppState
from app.ui.break_dialog import BreakDialog, WorkDurationDialog
from app.ui.break_time_input import BreakTimeInput
from app.ui.status_widget import StatusWidget
from app.ui.tray import TrayController


class ClockTests(unittest.TestCase):
    def test_next_occurrence_and_rounding(self) -> None:
        cases = [
            (datetime(2026, 11, 8, 14), time(15), datetime(2026, 11, 8, 15), 60),
            (datetime(2026, 11, 8, 14, 35), time(15, 20), datetime(2026, 11, 8, 15, 20), 45),
            (datetime(2026, 11, 8, 14, 35, 59), time(15, 20), datetime(2026, 11, 8, 15, 20), 45),
            (datetime(2026, 12, 31, 23, 30), time(0, 30), datetime(2027, 1, 1, 0, 30), 60),
            (datetime(2026, 11, 8, 14), time(13), datetime(2026, 11, 9, 13), 1380),
            (datetime(2026, 11, 8, 14), time(14), datetime(2026, 11, 9, 14), 1440),
            (datetime(2026, 11, 8, 14, 0, 30), time(14), datetime(2026, 11, 9, 14), 1440),
        ]
        for now, selected, expected, minutes in cases:
            with self.subTest(now=now, selected=selected):
                target = resolve_next_break_datetime(selected, now)
                self.assertEqual(target, expected)
                self.assertEqual(remaining_minutes(target, now), minutes)

    def test_due_and_elapsed_targets_show_zero(self) -> None:
        now = datetime(2026, 11, 8, 15)
        self.assertEqual(remaining_minutes(now, now), 0)
        self.assertEqual(remaining_minutes(now - timedelta(seconds=1), now), 0)
        self.assertEqual(remaining_minutes(now + timedelta(microseconds=1), now), 1)


class SchedulingFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.now = datetime(2026, 11, 8, 14, 35, 30)
        for module in (
            "app.core.time_utils", "app.core.timer_controller", "app.ui.break_time_input"
        ):
            clock = self.enterContext(patch(f"{module}.datetime", wraps=datetime))
            clock.now.side_effect = lambda: self.now

    def keep_widget(self, widget):
        self.addCleanup(widget.deleteLater)
        self.addCleanup(widget.hide)
        return widget

    def make_break_dialog(self, callback=None) -> BreakDialog:
        return self.keep_widget(BreakDialog(
            on_decision=callback or Mock(),
            break_normal_message="休憩時間です。",
            break_too_short_message="もう少し休憩してください。",
            end_confirm_message="終了しますか？",
            default_work_minutes=45,
            min_break_seconds=30,
        ))

    def test_input_defaults_editing_and_elapsed_preview(self) -> None:
        widget = self.keep_widget(BreakTimeInput())
        widget.reset(45)
        self.assertIsInstance(widget.time_edit, QTimeEdit)
        self.assertEqual(widget.time_edit.displayFormat(), "HH:mm")
        self.assertEqual(widget.time_edit.time(), QTime(15, 20))
        self.assertEqual(widget.remaining_label.text(), "休憩まで: 45分後")
        widget.time_edit.setTime(QTime(15, 30))
        self.assertEqual(widget.remaining_label.text(), "休憩まで: 55分後")
        widget.show()
        self.assertTrue(widget._refresh_timer.isActive())
        self.now += timedelta(minutes=10)
        widget._refresh_timer.timeout.emit()
        self.assertEqual(widget.remaining_label.text(), "休憩まで: 45分後")
        widget.hide()
        self.assertFalse(widget._refresh_timer.isActive())

    def test_start_dialog_confirmation_and_fresh_defaults(self) -> None:
        dialog = self.keep_widget(WorkDurationDialog())
        buttons = dialog.findChild(QDialogButtonBox)

        def confirm() -> None:
            dialog._break_time_input.time_edit.setTime(QTime(0, 30))
            buttons.button(QDialogButtonBox.StandardButton.Ok).click()

        QTimer.singleShot(0, confirm)
        accepted, target = dialog.ask(45)
        self.assertTrue(accepted)
        self.assertEqual(target, datetime(2026, 11, 9, 0, 30))
        self.now += timedelta(hours=1)
        QTimer.singleShot(0, buttons.button(QDialogButtonBox.StandardButton.Ok).click)
        self.assertEqual(dialog.ask(45), (True, datetime(2026, 11, 8, 16, 20)))
        QTimer.singleShot(0, buttons.button(QDialogButtonBox.StandardButton.Cancel).click)
        self.assertEqual(dialog.ask(45), (False, None))

    def test_break_dialog_resumes_with_date_and_keeps_idle_gate(self) -> None:
        callback = Mock()
        dialog = self.make_break_dialog(callback)
        self.now = datetime(2026, 11, 8, 23, 30)
        dialog.open_prompt()
        self.assertEqual(dialog._break_time_input.time_edit.time(), QTime(0, 15))
        self.assertFalse(dialog._break_done_button.isEnabled())
        dialog._break_done_button.click()
        callback.assert_not_called()
        dialog._mark_break_satisfied()
        self.assertTrue(dialog._break_time_input._refresh_timer.isActive())
        dialog._break_time_input.time_edit.setTime(QTime(0, 30))
        self.assertEqual(dialog._break_time_input.remaining_label.text(), "休憩まで: 60分後")
        dialog._break_done_button.click()
        callback.assert_called_once_with("break_done", None, datetime(2026, 11, 9, 0, 30))
        self.assertFalse(dialog._break_time_input._refresh_timer.isActive())
        self.now = datetime(2026, 11, 9, 1)
        dialog.open_prompt()
        self.assertEqual(dialog._break_time_input.time_edit.time(), QTime(1, 45))

    def test_unconfirmed_time_rolls_forward_but_confirmation_keeps_date(self) -> None:
        widget = self.keep_widget(BreakTimeInput())
        widget.time_edit.setTime(QTime(15, 20))
        self.now = datetime(2026, 11, 8, 15, 20)
        widget.refresh()
        self.assertEqual(widget.remaining_label.text(), "休憩まで: 1440分後")
        self.assertEqual(widget.selected_datetime(), datetime(2026, 11, 9, 15, 20))

    def test_timer_arrival_and_sleep_jump_fire_once(self) -> None:
        target = datetime(2026, 11, 9, 0, 30)
        for wake_time in (target, target + timedelta(days=1, hours=2)):
            with self.subTest(wake_time=wake_time):
                logger, notifier, elapsed = Mock(), Mock(), Mock()
                controller = TimerController(45, elapsed, logger, notifier)
                self.addCleanup(controller._work_timer.stop)
                self.now = target - timedelta(seconds=1)
                controller.start_work(target)
                self.assertEqual(controller.next_break_datetime, target)
                self.assertEqual(controller.get_remaining_seconds(), 1)
                controller._handle_work_timer_elapsed()
                elapsed.assert_not_called()
                self.now = wake_time
                controller._handle_work_timer_elapsed()
                controller._handle_work_timer_elapsed()
                self.assertEqual(controller.state, AppState.BREAKING)
                elapsed.assert_called_once_with()
                notifier.send_break_notification.assert_called_once_with()
                logger.mark_timer_fired.assert_called_once_with(logger.create_session.return_value)
                next_target = wake_time + timedelta(minutes=10)
                controller.resume_work(next_target)
                self.assertEqual(controller.next_break_datetime, next_target)
                logger.mark_work_resumed.assert_called_once_with(logger.create_session.return_value)
                self.assertEqual(controller._work_minutes, 45)

    def test_confirmed_target_is_not_shifted_if_already_due_when_started(self) -> None:
        elapsed = Mock()
        controller = TimerController(45, elapsed)
        self.addCleanup(controller._work_timer.stop)
        target = self.now - timedelta(seconds=1)
        controller.start_work(target)
        self.assertEqual(controller.next_break_datetime, target)
        controller._handle_work_timer_elapsed()
        elapsed.assert_called_once_with()

    def test_tray_start_resume_and_cancel_forward_datetime_without_saving_settings(self) -> None:
        target = datetime(2026, 11, 9, 0, 30)
        for method in ("start_work", "resume_work"):
            for accepted in (False, True):
                with self.subTest(method=method, accepted=accepted):
                    tray = Mock()
                    tray._config = SimpleNamespace(work_minutes=45)
                    tray._work_duration_dialog.ask.return_value = (accepted, target if accepted else None)
                    getattr(TrayController, method)(tray)
                    tray._work_duration_dialog.ask.assert_called_once_with(45)
                    action = getattr(tray._timer_controller, method)
                    if accepted:
                        action.assert_called_once_with(target)
                        tray._show_work_started_notification.assert_called_once_with()
                    else:
                        action.assert_not_called()
                        tray._show_work_started_notification.assert_not_called()
                    self.assertEqual(tray._config.work_minutes, 45)
        tray = Mock()
        TrayController._on_break_decision(tray, BreakDialog.ACTION_BREAK_DONE, None, target)
        tray._timer_controller.resume_work.assert_called_once_with(target)

    def test_notification_and_widget_use_confirmed_datetime(self) -> None:
        controller = TimerController(25)
        self.addCleanup(controller._work_timer.stop)
        target = datetime(2026, 11, 8, 15, 20)
        controller.start_work(target)
        tray = SimpleNamespace(_timer_controller=controller, _tray_icon=Mock())
        widget = self.keep_widget(StatusWidget(lambda: controller.state, lambda: controller.next_break_datetime, True))
        self.addCleanup(widget._update_timer.stop)
        for minutes in (45, 35):
            TrayController._show_work_started_notification(tray)
            self.assertEqual(tray._tray_icon.showMessage.call_args.args[:2],
                             ("作業開始", f"次の休憩: {minutes}分後 (15:20)"))
            widget.refresh()
            self.assertEqual(widget._time_label.text(), f"15:20 ({minutes}分後)")
            self.now += timedelta(minutes=10)


if __name__ == "__main__":
    unittest.main()
