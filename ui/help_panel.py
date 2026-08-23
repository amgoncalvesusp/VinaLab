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
        self.layout.setSpacing(10)
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
            title = QLabel(I18n.get(title_key, lang))
            title.setObjectName("label_section_title")
            title.setWordWrap(True)
            body = QLabel(I18n.get(body_key, lang))
            body.setObjectName("label_muted")
            body.setTextFormat(Qt.PlainText)
            body.setWordWrap(True)
            self.layout.addWidget(title)
            self.layout.addWidget(body)
            if code:
                example = QLabel(f"<pre>{code}</pre>")
                example.setObjectName("label_value")
                example.setTextInteractionFlags(Qt.TextSelectableByMouse)
                self.layout.addWidget(example)
        self.layout.addStretch()

    def _entries_for_tab(self) -> list[tuple[str, str, str | None]]:
        """Return contextual help entries for the active tab."""
        common = [
            ("help_beginner_flow_title", "help_beginner_flow", None),
            ("help_light_scope_title", "help_light_scope", None),
        ]
        if self.tab_key == "tab_converter":
            return common + [
                ("help_converter_title", "help_converter", None),
                ("receptor_label", "help_pdbqt", None),
                ("batch_mode", "help_batch", None),
            ]
        if self.tab_key == "tab_prepare_protein":
            return common + [
                ("help_prepare_title", "help_prepare", None),
                ("receptor_label", "help_pdbqt", None),
            ]
        if self.tab_key == "tab_docking":
            return common + [
                ("help_setup_title", "help_setup", None),
                ("search_box", "help_search_box", "center_x = 10.0\nsize_x = 22.0"),
                ("help_reference_ligand_title", "help_reference_ligand", None),
                ("help_box_preview_title", "help_box_preview", None),
                ("exhaustiveness", "help_exhaustiveness", "exhaustiveness = 8"),
            ]
        if self.tab_key == "tab_results":
            return common + [
                ("help_results_title", "help_results", None),
                ("affinity_col", "help_affinity", None),
                ("rmsd_lb_col", "help_rmsd", None),
                ("help_pymol_title", "help_pymol", None),
            ]
        if self.tab_key == "tab_report":
            return common + [
                ("help_report_title", "help_report", None),
                ("affinity_col", "help_affinity", None),
            ]
        return common + [
            ("help_setup_title", "help_setup", None),
            ("receptor_label", "help_pdbqt", None),
            ("search_box", "help_search_box", None),
        ]
