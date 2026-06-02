# -*- coding: utf-8 -*-
"""Context-sensitive help dock for VinaLab."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QLabel, QVBoxLayout, QWidget

from core.i18n import I18n
from core.scrolling import ScrollManager


class HelpPanel(QDockWidget):
    """Collapsible bilingual contextual help panel."""

    def __init__(self, parent=None) -> None:
        """Create the help panel hidden by default."""
        super().__init__(parent)
        self.lang = "pt"
        self.tab_key = "tab_setup"
        self.setAllowedAreas(Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.setWidget(ScrollManager.wrap(self.container, "help_scroll_area"))
        self.hide()

    def set_context(self, tab_key: str, lang: str) -> None:
        """Update help content for the active tab."""
        self.tab_key = tab_key
        self.retranslate_ui(lang)

    def retranslate_ui(self, lang: str) -> None:
        """Retranslate and rerender the help panel."""
        self.lang = lang
        self.setWindowTitle(I18n.get("help_title", lang))
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        entries = self._entries_for_tab()
        for title_key, body_key, code in entries:
            title = QLabel(f"<b>{I18n.get(title_key, lang)}</b>")
            title.setWordWrap(True)
            body = QLabel(I18n.get(body_key, lang))
            body.setWordWrap(True)
            self.layout.addWidget(title)
            self.layout.addWidget(body)
            if code:
                example = QLabel(f"<pre>{code}</pre>")
                example.setTextInteractionFlags(Qt.TextSelectableByMouse)
                self.layout.addWidget(example)
        self.layout.addStretch()

    def _entries_for_tab(self) -> list[tuple[str, str, str | None]]:
        """Return contextual help entries for the active tab."""
        common = [
            ("help_title", "help_what_is_vina", None),
            ("receptor_label", "help_pdbqt", None),
        ]
        if self.tab_key == "tab_docking":
            return common + [
                ("search_box", "help_search_box", "center_x = 10.0\nsize_x = 22.0"),
                ("exhaustiveness", "help_exhaustiveness", "exhaustiveness = 8"),
            ]
        if self.tab_key == "tab_results":
            return common + [
                ("affinity_col", "help_affinity", None),
                ("rmsd_lb_col", "help_rmsd", None),
            ]
        if self.tab_key == "tab_report":
            return common + [("generate_pdf", "help_affinity", None)]
        return common + [("batch_mode", "help_batch", None), ("search_box", "help_search_box", None)]
