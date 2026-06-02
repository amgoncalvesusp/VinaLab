# -*- coding: utf-8 -*-
"""About dialog for VinaLab."""

from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from core.i18n import I18n


class AboutDialog(QDialog):
    """Authorship and citation dialog."""

    def __init__(self, lang: str = "pt", parent=None) -> None:
        """Create the about dialog."""
        super().__init__(parent)
        self.lang = lang
        self.logo_label = QLabel("☕ VinaLab")
        self.title_label = QLabel()
        self.version_label = QLabel()
        self.author_label = QLabel()
        self.license_label = QLabel()
        self.citation_label = QLabel()
        self.close_button = QPushButton()
        self._build_ui()
        self.retranslate_ui(lang)
        self.close_button.clicked.connect(self.accept)

    def retranslate_ui(self, lang: str) -> None:
        """Retranslate the about dialog."""
        self.lang = lang
        self.setWindowTitle(I18n.get("about_title", lang))
        self.title_label.setText(I18n.get("app_title", lang))
        self.version_label.setText(I18n.get("version_label", lang))
        self.author_label.setText(I18n.get("author_label", lang))
        self.license_label.setText(I18n.get("license_label", lang))
        self.citation_label.setText(
            f'<a href="https://vina.scripps.edu/">AutoDock Vina</a> — {I18n.get("vina_citation", lang)}'
        )
        self.close_button.setText("OK")

    def _build_ui(self) -> None:
        """Build the about dialog layout."""
        layout = QVBoxLayout(self)
        self.citation_label.setOpenExternalLinks(True)
        layout.addWidget(self.logo_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.version_label)
        layout.addWidget(self.author_label)
        layout.addWidget(self.license_label)
        layout.addWidget(self.citation_label)
        layout.addWidget(self.close_button)
