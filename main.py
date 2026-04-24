"""Application entry point for the break reminder app."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.ui.tray import TrayController


def main() -> int:
    """Create the Qt application and initialize future tray integration."""
    app = QApplication(sys.argv)
    tray = TrayController()
    tray.setup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
