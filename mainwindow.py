"""Main window for the VinaLab desktop application."""

from pathlib import Path
import json
import subprocess
import sys

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QLabel, QMainWindow, QMessageBox, QPushButton, QSizePolicy, QSplitter, QStatusBar, QTabWidget

from core.environment_manager import EnvironmentManager
from core.i18n import I18n
from core.responsive import ResponsiveManager
from tabs.docking_tab import DockingTab
from tabs.prepare_protein_tab import PrepareProteinTab
from tabs.report_tab import ReportTab
from tabs.results_tab import ResultsTab
from tabs.setup_tab import SetupTab
from ui.about_dialog import AboutDialog
from ui.converter_widget import ConverterWidget
from ui.help_panel import HelpPanel
from ui.welcome_dialog import WelcomeDialog


class MainWindow(QMainWindow):
    """Top-level window containing converter, setup, docking, results, and report tabs."""

    docking_started_signal = Signal()

    def __init__(self) -> None:
        """Create the main window and wire tab-level signals."""
        super().__init__()
        self.environment_manager = EnvironmentManager()
        self.prefs_path = self.environment_manager.user_dir / "config" / "user_prefs.json"
        self.was_first_run = not self.prefs_path.exists()
        self.lang = I18n.load_lang(str(self.prefs_path))
        self.current_screen_profile = ResponsiveManager.detect_screen_profile(self.screen())

        self.tabs = QTabWidget()
        self.setup_tab = SetupTab()
        self.converter_tab = ConverterWidget()
        self.prepare_protein_tab = PrepareProteinTab()
        self.results_tab = ResultsTab()
        self.report_tab = ReportTab()
        self.docking_tab = DockingTab(
            setup_provider=self.setup_tab,
            results_consumer=self.results_tab,
            report_consumer=self.report_tab,
        )
        self.report_tab.set_analysis_provider(self.results_tab)

        self.docking_workspace = QSplitter(Qt.Vertical)
        self.docking_workspace.addWidget(self.setup_tab)
        self.docking_workspace.addWidget(self.docking_tab)
        self.docking_workspace.setStretchFactor(0, 1)
        self.docking_workspace.setStretchFactor(1, 2)
        self.docking_workspace.setChildrenCollapsible(False)

        self.tabs.addTab(self.converter_tab, "")
        self.tabs.addTab(self.prepare_protein_tab, "")
        self.tabs.addTab(self.docking_workspace, "")
        self.tabs.addTab(self.report_tab, "")
        self.tabs.setMinimumWidth(340)
        self.tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.workspace_splitter = QSplitter(Qt.Horizontal)
        self.workspace_splitter.addWidget(self.tabs)
        self.workspace_splitter.addWidget(self.results_tab)
        self.workspace_splitter.setStretchFactor(0, 1)
        self.workspace_splitter.setStretchFactor(1, 1)
        self.workspace_splitter.setChildrenCollapsible(False)
        self.setCentralWidget(self.workspace_splitter)

        self.help_panel = HelpPanel(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.help_panel)
        self._build_menu_bar()
        self.docking_tab.docking_launched.connect(self._show_results_tab)
        self.docking_tab.output_directory_changed.connect(self.report_tab.set_output_directory)
        self.docking_tab.parameters_changed.connect(self.report_tab.set_parameters)
        self.docking_tab.box_changed.connect(self.results_tab.update_box_preview)
        self.results_tab.results_changed.connect(self.report_tab.set_results)
        self.results_tab.chart_updated.connect(self.report_tab.set_chart_path)
        self.converter_tab.conversion_ready.connect(self._use_converted_file)
        self.prepare_protein_tab.receptor_prepared.connect(self._use_prepared_receptor)
        self.setup_tab.selection_changed.connect(self._push_receptor_to_viewer)
        self.tabs.currentChanged.connect(self._active_tab_changed)
        self._build_status_bar()
        self.retranslate_ui(self.lang)
        ResponsiveManager.apply_profile(self, self.current_screen_profile)
        self.refresh_environment_status()
        self.results_tab.update_box_preview(self.docking_tab.current_box())
        self._push_receptor_to_viewer()
        self._show_welcome_if_needed()

    def _show_results_tab(self) -> None:
        """Keep the docking workspace visible; results are always shown in the right panel."""
        self.tabs.setCurrentWidget(self.docking_workspace)

    def output_directory(self) -> Path | None:
        """Return the currently selected output directory."""
        return self.docking_tab.output_directory()

    def refresh_environment_status(self) -> None:
        """Refresh the persistent environment readiness status."""
        report = self.environment_manager.cached_status_report()
        if not report:
            self.statusBar().showMessage(I18n.get("env_checking", self.lang))
            self.fix_button.setVisible(False)
            return
        missing = next((package["name"] for package in report["packages"] if not package["installed"]), None)
        if report["all_ready"]:
            self.statusBar().showMessage(I18n.get("env_ready", self.lang))
            self.fix_button.setVisible(False)
        elif missing:
            self.statusBar().showMessage(f"{I18n.get('env_error', self.lang)}: {missing}")
            self.fix_button.setVisible(True)
        else:
            self.statusBar().showMessage(I18n.get("env_checking", self.lang))
            self.fix_button.setVisible(True)

    def rerun_bootstrap(self) -> None:
        """Start the bootstrap launcher to repair the environment."""
        if getattr(sys, "frozen", False):
            self.environment_manager.full_status_report()
            self.refresh_environment_status()
            QMessageBox.information(
                self,
                "Runtime incluído",
                "Esta instalação do VinaLab já inclui o runtime obrigatório. Dependências opcionais de pontuação podem ser instaladas separadamente.",
            )
            return
        launcher_path = Path(__file__).resolve().parent / "launcher.py"
        subprocess.Popen([sys.executable, str(launcher_path)], cwd=Path(__file__).resolve().parent)

    def retranslate_ui(self, lang: str) -> None:
        """Retranslate the whole main window at runtime."""
        self.lang = lang
        I18n.save_lang(self.lang, str(self.prefs_path))
        self.setWindowTitle(I18n.get("window_title", self.lang))
        self.tabs.setTabText(0, I18n.get("tab_converter", self.lang))
        self.tabs.setTabText(1, I18n.get("tab_prepare_protein", self.lang))
        self.tabs.setTabText(2, I18n.get("tab_docking", self.lang))
        self.tabs.setTabText(3, I18n.get("tab_report", self.lang))
        self.setup_tab.retranslate_ui(self.lang)
        self.converter_tab.retranslate_ui(self.lang)
        self.prepare_protein_tab.retranslate_ui(self.lang)
        self.docking_tab.retranslate_ui(self.lang)
        self.results_tab.retranslate_ui(self.lang)
        self.report_tab.retranslate_ui(self.lang)
        self._retranslate_menus(self.lang)
        self.fix_button.setText(I18n.get("fix_now", self.lang))
        self.author_label.setText(I18n.get("author_status", self.lang))
        self.help_panel.retranslate_ui(self.lang)
        self.refresh_environment_status()

    def resizeEvent(self, event) -> None:
        """Reapply the responsive profile when width crosses a profile boundary."""
        new_profile = ResponsiveManager.profile_for_width(self.width(), self.current_screen_profile)
        if new_profile != self.current_screen_profile:
            self.current_screen_profile = new_profile
            ResponsiveManager.apply_profile(self, new_profile)
        super().resizeEvent(event)

    def _build_status_bar(self) -> None:
        """Create the main window status bar and repair button."""
        self.setStatusBar(QStatusBar(self))
        self.fix_button = QPushButton("Fix now")
        self.fix_button.clicked.connect(self.rerun_bootstrap)
        self.author_label = QLabel()
        self.statusBar().addPermanentWidget(self.fix_button)
        self.statusBar().addPermanentWidget(self.author_label)
        self.fix_button.setVisible(False)

    def _build_menu_bar(self) -> None:
        """Create a traditional application menu bar."""
        menu_bar = self.menuBar()
        menu_bar.setNativeMenuBar(False)

        self.file_menu = menu_bar.addMenu("")
        self.analysis_menu = menu_bar.addMenu("")
        self.view_menu = menu_bar.addMenu("")
        self.help_menu = menu_bar.addMenu("")

        self.export_complex_action = QAction(self)
        self.export_complex_action.triggered.connect(self.results_tab.open_export_dialog)
        self.file_menu.addAction(self.export_complex_action)
        self.generate_report_action = QAction(self)
        self.generate_report_action.triggered.connect(self.report_tab.generate_pdf_report)
        self.file_menu.addAction(self.generate_report_action)

        self.validate_protocol_action = QAction(self)
        self.validate_protocol_action.triggered.connect(self.docking_tab.validate_protocol)
        self.analysis_menu.addAction(self.validate_protocol_action)

        self.language_group = QActionGroup(self)
        self.language_group.setExclusive(True)
        self.pt_action = QAction(self)
        self.pt_action.setCheckable(True)
        self.en_action = QAction(self)
        self.en_action.setCheckable(True)
        self.language_group.addAction(self.pt_action)
        self.language_group.addAction(self.en_action)
        self.view_menu.addAction(self.pt_action)
        self.view_menu.addAction(self.en_action)
        self.pt_action.triggered.connect(lambda: self.set_language("pt"))
        self.en_action.triggered.connect(lambda: self.set_language("en"))

        self.quick_help_action = QAction(self)
        self.quick_help_action.triggered.connect(self._toggle_help)
        self.window_help_action = QAction(self)
        self.window_help_action.triggered.connect(self._toggle_help)
        self.about_action = QAction(self)
        self.about_action.triggered.connect(self._show_about)
        self.help_menu.addAction(self.quick_help_action)
        self.help_menu.addAction(self.window_help_action)
        self.help_menu.addSeparator()
        self.help_menu.addAction(self.about_action)

    def _retranslate_menus(self, lang: str) -> None:
        """Retranslate menu titles and actions."""
        self.file_menu.setTitle(I18n.get("menu_file", lang))
        self.analysis_menu.setTitle(I18n.get("menu_analysis", lang))
        self.view_menu.setTitle(I18n.get("menu_language", lang))
        self.help_menu.setTitle(I18n.get("menu_help", lang))
        self.export_complex_action.setText(I18n.get("export_complex", lang))
        self.generate_report_action.setText(I18n.get("generate_report", lang))
        self.validate_protocol_action.setText(I18n.get("validate_protocol", lang))
        self.pt_action.setText(I18n.get("lang_portuguese", lang))
        self.en_action.setText(I18n.get("lang_english", lang))
        self.window_help_action.setText(I18n.get("action_show_help_panel", lang))
        self.quick_help_action.setText(I18n.get("action_quick_help", lang))
        self.about_action.setText(I18n.get("about_button", lang))
        self.pt_action.setChecked(lang == "pt")
        self.en_action.setChecked(lang == "en")

    def set_language(self, lang: str) -> None:
        """Switch UI language at runtime."""
        self.retranslate_ui(lang)

    def _toggle_help(self) -> None:
        """Toggle the contextual help panel."""
        self.help_panel.setVisible(not self.help_panel.isVisible())

    def _show_about(self) -> None:
        """Show authorship and citation information."""
        AboutDialog(self.lang, self).exec()

    def _active_tab_changed(self, index: int) -> None:
        """Update help panel context when the active tab changes."""
        keys = ["tab_converter", "tab_prepare_protein", "tab_docking", "tab_report"]
        if 0 <= index < len(keys):
            self.help_panel.set_context(keys[index], self.lang)

    def _push_receptor_to_viewer(self) -> None:
        """Forward the currently selected receptor path to the results viewer."""
        self.results_tab.update_receptor_preview(self.setup_tab.receptor_path())

    def _use_converted_file(self, filepath: str, molecule_type: str) -> None:
        """Use a converted file in the setup tab."""
        if molecule_type == "receptor":
            self.setup_tab.set_receptor_file(filepath)
        elif molecule_type == "ligand_batch":
            self.setup_tab.set_ligand_folder(filepath)
        else:
            self.setup_tab.set_ligand_file(filepath)
        self.tabs.setCurrentWidget(self.docking_workspace)

    def _use_prepared_receptor(self, filepath: str) -> None:
        """Forward a prepared PDB from Prepare Protein tab to the Converter for PDBQT generation.

        The prepared PDB still needs to be converted to PDBQT before docking. We
        pre-fill the converter input and switch to the converter tab so the user
        can review, choose 'Receptor (proteína)', and run conversion.
        """
        self.converter_tab.input_paths = [Path(filepath)]
        self.converter_tab.input_edit.setText(str(Path(filepath)))
        self.converter_tab.type_combo.setCurrentIndex(1)
        self.converter_tab._suggest_output()
        self.tabs.setCurrentWidget(self.converter_tab)
        self.statusBar().showMessage(
            f"PDB preparado pronto para conversão: {Path(filepath).name}", 5000
        )

    def _show_welcome_if_needed(self) -> None:
        """Show the first-run welcome dialog after the window initializes."""
        prefs = self._read_prefs()
        if self.was_first_run or prefs.get("first_run", True):
            QTimer.singleShot(0, self._show_welcome_dialog)

    def _show_welcome_dialog(self) -> None:
        """Show the welcome dialog and apply the selected language."""
        dialog = WelcomeDialog(self.prefs_path, self.lang, self)
        if dialog.exec():
            self.retranslate_ui(dialog.current_language())

    def _read_prefs(self) -> dict:
        """Read user preferences."""
        if not self.prefs_path.exists():
            return {}
        try:
            return json.loads(self.prefs_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
