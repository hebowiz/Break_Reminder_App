"""Logging interface stubs."""


class AppLogger:
    """Handle app log persistence and formatting."""

    def log_event(self, event_name: str) -> None:
        """Record an event in a future implementation."""
        _ = event_name
        return None
