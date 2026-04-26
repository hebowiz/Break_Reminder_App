"""Effect orchestration for optional break visuals."""

from __future__ import annotations

from app.effects.overlay import FullscreenOverlay


class EffectManager:
    """Coordinate optional visual effects."""

    def __init__(self, enabled: bool, overlay_text: str) -> None:
        self._enabled = bool(enabled)
        self._overlay = FullscreenOverlay(text=overlay_text)

    def update_settings(self, enabled: bool, overlay_text: str) -> None:
        """Update effect enablement and overlay text."""
        self._enabled = bool(enabled)
        self._overlay.set_text(overlay_text)
        if not self._enabled:
            self.hide_break_effect()

    def show_break_effect(self) -> None:
        """Show break overlay when effects are enabled."""
        if not self._enabled:
            return
        self._overlay.show_on_cursor_screen()

    def hide_break_effect(self) -> None:
        """Hide break overlay."""
        self._overlay.hide_overlay()
