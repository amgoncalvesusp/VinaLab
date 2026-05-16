"""PySide6 splash screen branding for VinaLab."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QSplashScreen

from core.i18n import I18n


class VinaSplash(QSplashScreen):
    """Splash screen with VinaLab branding."""

    def __init__(self, pixmap: QPixmap, lang: str = "pt") -> None:
        """Create the splash screen."""
        super().__init__(pixmap)
        self.lang = lang
        self.showMessage(I18n.get("author_label", lang), Qt.AlignBottom | Qt.AlignCenter, Qt.white)
