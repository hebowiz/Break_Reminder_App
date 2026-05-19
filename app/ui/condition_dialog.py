"""Condition self-check input dialog."""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSlider,
    QVBoxLayout,
    QWidget,
)


SYMPTOM_ITEMS = [
    "IBS",
    "眠気",
    "倦怠感",
    "疲れやすい",
    "頭痛",
    "動悸",
    "下痢",
    "火照り",
    "目眩",
    "鼻炎",
    "目のかすみ",
    "発熱",
    "悪寒",
    "思考乱れ",
    "その他",
]


@dataclass
class ConditionInput:
    """Structured condition input for future persistence/integration."""

    condition_score: int = 50
    mood_score: int = 50
    energy_score: int = 50
    symptoms: list[str] = field(default_factory=list)
    other_text: str = ""


class ConditionInputDialog(QDialog):
    """Collect lightweight condition, mood, energy, and symptom inputs."""

    def __init__(self, parent: QDialog | None = None) -> None:
        super().__init__(parent)
        self._sliders: dict[str, QSlider] = {}
        self._value_labels: dict[str, QLabel] = {}
        self._symptom_checks: dict[str, QCheckBox] = {}
        self._other_text: QLineEdit | None = None
        self._condition_input = ConditionInput()
        self._setup_ui()

    @property
    def condition_input(self) -> ConditionInput:
        """Return the latest accepted condition input."""
        return self._condition_input

    def _setup_ui(self) -> None:
        """Build condition input UI."""
        self.setWindowTitle("体調入力")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_score_row("condition_score", "体調"))
        layout.addWidget(self._build_score_row("mood_score", "気分"))
        layout.addWidget(self._build_score_row("energy_score", "余力"))
        layout.addWidget(self._build_symptoms_group())

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_score_row(self, key: str, label_text: str) -> QWidget:
        """Build one slider row with a realtime percentage label."""
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(label_text, self)
        label.setMinimumWidth(48)

        slider = QSlider(Qt.Orientation.Horizontal, self)
        slider.setRange(0, 100)
        slider.setSingleStep(10)
        slider.setPageStep(10)
        slider.setTickInterval(10)
        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        slider.setValue(50)

        value_label = QLabel("50%", self)
        value_label.setMinimumWidth(44)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        slider.valueChanged.connect(
            lambda value, slider_key=key: self._update_slider_value(slider_key, value)
        )

        self._sliders[key] = slider
        self._value_labels[key] = value_label

        layout.addWidget(label)
        layout.addWidget(slider, 1)
        layout.addWidget(value_label)
        return container

    def _build_symptoms_group(self) -> QGroupBox:
        """Build symptom checkboxes in a compact grid."""
        group = QGroupBox("不調項目", self)
        grid = QGridLayout(group)
        columns = 3
        row = 0
        column = 0

        for symptom in SYMPTOM_ITEMS:
            checkbox = QCheckBox(symptom, self)
            self._symptom_checks[symptom] = checkbox
            if symptom == "その他":
                if column >= columns - 1:
                    row += 1
                    column = 0
                checkbox.toggled.connect(self._set_other_enabled)
                grid.addWidget(checkbox, row, column)
                self._other_text = QLineEdit(self)
                self._other_text.setPlaceholderText("その他の内容")
                self._other_text.setEnabled(False)
                grid.addWidget(self._other_text, row, column + 1, 1, columns - column - 1)
                row += 1
                column = 0
                continue

            grid.addWidget(checkbox, row, column)
            column += 1
            if column >= columns:
                row += 1
                column = 0

        return group

    def _update_slider_value(self, key: str, value: int) -> None:
        """Snap slider values to 10% increments and update label."""
        slider = self._sliders[key]
        snapped_value = max(0, min(100, ((value + 5) // 10) * 10))
        if snapped_value != value:
            slider.setValue(snapped_value)
            return
        self._value_labels[key].setText(f"{snapped_value}%")

    def _set_other_enabled(self, checked: bool) -> None:
        """Enable free text only when 'その他' is selected."""
        if self._other_text is None:
            return
        self._other_text.setEnabled(checked)
        if not checked:
            self._other_text.clear()

    def _accept(self) -> None:
        """Collect input and accept the dialog."""
        symptoms = [
            symptom
            for symptom, checkbox in self._symptom_checks.items()
            if symptom != "その他" and checkbox.isChecked()
        ]
        other_text = ""
        other_checkbox = self._symptom_checks.get("その他")
        if other_checkbox is not None and other_checkbox.isChecked():
            if self._other_text is not None:
                other_text = self._other_text.text().strip()

        self._condition_input = ConditionInput(
            condition_score=int(self._sliders["condition_score"].value()),
            mood_score=int(self._sliders["mood_score"].value()),
            energy_score=int(self._sliders["energy_score"].value()),
            symptoms=symptoms,
            other_text=other_text,
        )
        self.accept()
