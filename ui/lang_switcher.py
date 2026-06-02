# -*- coding: utf-8 -*-
"""Runtime language switcher widget."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class LangSwitcher(QWidget):
    """Two-button PT/EN language switcher."""

    lang_changed = Signal(str)

    def __init__(self, lang: str = "pt") -> None:
        """Create the language switcher with an initial language."""
        super().__init__()
        self.pt_button = QPushButton("🇧🇷 PT")
        self.en_button = QPushButton("🇺🇸 EN")
        self.pt_button.setCheckable(True)
        self.en_button.setCheckable(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.pt_button)
        layout.addWidget(self.en_button)
        self.pt_button.clicked.connect(lambda: self.set_language("pt"))
        self.en_button.clicked.connect(lambda: self.set_language("en"))
        self.set_language(lang, emit=False)

    def set_language(self, lang: str, emit: bool = True) -> None:
        """Set the active language and optionally emit lang_changed."""
        lang = lang if lang in {"pt", "en"} else "pt"
        self.pt_button.setChecked(lang == "pt")
        self.en_button.setChecked(lang == "en")
        self._apply_button_style()
        if emit:
            self.lang_changed.emit(lang)

    def _apply_button_style(self) -> None:
        """Apply checked-state styling to the active language button."""
        self.pt_button.setObjectName("lang_btn_active" if self.pt_button.isChecked() else "lang_btn_inactive")
        self.en_button.setObjectName("lang_btn_active" if self.en_button.isChecked() else "lang_btn_inactive")
        for button in (self.pt_button, self.en_button):
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()
