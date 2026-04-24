"""Timer control logic stubs."""

from __future__ import annotations

from app.state import AppState


class TimerController:
    """Control work/break timer transitions."""

    def __init__(self) -> None:
        self.state = AppState.STOPPED

    def start(self) -> None:
        self.state = AppState.WORKING

    def stop(self) -> None:
        self.state = AppState.STOPPED
