"""Settings dialog for editing config.json safely."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.config import AppConfig, load_config, save_config


class SettingsDialog(QDialog):
    """Dialog for editing runtime settings with type-safe widgets."""

    def __init__(self, parent: QDialog | None = None) -> None:
        super().__init__(parent)
        self._saved_config: AppConfig | None = None
        self._current_config: AppConfig = load_config()
        self._setup_ui()
        self._load_values(self._current_config)

    @property
    def saved_config(self) -> AppConfig | None:
        """Return config saved by this dialog invocation."""
        return self._saved_config

    def _setup_ui(self) -> None:
        """Build settings form and action buttons."""
        self.setWindowTitle("設定")
        self.setMinimumWidth(420)

        self._work_minutes = QSpinBox(self)
        self._work_minutes.setRange(1, 240)
        self._work_minutes.setSingleStep(1)
        self._work_minutes.setSuffix(" 分")

        self._min_break_seconds = QSpinBox(self)
        self._min_break_seconds.setRange(5, 3600)
        self._min_break_seconds.setSuffix(" 秒")

        self._ntfy_enabled = QCheckBox("ntfy 通知を有効化", self)
        self._ntfy_topic = QLineEdit(self)
        self._ntfy_topic.setPlaceholderText("例: my-break-topic")

        self._notification_level = QComboBox(self)
        self._notification_level.addItem("Level 1", 1)
        self._notification_level.addItem("Level 2", 2)
        self._notification_level.addItem("Level 3", 3)

        self._effects_enabled = QCheckBox("演出を有効化（未実装）", self)
        self._effects_enabled.setText("演出を有効化")

        self._effect_image_path = QLineEdit(self)
        self._effect_image_path.setPlaceholderText("画像ファイルを選択（任意）")
        browse_button = QPushButton("参照", self)
        browse_button.clicked.connect(self._browse_effect_image)

        image_path_layout = QHBoxLayout()
        image_path_layout.setContentsMargins(0, 0, 0, 0)
        image_path_layout.addWidget(self._effect_image_path)
        image_path_layout.addWidget(browse_button)
        image_path_container = QWidget(self)
        image_path_container.setLayout(image_path_layout)

        self._start_with_windows = QCheckBox("Windows起動時に自動起動", self)
        self._hotkey_enabled = QCheckBox("作業開始ショートカットを有効化", self)
        self._hotkey_start_work = QLineEdit(self)
        self._hotkey_start_work.setPlaceholderText("例: Ctrl+Alt+B")
        self._hotkey_enabled.toggled.connect(self._hotkey_start_work.setEnabled)

        form = QFormLayout()
        form.addRow("作業時間", self._work_minutes)
        form.addRow("最低休憩時間", self._min_break_seconds)
        form.addRow("ntfy", self._ntfy_enabled)
        form.addRow("ntfy topic", self._ntfy_topic)
        form.addRow("通知レベル", self._notification_level)
        form.addRow("演出", self._effects_enabled)
        form.addRow("演出画像", image_path_container)
        form.addRow("自動起動", self._start_with_windows)
        form.addRow("ショートカット", self._hotkey_enabled)
        form.addRow("開始ホットキー", self._hotkey_start_work)

        note = QLabel("保存後、作業中の場合は次回タイマー開始から反映されます。", self)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def _load_values(self, config: AppConfig) -> None:
        """Populate widgets from current config."""
        self._work_minutes.setValue(config.work_minutes)
        self._min_break_seconds.setValue(config.min_break_seconds)
        self._ntfy_enabled.setChecked(config.ntfy_enabled)
        self._ntfy_topic.setText(config.ntfy_topic)

        index = self._notification_level.findData(config.notification_level)
        self._notification_level.setCurrentIndex(index if index >= 0 else 1)

        self._effects_enabled.setChecked(config.effects_enabled)
        self._effect_image_path.setText(config.effect_image_path)
        self._start_with_windows.setChecked(config.start_with_windows)
        self._hotkey_enabled.setChecked(config.hotkey_enabled)
        self._hotkey_start_work.setText(config.hotkey_start_work)
        self._hotkey_start_work.setEnabled(config.hotkey_enabled)

    def _build_config(self) -> AppConfig:
        """Build AppConfig from current widget values."""
        return AppConfig(
            work_minutes=int(self._work_minutes.value()),
            min_break_seconds=int(self._min_break_seconds.value()),
            ntfy_enabled=bool(self._ntfy_enabled.isChecked()),
            ntfy_topic=self._ntfy_topic.text().strip(),
            notification_level=int(self._notification_level.currentData()),
            effects_enabled=bool(self._effects_enabled.isChecked()),
            effect_image_path=self._effect_image_path.text().strip(),
            start_with_windows=bool(self._start_with_windows.isChecked()),
            hotkey_enabled=bool(self._hotkey_enabled.isChecked()),
            hotkey_start_work=self._hotkey_start_work.text().strip() or "Ctrl+Alt+B",
            messages=dict(self._current_config.messages),
        )

    def _on_save(self) -> None:
        """Persist settings to config.json and close on success."""
        config = self._build_config()
        if not save_config(config):
            QMessageBox.warning(self, "エラー", "設定の保存に失敗しました。")
            return
        self._saved_config = config
        self.accept()

    def _browse_effect_image(self) -> None:
        """Open file dialog and set selected effect image path."""
        current_path = self._effect_image_path.text().strip()
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "演出画像を選択",
            current_path,
            "Images (*.jpg *.jpeg *.bmp *.png *.gif)",
        )
        if not selected_path:
            return
        self._effect_image_path.setText(selected_path)
