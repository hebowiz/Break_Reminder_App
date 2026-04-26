"""Effect orchestration for optional break visuals."""

from __future__ import annotations

from app.effects.overlay import FullscreenOverlay


class EffectManager:
    """Coordinate optional visual effects."""

    def __init__(self, enabled: bool, effect_image_path: str) -> None:
        self._enabled = bool(enabled)
        self._effect_image_path = str(effect_image_path).strip()
        self._overlay: FullscreenOverlay | None = None

    def update_settings(self, enabled: bool, effect_image_path: str) -> None:
        """Update effect enablement and image path."""
        self._enabled = bool(enabled)
        self._effect_image_path = str(effect_image_path).strip()
        if not self._enabled or not self._effect_image_path:
            self.hide_break_effect()

    def show_break_effect(self, effect_image_path: str | None = None) -> None:
        """Show break overlay when effects are enabled."""
        if effect_image_path is not None:
            self._effect_image_path = str(effect_image_path).strip()
        if not self._enabled:
            return
        if not self._effect_image_path:
            return
        self.hide_break_effect()
        overlay = FullscreenOverlay()
        if not overlay.show_on_cursor_screen(self._effect_image_path):
            overlay.close()
            overlay.deleteLater()
            return
        self._overlay = overlay

    def hide_break_effect(self) -> None:
        """Hide break overlay."""
        if self._overlay is None:
            return
        self._overlay.hide_overlay()
        self._overlay.close()
        self._overlay.deleteLater()
        self._overlay = None
