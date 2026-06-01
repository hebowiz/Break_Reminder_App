"""Read-only viewer for condition JSONL logs."""

from __future__ import annotations

import traceback
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.infra.condition_logger import (
    ConditionLogRecord,
    get_record_symptoms,
    load_condition_logs,
)


class ConditionLogViewerDialog(QDialog):
    """Display condition logs in a read-only table."""

    def __init__(self, parent: QDialog | None = None) -> None:
        super().__init__(parent)
        self._table = QTableWidget(self)
        self._empty_label = QLabel("ログがありません", self)
        self._setup_ui()
        self.refresh()

    def refresh(self) -> None:
        """Reload condition logs from JSONL."""
        try:
            records = load_condition_logs()
            self._empty_label.setVisible(not records)
            self._table.setRowCount(len(records))
            for row_index, record in enumerate(records):
                self._set_cell(row_index, 0, self._format_datetime(record.get("timestamp")))
                self._set_cell(row_index, 1, self._to_text(record.get("condition")))
                self._set_cell(row_index, 2, self._to_text(record.get("mood")))
                self._set_cell(row_index, 3, self._to_text(record.get("energy")))
                self._set_cell(row_index, 4, self._format_symptoms(record))
                self._set_cell(row_index, 5, self._to_text(record.get("comment")))
            self._table.resizeColumnsToContents()
        except Exception:
            traceback.print_exc()
            QMessageBox.warning(self, "エラー", "体調ログの読み込みに失敗しました。")

    def _setup_ui(self) -> None:
        """Build viewer layout and controls."""
        self.setWindowTitle("体調ログ")
        self.resize(860, 420)

        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["日時", "体調", "気分", "余力", "不調項目", "コメント"]
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
        layout.addWidget(self._empty_label)
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
        """Format ISO8601 datetime text for readability."""
        text = cls._to_text(value)
        if not text:
            return ""
        try:
            parsed = datetime.fromisoformat(text)
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return text

    @classmethod
    def _format_symptoms(cls, record: ConditionLogRecord) -> str:
        """Format normalized symptoms as comma-separated text."""
        symptoms = get_record_symptoms(record)
        return ", ".join(cls._to_text(symptom) for symptom in symptoms)
