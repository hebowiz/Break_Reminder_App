"""Utilities for selecting target screen in multi-monitor setups."""

from __future__ import annotations

from PySide6.QtGui import QCursor, QGuiApplication, QScreen
from PySide6.QtWidgets import QApplication


def get_screen_at_cursor() -> QScreen | None:
    """Return screen under cursor, fallback to primary screen."""
    app = QApplication.instance()
    if app is None:
        return None

    cursor_pos = QCursor.pos()
    screen = QGuiApplication.screenAt(cursor_pos)
    if screen is not None:
        return screen

    return app.primaryScreen()
