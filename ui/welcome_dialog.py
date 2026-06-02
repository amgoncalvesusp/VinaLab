# -*- coding: utf-8 -*-
"""First-run welcome dialog for VinaLab."""

from pathlib import Path
import json

from PySide6.QtWidgets import QComboBox, QDialog, QLabel, QPushButton, QVBoxLayout

from core.i18n import I18n


class WelcomeDialog(QDialog):
    """Welcome dialog shown on first launch."""

    def __init__(self, prefs_path: Path, lang: str = "pt", parent=None) -> None:
        """Create the welcome dialog with language selection."""
        super().__init__(parent)
        self.prefs_path = prefs_path
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Português (Brasil)", "pt")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.setCurrentIndex(0 if lang == "pt" else 1)
        self.title_label = QLabel()
        self.logo_label = QLabel("☕ VinaLab")
        self.author_label = QLabel()
        self.body_label = QLabel()
        self.start_button = QPushButton()
        self._build_ui()
        self.lang_combo.currentIndexChanged.connect(self._retranslate)
        self.start_button.clicked.connect(self.accept)
        self._retranslate()

    def accept(self) -> None:
        """Persist first-run completion and selected language."""
        prefs = {}
        if self.prefs_path.exists():
            try:
                prefs = json.loads(self.prefs_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                prefs = {}
        prefs["language"] = self.current_language()
        prefs["first_run"] = False
        self.prefs_path.parent.mkdir(parents=True, exist_ok=True)
        self.prefs_path.write_text(json.dumps(prefs, indent=2, ensure_ascii=False), encoding="utf-8")
        super().accept()

    def current_language(self) -> str:
        """Return the selected language code."""
        return self.lang_combo.currentData()

    def _build_ui(self) -> None:
        """Build the welcome dialog layout."""
        layout = QVBoxLayout(self)
        self.logo_label.setObjectName("welcomeLogo")
        self.body_label.setWordWrap(True)
        layout.addWidget(self.logo_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.author_label)
        layout.addWidget(self.body_label)
        layout.addWidget(self.lang_combo)
        layout.addWidget(self.start_button)

    def _retranslate(self) -> None:
        """Refresh texts for the selected language."""
        lang = self.current_language()
        self.setWindowTitle(I18n.get("welcome_title", lang))
        self.title_label.setText(I18n.get("welcome_title", lang))
        self.author_label.setText(I18n.get("author_label", lang))
        self.body_label.setText(I18n.get("welcome_body", lang))
        self.start_button.setText(I18n.get("get_started", lang))
