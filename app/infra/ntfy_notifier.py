"""ntfy notification sender for MVP."""

from __future__ import annotations

import traceback

import requests


class NtfyNotifier:
    """Send notifications to ntfy.sh."""

    def __init__(self, enabled: bool, topic: str, message: str) -> None:
        self._enabled = bool(enabled)
        self._topic = topic.strip()
        self._message = message

    def send_break_notification(self) -> None:
        """Send break reminder notification when enabled and configured."""
        if not self._enabled:
            return
        if not self._topic:
            return

        url = f"https://ntfy.sh/{self._topic}"
        headers = {
            "Title": "Break Timer",
            "Priority": "high",
            "Tags": "warning",
        }
        try:
            requests.post(
                url,
                data=self._message.encode("utf-8"),
                headers=headers,
                timeout=5,
            )
        except Exception:
            traceback.print_exc()
