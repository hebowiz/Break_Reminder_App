"""Application state definitions."""

from enum import Enum, auto


class AppState(Enum):
    STOPPED = auto()
    WORKING = auto()
    NOTIFYING = auto()
    BREAKING = auto()
