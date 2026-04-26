"""Global hotkey registration for Windows using RegisterHotKey."""

from __future__ import annotations

import ctypes
import sys
import traceback
from collections.abc import Callable
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter
from PySide6.QtWidgets import QApplication


WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
HOTKEY_ID_START_WORK = 1


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
    ]


class _NativeHotkeyFilter(QAbstractNativeEventFilter):
    """Qt native event filter that catches WM_HOTKEY."""

    def __init__(self, on_start_work: Callable[[], None]) -> None:
        super().__init__()
        self._on_start_work = on_start_work

    def nativeEventFilter(self, event_type, message):  # type: ignore[override]
        try:
            event_name = bytes(event_type).decode(errors="ignore")
            if event_name not in {"windows_generic_MSG", "windows_dispatcher_MSG"}:
                return False, 0

            msg = MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and int(msg.wParam) == HOTKEY_ID_START_WORK:
                self._on_start_work()
                return True, 0
        except Exception:
            traceback.print_exc()
        return False, 0


class GlobalHotkeyManager:
    """Manage global hotkey lifecycle for start-work action."""

    def __init__(self, app: QApplication, on_start_work: Callable[[], None]) -> None:
        self._app = app
        self._on_start_work = on_start_work
        self._event_filter = _NativeHotkeyFilter(self._on_start_work)
        self._app.installNativeEventFilter(self._event_filter)
        self._registered = False
        self._enabled = False
        self._hotkey_text = "Ctrl+Alt+B"

    def apply_settings(self, enabled: bool, hotkey_text: str) -> bool:
        """Apply hotkey settings immediately. Returns registration success."""
        self.unregister()
        self._enabled = bool(enabled)
        self._hotkey_text = (hotkey_text or "").strip() or "Ctrl+Alt+B"
        if sys.platform != "win32":
            return False
        if not self._enabled:
            return True

        parsed = _parse_hotkey(self._hotkey_text)
        if parsed is None:
            try:
                raise ValueError(f"unsupported hotkey format: {self._hotkey_text}")
            except Exception:
                traceback.print_exc()
            return False

        modifiers, vk = parsed
        user32 = ctypes.windll.user32
        if not user32.RegisterHotKey(None, HOTKEY_ID_START_WORK, modifiers, vk):
            try:
                raise OSError("RegisterHotKey failed")
            except Exception:
                traceback.print_exc()
            return False
        self._registered = True
        return True

    def unregister(self) -> None:
        """Unregister currently active global hotkey."""
        if not self._registered:
            return
        if sys.platform != "win32":
            self._registered = False
            return
        try:
            ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID_START_WORK)
        except Exception:
            traceback.print_exc()
        finally:
            self._registered = False

    def shutdown(self) -> None:
        """Release OS hotkey and Qt event filter."""
        self.unregister()
        try:
            self._app.removeNativeEventFilter(self._event_filter)
        except Exception:
            traceback.print_exc()


def _parse_hotkey(hotkey_text: str) -> tuple[int, int] | None:
    """Parse hotkey text like 'Ctrl+Alt+B' into RegisterHotKey params."""
    tokens = [token.strip().lower() for token in hotkey_text.split("+") if token.strip()]
    if not tokens:
        return None

    modifiers = 0
    key_token = None
    for token in tokens:
        if token in {"ctrl", "control"}:
            modifiers |= MOD_CONTROL
        elif token == "alt":
            modifiers |= MOD_ALT
        elif token == "shift":
            modifiers |= MOD_SHIFT
        elif token in {"win", "windows"}:
            modifiers |= MOD_WIN
        else:
            key_token = token

    if key_token is None:
        return None

    vk = _token_to_vk(key_token)
    if vk is None:
        return None
    return modifiers, vk


def _token_to_vk(token: str) -> int | None:
    """Convert key token to Windows virtual-key code."""
    normalized = token.strip().lower()
    if len(normalized) == 1 and normalized.isalpha():
        return ord(normalized.upper())
    if len(normalized) == 1 and normalized.isdigit():
        return ord(normalized)

    special = {
        "space": 0x20,
        "enter": 0x0D,
        "return": 0x0D,
        "esc": 0x1B,
        "escape": 0x1B,
        "tab": 0x09,
        "backspace": 0x08,
        "delete": 0x2E,
        "left": 0x25,
        "up": 0x26,
        "right": 0x27,
        "down": 0x28,
    }
    if normalized in special:
        return special[normalized]

    if normalized.startswith("f") and normalized[1:].isdigit():
        index = int(normalized[1:])
        if 1 <= index <= 24:
            return 0x70 + (index - 1)

    return None
