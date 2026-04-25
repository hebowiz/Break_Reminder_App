"""Application-local idle tracking for break validation on Windows."""

from __future__ import annotations

import ctypes
import time
from ctypes import wintypes


class POINT(ctypes.Structure):
    """Windows POINT structure."""

    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class IdleTracker:
    """Track idle seconds based on local cursor/key activity sampling."""

    _VK_KEYS = [
        0x01,  # VK_LBUTTON
        0x02,  # VK_RBUTTON
        0x04,  # VK_MBUTTON
        0x10,  # VK_SHIFT
        0x11,  # VK_CONTROL
        0x12,  # VK_MENU (ALT)
        0x20,  # VK_SPACE
        0x0D,  # VK_RETURN
        0x1B,  # VK_ESCAPE
        0x08,  # VK_BACK
        0x2E,  # VK_DELETE
        0x09,  # VK_TAB
        0x25,  # VK_LEFT
        0x26,  # VK_UP
        0x27,  # VK_RIGHT
        0x28,  # VK_DOWN
    ] + list(range(0x30, 0x3A)) + list(range(0x41, 0x5B))

    def __init__(self, debug: bool = False) -> None:
        self._debug = debug
        self._idle_seconds = 0.0
        self._available = True
        self._last_sample_at = time.monotonic()
        self._last_cursor_pos: tuple[int, int] | None = None

        self._user32 = ctypes.windll.user32
        self._user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
        self._user32.GetCursorPos.restype = wintypes.BOOL
        self._user32.GetAsyncKeyState.argtypes = [wintypes.INT]
        self._user32.GetAsyncKeyState.restype = wintypes.SHORT

    def reset(self) -> None:
        """Reset idle counter and sampling baseline."""
        self._idle_seconds = 0.0
        self._available = True
        self._last_sample_at = time.monotonic()
        self._last_cursor_pos = self._get_cursor_pos()

    def update(self) -> None:
        """Update idle seconds by checking local activity since last sample."""
        now = time.monotonic()
        delta = max(0.0, now - self._last_sample_at)

        activity, current_pos, available = self._detect_activity()
        if not available:
            self._available = False
            self._last_sample_at = now
            return
        self._available = True

        if activity:
            self._idle_seconds = 0.0
        else:
            self._idle_seconds += delta

        self._last_sample_at = now
        if current_pos is not None:
            self._last_cursor_pos = current_pos

        if self._debug:
            print(
                f"[IdleTracker] activity={activity}, "
                f"idle_seconds={self._idle_seconds:.3f}, "
                f"cursor={self._last_cursor_pos}"
            )

    def get_idle_seconds(self) -> float | None:
        """Return sampled idle seconds. None when tracker is unavailable."""
        if not self._available:
            return None
        return self._idle_seconds

    def _detect_activity(self) -> tuple[bool, tuple[int, int] | None, bool]:
        """Detect activity from cursor movement and key/button states."""
        try:
            current_pos = self._get_cursor_pos()
            if current_pos is None:
                return False, None, False

            moved = (
                self._last_cursor_pos is not None and current_pos != self._last_cursor_pos
            )
            if moved:
                return True, current_pos, True

            for vk in self._VK_KEYS:
                if self._is_key_down(vk):
                    return True, current_pos, True

            return False, current_pos, True
        except Exception:
            return False, None, False

    def _get_cursor_pos(self) -> tuple[int, int] | None:
        """Get current cursor coordinates."""
        point = POINT()
        ok = self._user32.GetCursorPos(ctypes.byref(point))
        if not ok:
            return None
        return point.x, point.y

    def _is_key_down(self, vk_code: int) -> bool:
        """Check whether a virtual key is currently pressed."""
        state = self._user32.GetAsyncKeyState(vk_code)
        return bool(state & 0x8000)
