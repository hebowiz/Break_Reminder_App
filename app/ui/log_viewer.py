"""Simple log viewer dialog for SQLite work session history."""

from __future__ import annotations

import traceback
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.infra.logger import SQLiteLogger


class LogViewerDialog(QDialog):
    """Read-only table dialog for recent work sessions."""

    def __init__(self, logger: SQLiteLogger, parent: QDialog | None = None) -> None:
        super().__init__(parent)
        self._logger = logger
        self._table = QTableWidget(self)
        self._setup_ui()
        self.refresh()

    def refresh(self) -> None:
        """Reload latest sessions from SQLite."""
        try:
            rows = self._logger.get_recent_sessions(limit=100)
            self._table.setRowCount(len(rows))
            for row_index, row in enumerate(rows):
                self._set_cell(row_index, 0, str(row.get("id", "")))
                self._set_cell(row_index, 1, self._format_datetime(row.get("work_started_at")))
                self._set_cell(row_index, 2, self._format_datetime(row.get("timer_fired_at")))
                self._set_cell(row_index, 3, self._format_datetime(row.get("work_resumed_at")))
                self._set_cell(row_index, 4, self._format_datetime(row.get("work_ended_at")))
                self._set_cell(row_index, 5, self._map_end_reason(row.get("end_reason")))
            self._table.resizeColumnsToContents()
        except Exception:
            traceback.print_exc()
            QMessageBox.warning(self, "エラー", "ログの読み込みに失敗しました。")

    def _setup_ui(self) -> None:
        """Build viewer layout and controls."""
        self.setWindowTitle("作業ログ")
        self.resize(820, 420)

        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["ID", "作業開始", "通知", "再開", "終了", "終了理由"]
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        refresh_button = QPushButton("更新", self)
        close_button = QPushButton("閉じる", self)
        refresh_button.setAutoDefault(False)
        refresh_button.setDefault(False)
        close_button.setAutoDefault(False)
        close_button.setDefault(False)

        refresh_button.clicked.connect(self.refresh)
        close_button.clicked.connect(self.close)

        button_layout = QHBoxLayout()
        button_layout.addWidget(refresh_button)
        button_layout.addStretch(1)
        button_layout.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._table)
        layout.addLayout(button_layout)

    def _set_cell(self, row: int, column: int, value: str) -> None:
        """Set a read-only table cell value."""
        self._table.setItem(row, column, QTableWidgetItem(value))

    @staticmethod
    def _to_text(value: object) -> str:
        """Normalize nullable values for display."""
        if value is None:
            return ""
        return str(value)

    @classmethod
    def _format_datetime(cls, value: object) -> str:
        """Format ISO8601 datetime text for readability in the table."""
        text = cls._to_text(value)
        if not text:
            return ""
        try:
            parsed = datetime.fromisoformat(text)
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return text

    @staticmethod
    def _map_end_reason(value: object) -> str:
        """Map known end reasons to user-facing labels."""
        text = "" if value is None else str(value)
        if text == "user_ended":
            return "今日は終了"
        if text == "stopped":
            return "作業停止"
        return text
