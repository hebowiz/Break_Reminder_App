"""Application entry point for the break reminder app."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.ui.tray import TrayController


def main() -> int:
    """Start the Qt application and run tray-resident MVP."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray = TrayController(app)
    tray.setup()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
