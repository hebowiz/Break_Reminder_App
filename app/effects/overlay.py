"""Fullscreen overlay image effect for break prompts."""

from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QMovie, QPixmap, QResizeEvent
from PySide6.QtWidgets import QLabel, QWidget

from app.ui.screen_utils import get_screen_at_cursor


SUPPORTED_EFFECT_EXTENSIONS = {".jpg", ".jpeg", ".bmp", ".png", ".gif"}


class FullscreenOverlay(QWidget):
    """Single-use fullscreen image overlay shown on cursor screen."""

    def __init__(self) -> None:
        super().__init__(None)
        self._image_label: QLabel | None = None
        self._source_pixmap: QPixmap | None = None
        self._movie_source_size: QSize | None = None
        self._movie: QMovie | None = None
        self._setup_window()

    def show_on_cursor_screen(self, image_path: str) -> bool:
        """Prepare media completely and show overlay only on success."""
        try:
            self._teardown_content()
            path = Path(image_path)
            if not self._is_supported_image(path):
                return False

            screen = get_screen_at_cursor()
            if screen is None:
                return False

            target_geometry = screen.geometry()
            target_size = target_geometry.size()
            self.setGeometry(target_geometry)

            label = QLabel(self)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setScaledContents(False)
            label.setGeometry(self.rect())
            self._image_label = label

            if path.suffix.lower() == ".gif":
                if not self._apply_gif(path, target_size):
                    self._teardown_content()
                    return False
            else:
                if not self._apply_static_image(path, target_size):
                    self._teardown_content()
                    return False

            self.update()
            self.show()
            return True
        except Exception:
            traceback.print_exc()
            self._teardown_content()
            return False

    def hide_overlay(self) -> None:
        """Hide overlay and release displayed media resources."""
        self._teardown_content()
        self.hide()

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        """Keep media fitted and centered when widget size changes."""
        if self._image_label is not None:
            self._image_label.setGeometry(self.rect())
        if self._source_pixmap is not None and self._image_label is not None:
            fitted = self._source_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._image_label.setPixmap(fitted)
        if self._movie is not None and self._movie_source_size is not None:
            self._movie.setScaledSize(calculate_fit_size(self._movie_source_size, self.size()))
        super().resizeEvent(event)

    def _setup_window(self) -> None:
        """Configure non-activating always-on-top overlay window."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    def _apply_static_image(self, path: Path, target_size: QSize) -> bool:
        """Load and fit static image formats (.jpg/.jpeg/.bmp/.png)."""
        pixmap = QPixmap(str(path))
        if pixmap.isNull() or self._image_label is None:
            return False
        self._source_pixmap = pixmap
        fitted = pixmap.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._image_label.setPixmap(fitted)
        return True

    def _apply_gif(self, path: Path, target_size: QSize) -> bool:
        """Load and fit GIF image with per-show movie instance."""
        if self._image_label is None:
            return False
        movie = QMovie(str(path))
        if not movie.isValid():
            return False
        movie.jumpToFrame(0)
        source_size = movie.currentImage().size()
        if source_size.isEmpty():
            source_size = movie.frameRect().size()
        if source_size.isEmpty():
            source_size = target_size

        self._movie_source_size = source_size
        movie.setScaledSize(calculate_fit_size(source_size, target_size))
        self._movie = movie
        self._source_pixmap = None
        self._image_label.setMovie(movie)
        movie.start()
        return True

    def _is_supported_image(self, path: Path) -> bool:
        """Return whether image path is existing file with supported extension."""
        if not path.exists() or not path.is_file():
            return False
        return path.suffix.lower() in SUPPORTED_EFFECT_EXTENSIONS

    def _teardown_content(self) -> None:
        """Release media resources and label to avoid stale frame flashes."""
        if self._movie is not None:
            self._movie.stop()
            self._movie.deleteLater()
            self._movie = None

        if self._image_label is not None:
            self._image_label.clear()
            self._image_label.setMovie(None)
            self._image_label.setPixmap(QPixmap())
            self._image_label.deleteLater()
            self._image_label = None

        self._source_pixmap = None
        self._movie_source_size = None


def calculate_fit_size(source_size: QSize, target_size: QSize) -> QSize:
    """Calculate aspect-ratio-preserving fitted size within target bounds."""
    source_w = max(1, source_size.width())
    source_h = max(1, source_size.height())
    target_w = max(1, target_size.width())
    target_h = max(1, target_size.height())

    scale = min(target_w / source_w, target_h / source_h)
    fitted_w = max(1, int(source_w * scale))
    fitted_h = max(1, int(source_h * scale))
    return QSize(fitted_w, fitted_h)
