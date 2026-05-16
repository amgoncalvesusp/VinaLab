"""Docking parameter tab and execution wiring.

Scoring-function ranking based on benchmark literature (2021-2025):
1. GNINA CNN ensemble: strongest overall virtual screening/redocking performance,
   but requires a separate GNINA binary, typically Linux/WSL.
2. Vinardo: empirical scoring optimized beyond Vina and strong CASF benchmark
   performance.
3. Vina: fast, standard, widely validated AutoDock Vina scoring.
4. AutoDock4/ad4: force-field scoring for charged/metalloprotein cases and
   affinity-map workflows.
"""

import json
from pathlib import Path
import shutil

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QCheckBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.docking_engine import DockingWorker, discover_external_scoring_functions, find_obabel_executable
from core.environment_manager import EnvironmentManager
from core.file_utils import is_pdbqt_file, pdbqt_coordinate_bounds, pdbqt_receptor_atoms
from core.i18n import I18n
from core.scrolling import ScrollManager


SCORING_OPTIONS = [
    {
        "key": "gnina",
        "label_pt": "GNINA (CNN) ★★★★",
        "label_en": "GNINA (CNN) ★★★★",
        "desc_pt": "Melhor desempenho em triagem virtual (deep learning). Requer binário GNINA externo.",
        "desc_en": "Best virtual screening performance (deep learning). Requires an external GNINA binary.",
        "badge_key": "badge_best",
        "badge_object": "badge_best",
        "ref_url": "https://doi.org/10.1186/s13321-025-00973-x",
        "ref_label": "McNutt et al., J. Cheminformatics 2025",
        "available_check": "gnina_binary",
        "vina_sf_name": None,
    },
    {
        "key": "vinardo",
        "label_pt": "Vinardo ★★★☆",
        "label_en": "Vinardo ★★★☆",
        "desc_pt": "Supera Vina em todos os benchmarks CASF. Recomendado para triagem virtual.",
        "desc_en": "Outperforms Vina in all CASF benchmarks. Recommended for virtual screening.",
        "badge_key": "badge_recommended",
        "badge_object": "badge_recommended",
        "ref_url": "https://doi.org/10.1371/journal.pone.0155183",
        "ref_label": "Quiroga & Villarreal, PLoS ONE 2016",
        "available_check": "always",
        "vina_sf_name": "vinardo",
    },
    {
        "key": "vina",
        "label_pt": "Vina (padrão) ★★☆☆",
        "label_en": "Vina (standard) ★★☆☆",
        "desc_pt": "Função padrão. Rápida e amplamente validada.",
        "desc_en": "Standard function. Fast and widely validated.",
        "badge_key": "badge_default",
        "badge_object": "badge_default",
        "ref_url": "https://doi.org/10.1002/jcc.21334",
        "ref_label": "Trott & Olson, J. Comput. Chem. 2010",
        "available_check": "always",
        "vina_sf_name": "vina",
    },
    {
        "key": "ad4",
        "label_pt": "AutoDock4 (ad4) ★★☆☆",
        "label_en": "AutoDock4 (ad4) ★★☆☆",
        "desc_pt": "Campo de força clássico. Melhor para metaloproteínas. Requer mapas de afinidade (AutoGrid4).",
        "desc_en": "Classic force field. Best for metalloproteins. Requires affinity maps (AutoGrid4).",
        "badge_key": "badge_specialized",
        "badge_object": "badge_specialized",
        "ref_url": "https://doi.org/10.1021/acs.jcim.1c00203",
        "ref_label": "Eberhardt et al., J. Chem. Inf. Model. 2021",
        "available_check": "always",
        "vina_sf_name": "ad4",
    },
]


class ScoringFunctionSelector(QGroupBox):
    """Ranked scoring-function selector with references and availability checks."""

    selection_changed = Signal()

    def __init__(self) -> None:
        """Create checkboxes for supported scoring functions."""
        super().__init__()
        self.lang = "pt"
        self.prefs_path = Path(__file__).resolve().parents[1] / "config" / "user_prefs.json"
        self.checkboxes: dict[str, QCheckBox] = {}

        self.description_labels: dict[str, QLabel] = {}
        self.reference_buttons: dict[str, QPushButton] = {}
        self.options = self._ranked_options()
        self._build_ui()
        self.set_selected_keys(self._load_saved_keys())

    def selected_keys(self) -> list[str]:
        """Return all selected scoring option keys."""
        return [key for key, checkbox in self.checkboxes.items() if checkbox.isChecked()]

    def current_key(self) -> str:
        """Return the first selected scoring option key for legacy callers."""
        selected = self.selected_keys()
        return selected[0] if selected else "vina"

    def current_vina_sf_name(self) -> str | None:
        """Return the Vina Python sf_name for the current scoring option."""
        option = self._option_for_key(self.current_key())
        return option["vina_sf_name"] if option else "vina"

    def set_current_key(self, key: str) -> None:
        """Select a scoring function if available."""
        self.set_selected_keys([key])

    def set_selected_keys(self, keys: list[str]) -> None:
        """Select one or more scoring functions."""
        valid_keys = [key for key in keys if key in self.checkboxes and self.checkboxes[key].isEnabled()]
        if not valid_keys:
            valid_keys = ["vina"]
        for key, checkbox in self.checkboxes.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(key in valid_keys)
            checkbox.blockSignals(False)
        self._save_keys(valid_keys)
        self.selection_changed.emit()

    def retranslate_ui(self, lang: str) -> None:
        """Retranslate scoring selector labels."""
        self.lang = lang
        self.setTitle(I18n.get("scoring_group", lang))
        for option in self.options:
            key = option["key"]
            self.checkboxes[key].setText(option["label_pt"] if lang == "pt" else option["label_en"])
            self.description_labels[key].setText(self._description_with_status(option, lang))
            self.reference_buttons[key].setText(I18n.get("ref_button", lang))
            self.reference_buttons[key].setToolTip(option["ref_label"])
            unavailable_reason = self._unavailable_reason(option, lang)
            self.checkboxes[key].setToolTip(unavailable_reason)

    def _build_ui(self) -> None:
        """Build the selector group."""
        layout = QVBoxLayout(self)
        for index, option in enumerate(self.options):
            row_widget = QWidget()
            row = QHBoxLayout()
            row_widget.setLayout(row)
            checkbox = QCheckBox()
            ref_button = QPushButton()
            ref_button.setObjectName("btn_reference")
            ref_button.setFlat(True)
            description = QLabel()
            description.setObjectName("label_muted")
            description.setWordWrap(True)
            unavailable_reason = self._unavailable_reason(option, self.lang)
            if unavailable_reason:
                checkbox.setEnabled(False)
                description.setEnabled(False)
                checkbox.setToolTip(unavailable_reason)
            ref_button.clicked.connect(lambda _, url=option["ref_url"]: QDesktopServices.openUrl(QUrl(url)))
            checkbox.toggled.connect(lambda checked, key=option["key"]: self._selection_toggled(key, checked))
            self.checkboxes[option["key"]] = checkbox
            self.description_labels[option["key"]] = description
            self.reference_buttons[option["key"]] = ref_button
            row.addWidget(checkbox)
            row.addWidget(ref_button)
            row.addWidget(description, stretch=1)
            layout.addWidget(row_widget)
            if index < len(self.options) - 1:
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                layout.addWidget(separator)

    def _selection_toggled(self, key: str, checked: bool) -> None:
        """Persist and emit selection changes."""
        if not self.selected_keys():
            self.checkboxes[key].blockSignals(True)
            self.checkboxes[key].setChecked(True)
            self.checkboxes[key].blockSignals(False)
        self._save_keys(self.selected_keys())
        self.selection_changed.emit()

    def _load_saved_keys(self) -> list[str]:
        """Load saved scoring functions from preferences."""
        if not self.prefs_path.exists():
            return ["vina"]
        try:
            prefs = json.loads(self.prefs_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return ["vina"]
        saved = prefs.get("scoring_functions")
        if isinstance(saved, list):
            return [str(key) for key in saved]
        return [prefs.get("scoring_function", "vina")]

    def _save_keys(self, keys: list[str]) -> None:
        """Save selected scoring functions to preferences."""
        prefs = {}
        if self.prefs_path.exists():
            try:
                prefs = json.loads(self.prefs_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                prefs = {}
        prefs["scoring_functions"] = keys
        prefs["scoring_function"] = keys[0] if keys else "vina"
        self.prefs_path.parent.mkdir(parents=True, exist_ok=True)
        self.prefs_path.write_text(json.dumps(prefs, indent=2, ensure_ascii=False), encoding="utf-8")

    def _external_options(self) -> list[dict]:
        """Build options for pontuacao/ scoring bundles."""
        available = {item["key"]: item for item in discover_external_scoring_functions()}
        definitions = [
            {
                "key": "rtmscore",
                "label_pt": "RTMScore",
                "label_en": "RTMScore",
                "desc_pt": "Graph Transformer; forte em CASF-2016 para pose e triagem. Requer torch/dgl/MDAnalysis.",
                "desc_en": "Graph Transformer; strong CASF-2016 pose and screening performance. Requires torch/dgl/MDAnalysis.",
                "badge_key": "badge_best",
                "badge_object": "badge_best",
                "ref_url": "https://pubs.acs.org/doi/10.1021/acs.jmedchem.2c00991",
                "ref_label": "RTMScore, J. Med. Chem. 2022",
                "available_check": "archive",
                "vina_sf_name": "vina",
            },
            {
                "key": "delta_vina_xgb",
                "label_pt": "DeltaVinaXGB-Light",
                "label_en": "DeltaVinaXGB-Light",
                "desc_pt": "XGBoost sobre componentes do Vina; recomendado para validacao cruzada em CASF-2016.",
                "desc_en": "XGBoost over Vina components; recommended for CASF-2016 cross-validation.",
                "badge_key": "badge_recommended",
                "badge_object": "badge_recommended",
                "ref_url": "https://www.mdpi.com/1420-3049/27/14/4568/xml",
                "ref_label": "ML-era docking review, Molecules 2022",
                "available_check": "archive",
                "vina_sf_name": "vina",
            },
            {
                "key": "deltavina_rf20",
                "label_pt": "DeltaVinaRF20",
                "label_en": "DeltaVinaRF20",
                "desc_pt": "Random Forest que corrige Vina; historicamente forte em CASF-2013/2007, mas requer Python 2/R.",
                "desc_en": "Random Forest correction to Vina; historically strong on CASF-2013/2007, but requires Python 2/R.",
                "badge_key": "badge_specialized",
                "badge_object": "badge_specialized",
                "ref_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5140681/",
                "ref_label": "DeltaVinaRF20, J. Comput. Chem. 2016",
                "available_check": "archive",
                "vina_sf_name": "vina",
            },
        ]
        for option in definitions:
            option["archive_available"] = option["key"] in available
        manager = EnvironmentManager(Path(__file__).resolve().parents[1])
        cached_report = manager.cached_status_report()
        statuses = cached_report.get("scoring_functions") or manager.scoring_function_statuses()
        for option in definitions:
            status = statuses.get(option["key"], {})
            option["dependency_available"] = bool(status.get("available", False))
            option["unavailable_reason"] = status.get("reason", "")
            option["missing_imports"] = status.get("missing_imports", [])
        return definitions

    def _ranked_options(self) -> list[dict]:
        """Return scoring options ordered by literature-based recommendation."""
        native = {option["key"]: option for option in SCORING_OPTIONS}
        external = {option["key"]: option for option in self._external_options()}
        order = ["rtmscore", "gnina", "delta_vina_xgb", "deltavina_rf20", "vinardo", "vina", "ad4"]
        merged = {**native, **external}
        return [merged[key] for key in order if key in merged]

    def _option_for_key(self, key: str) -> dict | None:
        """Return an option dictionary by key."""
        return next((option for option in self.options if option["key"] == key), None)

    def _description_with_status(self, option: dict, lang: str) -> str:
        """Return the option description plus an availability line."""
        description = option["desc_pt"] if lang == "pt" else option["desc_en"]
        reason = self._unavailable_reason(option, lang)
        if reason:
            return f"{description}\nStatus: indisponível - {reason}"
        return f"{description}\nStatus: disponível"

    def _unavailable_reason(self, option: dict, lang: str) -> str:
        """Return a user-facing reason when a scoring option is unavailable."""
        if option["available_check"] == "gnina_binary" and _gnina_executable() is None:
            return I18n.get("scoring_gnina_warn", lang)
        if option["available_check"] == "archive" and not option.get("archive_available", False):
            return "Arquivo de pontuação não encontrado em pontuacao/."
        if option["available_check"] == "archive" and not option.get("dependency_available", True):
            return option.get("unavailable_reason") or "Dependência opcional de pontuação ausente."
        return ""


class DockingTab(QWidget):
    """Collect Vina parameters, save/load configs, and launch docking."""

    docking_launched = Signal()
    output_directory_changed = Signal(object)
    parameters_changed = Signal(dict)
    box_changed = Signal(dict)

    def __init__(self, setup_provider, results_consumer, report_consumer) -> None:
        """Create parameter controls and connect execution signals."""
        super().__init__()
        self.lang = "pt"
        self.setup_provider = setup_provider
        self.results_consumer = results_consumer
        self.report_consumer = report_consumer
        self.worker: DockingWorker | None = None
        self.validation_rows: list[dict] = []
        self.validation_reference_path: Path | None = None
        self.validation_top_n = 10
        self.scoring_selector = ScoringFunctionSelector()
        self.center_x = self._double_spin(-9999, 9999, 0.5, 3, 0.0)
        self.center_y = self._double_spin(-9999, 9999, 0.5, 3, 0.0)
        self.center_z = self._double_spin(-9999, 9999, 0.5, 3, 0.0)
        self.size_x = self._double_spin(1, 126, 1.0, 1, 20.0)
        self.size_y = self._double_spin(1, 126, 1.0, 1, 20.0)
        self.size_z = self._double_spin(1, 126, 1.0, 1, 20.0)
        self.size_preset_combo = QComboBox()
        self.snap_atom_button = QPushButton()
        self.snap_ligand_button = QPushButton()
        self.save_box_button = QPushButton()
        self.load_box_combo = QComboBox()
        self.box_presets_path = Path(__file__).resolve().parents[1] / "config" / "box_presets.json"
        self.exhaustiveness = self._spin(1, 512, 8)
        self.num_modes = self._spin(1, 20, 9)
        self.energy_range = self._double_spin(1, 10, 0.5, 1, 3.0)
        self.cpu = self._spin(0, 64, 0)
        self.seed = self._spin(0, 2147483647, 0)
        self.fix_seed = QCheckBox("Fixar semente para reprodutibilidade")
        self.min_rmsd = self._double_spin(0, 20, 0.1, 2, 1.0)
        self.output_edit = QLineEdit()
        self.progress_bar = QProgressBar()
        self.run_button = QPushButton()
        self.run_button.setObjectName("btn_primary")
        self.dependency_status_label = QLabel()
        self.checklist_group = QGroupBox()
        self.checklist_layout = QVBoxLayout()
        self.search_group = QGroupBox()
        self.parameter_group = QGroupBox()
        self.output_group = QGroupBox()
        self.atom_center_group = QGroupBox()
        self.atom_center_checkbox = QCheckBox()
        self.atom_tree = QTreeWidget()
        self.reload_atoms_button = QPushButton()
        self.atom_status_label = QLabel()
        self.auto_grid_button = QPushButton()
        self.save_button = QPushButton()
        self.load_button = QPushButton()
        self.output_button = QPushButton()
        self.labels = {key: QLabel() for key in (
            "scoring_label",
            "center_label",
            "size_label",
            "exhaustiveness",
            "num_modes",
            "energy_range",
            "cpu_label",
            "seed_label",
            "min_rmsd",
            "output_dir",
        )}
        for label in self.labels.values():
            label.setObjectName("label_field")
        self._build_ui()
        self._connect_signals()
        self.retranslate_ui(self.lang)

    def output_directory(self) -> Path | None:
        """Return the selected output directory."""
        text = self.output_edit.text().strip()
        return Path(text) if text else None

    def current_parameters(self) -> dict:
        """Return all current docking parameters as a dictionary."""
        seed = self.seed.value() if self.fix_seed.isChecked() else 0
        return {
            "scoring_function": self.scoring_selector.current_key(),
            "vina_sf_name": self.scoring_selector.current_vina_sf_name(),
            "scoring_functions": self.scoring_selector.selected_keys(),
            "center_x": self.center_x.value(),
            "center_y": self.center_y.value(),
            "center_z": self.center_z.value(),
            "size_x": self.size_x.value(),
            "size_y": self.size_y.value(),
            "size_z": self.size_z.value(),
            "exhaustiveness": self.exhaustiveness.value(),
            "num_modes": self.num_modes.value(),
            "energy_range": self.energy_range.value(),
            "cpu": self.cpu.value(),
            "seed": seed,
            "min_rmsd": self.min_rmsd.value(),
            "out": str(self.output_directory() or ""),
        }

    def save_config_file(self) -> None:
        """Write a Vina-format text config file from current parameters."""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            I18n.get("save_vina_config", self.lang),
            "",
            I18n.get("text_files", self.lang),
        )
        if not file_name:
            return
        params = self.current_parameters()
        config_lines = [
            f"scoring = {','.join(params['scoring_functions'])}",
            f"center_x = {params['center_x']:.3f}",
            f"center_y = {params['center_y']:.3f}",
            f"center_z = {params['center_z']:.3f}",
            f"size_x = {params['size_x']:.1f}",
            f"size_y = {params['size_y']:.1f}",
            f"size_z = {params['size_z']:.1f}",
            f"exhaustiveness = {params['exhaustiveness']}",
            f"num_modes = {params['num_modes']}",
            f"energy_range = {params['energy_range']:.1f}",
            f"cpu = {params['cpu']}",
            f"seed = {params['seed']}",
            f"min_rmsd = {params['min_rmsd']:.2f}",
            f"out = {params['out']}",
        ]
        Path(file_name).write_text("\n".join(config_lines) + "\n", encoding="utf-8")

    def load_config_file(self) -> None:
        """Load a Vina config file and populate supported fields."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            I18n.get("load_vina_config", self.lang),
            "",
            f"{I18n.get('text_files', self.lang)};;{I18n.get('all_files', self.lang)}",
        )
        if not file_name:
            return
        values: dict[str, str] = {}
        for raw_line in Path(file_name).read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
        self._apply_config_values(values)

    def launch_docking(self) -> None:
        """Validate all inputs and start the docking worker thread."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, I18n.get("docking_running", self.lang), I18n.get("docking_running_msg", self.lang))
            return
        if not self.setup_provider.validate_inputs():
            QMessageBox.warning(self, I18n.get("invalid_setup", self.lang), I18n.get("invalid_setup_msg", self.lang))
            return
        output_directory = self.output_directory()
        if output_directory is None:
            QMessageBox.warning(self, I18n.get("missing_output", self.lang), I18n.get("missing_output_msg", self.lang))
            return

        parameters = self.current_parameters()
        self.parameters_changed.emit(parameters)
        self.output_directory_changed.emit(output_directory)
        self.results_consumer.clear_results()
        self.progress_bar.setValue(0)
        self.run_button.setEnabled(False)
        self.docking_launched.emit()

        self.worker = DockingWorker(
            receptor_path=self.setup_provider.receptor_path(),
            rigid_receptor_path=self.setup_provider.rigid_receptor_path(),
            flexible_receptor_path=self.setup_provider.flexible_receptor_path(),
            ligand_paths=self.setup_provider.ligand_paths(),
            output_directory=output_directory,
            parameters=parameters,
        )
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.log_signal.connect(self.results_consumer.append_log)
        self.worker.result_signal.connect(self.results_consumer.add_results)
        self.worker.error_signal.connect(self._show_error)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()

    def validate_protocol(self) -> None:
        """Run redocking validation against a crystallographic reference pose."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, I18n.get("docking_running", self.lang), I18n.get("docking_running_msg", self.lang))
            return
        if not self.setup_provider.validate_inputs():
            QMessageBox.warning(self, I18n.get("invalid_setup", self.lang), I18n.get("invalid_setup_msg", self.lang))
            return
        reference_file, _ = QFileDialog.getOpenFileName(self, "Pose cristalográfica de referência", "", "Arquivos PDBQT (*.pdbqt);;Todos os arquivos (*)")
        if not reference_file:
            return
        top_n, ok = QInputDialog.getInt(self, "Validar protocolo", "Corte de sucesso Top-N", 10, 1, 100, 1)
        if not ok:
            return
        output_directory = (self.output_directory() or Path.cwd()) / "validation_redocking"
        output_directory.mkdir(parents=True, exist_ok=True)
        self.validation_rows = []
        self.validation_reference_path = Path(reference_file)
        self.validation_top_n = top_n
        parameters = self.current_parameters()
        parameters["out"] = str(output_directory)
        self.results_consumer.append_log(f"Iniciando redocking de validação do protocolo em {output_directory}.")
        self.run_button.setEnabled(False)
        self.docking_launched.emit()
        self.worker = DockingWorker(
            receptor_path=self.setup_provider.receptor_path(),
            rigid_receptor_path=self.setup_provider.rigid_receptor_path(),
            flexible_receptor_path=self.setup_provider.flexible_receptor_path(),
            ligand_paths=self.setup_provider.ligand_paths(),
            output_directory=output_directory,
            parameters=parameters,
        )
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.log_signal.connect(self.results_consumer.append_log)
        self.worker.result_signal.connect(self._collect_validation_results)
        self.worker.error_signal.connect(self._show_error)
        self.worker.finished.connect(self._worker_finished)
        self.worker.finished.connect(self._validation_finished)
        self.worker.start()

    def _collect_validation_results(self, rows: list[dict]) -> None:
        """Collect validation redocking results without replacing the main table."""
        self.validation_rows.extend(rows)

    def _validation_finished(self) -> None:
        """Open validation report after redocking completes."""
        if self.validation_reference_path is None:
            return
        self.results_consumer.append_log(f"Validação do protocolo interpretou {len(self.validation_rows)} pose(s).")
        self.results_consumer.show_validation_report(
            self.validation_rows,
            self.validation_reference_path,
            self.validation_top_n,
        )

    def retranslate_ui(self, lang: str) -> None:
        """Retranslate docking tab controls and tooltips."""
        self.lang = lang
        self.scoring_selector.retranslate_ui(lang)
        self.search_group.setTitle(I18n.get("search_box", lang))
        self.atom_center_group.setTitle(I18n.get("protein_atom_center", lang))
        self.parameter_group.setTitle(I18n.get("docking_group", lang))
        self.output_group.setTitle(I18n.get("output_dir", lang))
        self.checklist_group.setTitle(I18n.get("pre_run_checklist", lang))
        for key, label in self.labels.items():
            label.setText(I18n.get(key, lang))
        self.fix_seed.setText(I18n.get("fix_seed", lang))
        self.save_button.setText(I18n.get("save_config", lang))
        self.load_button.setText(I18n.get("load_config", lang))
        self.auto_grid_button.setText(I18n.get("adjust_box_size_ligand", lang))
        self.atom_center_checkbox.setText(I18n.get("choose_receptor_atom", lang))
        self.reload_atoms_button.setText(I18n.get("load_receptor_atoms", lang))
        self.snap_atom_button.setText(I18n.get("snap_selected_atom", lang))
        self.snap_ligand_button.setText(I18n.get("snap_crystal_ligand", lang))
        self.save_box_button.setText(I18n.get("save_box", lang))
        self.run_button.setText(I18n.get("run_docking", lang))
        self.output_button.setText(I18n.get("browse_button", lang))
        self.scoring_selector.setToolTip(I18n.get("tip_scoring", lang))
        for widget in (self.center_x, self.center_y, self.center_z):
            widget.setToolTip(I18n.get("tip_center", lang))
        for widget in (self.size_x, self.size_y, self.size_z):
            widget.setToolTip(I18n.get("tip_size", lang))
        self.auto_grid_button.setToolTip(I18n.get("tip_center", lang))
        self.snap_atom_button.setToolTip("Use o átomo do receptor selecionado na árvore como centro da caixa.")
        self.snap_ligand_button.setToolTip("Carregue um ligante PDBQT de referência e defina o centro no centro geométrico.")
        self.save_box_button.setToolTip("Salve o centro e o tamanho atuais como predefinição local nomeada.")
        self.load_box_combo.setToolTip("Carregue uma predefinição salva da caixa de busca.")
        self.exhaustiveness.setToolTip(I18n.get("tip_exhaustiveness", lang))
        self.num_modes.setToolTip(I18n.get("tip_num_modes", lang))
        self.energy_range.setToolTip(I18n.get("tip_energy_range", lang))
        self.cpu.setToolTip(I18n.get("tip_cpu", lang))
        self.seed.setToolTip(I18n.get("tip_seed", lang))
        self.fix_seed.setToolTip(I18n.get("tip_seed", lang))
        self.min_rmsd.setToolTip(I18n.get("help_rmsd", lang))
        self.output_edit.setToolTip(I18n.get("tip_output", lang))
        self.output_button.setToolTip(I18n.get("tip_output", lang))
        self.save_button.setToolTip(I18n.get("save_config", lang))
        self.load_button.setToolTip(I18n.get("load_config", lang))
        self.run_button.setToolTip(I18n.get("run_docking", lang))
        self._set_parameter_explanations()
        self._refresh_dependency_status()
        self._refresh_pre_run_checklist()

    def _build_ui(self) -> None:
        """Build the docking parameter layout."""
        outer_layout = QVBoxLayout(self)
        content = QWidget()
        layout = QVBoxLayout(content)
        self.output_edit.setReadOnly(True)
        layout.addWidget(self.scoring_selector)

        search_form = QFormLayout(self.search_group)
        search_form.addRow(self.labels["center_label"], self._xyz_row(self.center_x, self.center_y, self.center_z))
        search_form.addRow(self.labels["size_label"], self._xyz_row(self.size_x, self.size_y, self.size_z))
        search_form.addRow("Predefinição de tamanho", self._box_size_preset_row())
        self.auto_grid_button.clicked.connect(self.fit_grid_to_ligands)
        search_form.addRow(self.auto_grid_button)
        search_form.addRow(self._box_snap_row())
        search_form.addRow("Predefinições da caixa", self._box_preset_row())
        search_form.addRow(self._build_atom_center_group())
        layout.addWidget(self.search_group)
        layout.addWidget(self._separator())

        form = QFormLayout(self.parameter_group)
        form.addRow(self.labels["exhaustiveness"], self.exhaustiveness)
        form.addRow(self.labels["num_modes"], self.num_modes)
        form.addRow(self.labels["energy_range"], self.energy_range)
        form.addRow(self.labels["cpu_label"], self.cpu)
        form.addRow(self.labels["seed_label"], self._seed_row())
        form.addRow(self.labels["min_rmsd"], self.min_rmsd)
        layout.addWidget(self.parameter_group)
        layout.addWidget(self._separator())

        output_form = QFormLayout(self.output_group)
        output_form.addRow(self.labels["output_dir"], self._output_row())
        config_row = QHBoxLayout()
        self.save_button.clicked.connect(self.save_config_file)
        self.load_button.clicked.connect(self.load_config_file)
        config_row.addWidget(self.save_button)
        config_row.addWidget(self.load_button)
        output_form.addRow(config_row)
        layout.addWidget(self.output_group)

        button_row = QHBoxLayout()
        self.run_button.clicked.connect(self.launch_docking)
        button_row.addStretch()
        button_row.addWidget(self.run_button)
        layout.addLayout(button_row)
        layout.addWidget(self.progress_bar)
        self.dependency_status_label.setWordWrap(True)
        layout.addWidget(self.dependency_status_label)
        self.checklist_group.setLayout(self.checklist_layout)
        layout.addWidget(self.checklist_group)
        outer_layout.addWidget(ScrollManager.wrap(content))

    def _box_size_preset_row(self) -> QHBoxLayout:
        """Create size preset controls for common docking boxes."""
        self.size_preset_combo.addItems(["Personalizado", "Pequena (15x15x15)", "Média (20x20x20)", "Grande (25x25x25)"])
        self.size_preset_combo.setCurrentText("Média (20x20x20)")
        self.size_preset_combo.currentTextChanged.connect(self._apply_size_preset)
        row = QHBoxLayout()
        row.addWidget(self.size_preset_combo)
        return row

    def _box_snap_row(self) -> QHBoxLayout:
        """Create snap-to-center shortcut buttons."""
        self.snap_atom_button.clicked.connect(self._snap_to_selected_atom)
        self.snap_ligand_button.clicked.connect(self._snap_to_crystallographic_ligand)
        row = QHBoxLayout()
        row.addWidget(self.snap_atom_button)
        row.addWidget(self.snap_ligand_button)
        return row

    def _box_preset_row(self) -> QHBoxLayout:
        """Create save/load controls for named box presets."""
        self.save_box_button.clicked.connect(self._save_box_preset)
        self.load_box_combo.currentTextChanged.connect(self._load_box_preset)
        self._refresh_box_preset_combo()
        row = QHBoxLayout()
        row.addWidget(self.load_box_combo)
        row.addWidget(self.save_box_button)
        return row

    def _connect_signals(self) -> None:
        """Connect parameter changes to report updates."""
        widgets = [
            self.scoring_selector,
            self.center_x,
            self.center_y,
            self.center_z,
            self.size_x,
            self.size_y,
            self.size_z,
            self.exhaustiveness,
            self.num_modes,
            self.energy_range,
            self.cpu,
            self.seed,
            self.fix_seed,
            self.min_rmsd,
        ]
        for widget in widgets:
            signal = getattr(widget, "valueChanged", None) or getattr(widget, "selection_changed", None) or getattr(widget, "toggled", None)
            signal.connect(lambda *_: self.parameters_changed.emit(self.current_parameters()))
            signal.connect(lambda *_: self._refresh_pre_run_checklist())
        for widget in (self.center_x, self.center_y, self.center_z, self.size_x, self.size_y, self.size_z):
            widget.valueChanged.connect(lambda *_: self.box_changed.emit(self.current_box()))
        self.atom_center_checkbox.toggled.connect(self._atom_center_toggled)
        self.reload_atoms_button.clicked.connect(self._load_receptor_atoms)
        self.atom_tree.itemClicked.connect(self._atom_tree_item_clicked)
        if hasattr(self.setup_provider, "selection_changed"):
            self.setup_provider.selection_changed.connect(self._setup_selection_changed)
            self.setup_provider.selection_changed.connect(self._refresh_pre_run_checklist)

    def fit_grid_to_ligands(self) -> None:
        """Fit only the box size to ligand bounds, keeping the receptor-point center unchanged."""
        ligand_paths = self.setup_provider.ligand_paths()
        bounds = pdbqt_coordinate_bounds(ligand_paths)
        if bounds is None:
            QMessageBox.warning(self, I18n.get("warning_title", self.lang), I18n.get("auto_grid_failed", self.lang))
            return

        padding = 4.0
        size = tuple(min(126.0, max(1.0, axis_bounds[1] - axis_bounds[0] + padding)) for axis_bounds in bounds)
        self.size_x.setValue(size[0])
        self.size_y.setValue(size[1])
        self.size_z.setValue(size[2])
        self.parameters_changed.emit(self.current_parameters())
        self.box_changed.emit(self.current_box())
        QMessageBox.information(
            self,
            I18n.get("success_title", self.lang),
            (
                "Centro da caixa de busca mantido a partir dos campos do ponto receptor/proteína. "
                f"Tamanho da caixa atualizado para ({size[0]:.1f}, {size[1]:.1f}, {size[2]:.1f})."
            ),
        )

    def current_box(self) -> dict:
        """Return current search-box center and size values."""
        return {
            "center_x": self.center_x.value(),
            "center_y": self.center_y.value(),
            "center_z": self.center_z.value(),
            "size_x": self.size_x.value(),
            "size_y": self.size_y.value(),
            "size_z": self.size_z.value(),
        }

    def _apply_size_preset(self, label: str) -> None:
        """Apply common cubic search-box size presets."""
        presets = {
            "Pequena (15x15x15)": 15.0,
            "Média (20x20x20)": 20.0,
            "Grande (25x25x25)": 25.0,
        }
        if label not in presets:
            return
        value = presets[label]
        for widget in (self.size_x, self.size_y, self.size_z):
            widget.setValue(value)
        self.box_changed.emit(self.current_box())

    def _snap_to_selected_atom(self) -> None:
        """Set the box center from the current receptor atom/residue tree selection."""
        item = self.atom_tree.currentItem()
        if item is None:
            QMessageBox.information(self, "Centralizar no átomo selecionado", "Selecione primeiro um átomo ou resíduo do receptor.")
            return
        atom = item.data(0, Qt.UserRole)
        if atom:
            self._set_center_from_xyz(float(atom["x"]), float(atom["y"]), float(atom["z"]))
            return
        child_atoms = [item.child(index).data(0, Qt.UserRole) for index in range(item.childCount())]
        child_atoms = [child for child in child_atoms if child]
        if not child_atoms:
            return
        x = sum(float(child["x"]) for child in child_atoms) / len(child_atoms)
        y = sum(float(child["y"]) for child in child_atoms) / len(child_atoms)
        z = sum(float(child["z"]) for child in child_atoms) / len(child_atoms)
        self._set_center_from_xyz(x, y, z)

    def _snap_to_crystallographic_ligand(self) -> None:
        """Set the box center from the geometric center of a reference ligand."""
        file_name, _ = QFileDialog.getOpenFileName(self, "Ligante cristalográfico", "", "Arquivos PDBQT (*.pdbqt);;Todos os arquivos (*)")
        if not file_name:
            return
        bounds = pdbqt_coordinate_bounds([Path(file_name)])
        if bounds is None:
            QMessageBox.warning(self, "Ligante cristalográfico", "Não foi possível ler as coordenadas do ligante.")
            return
        center = tuple((axis_bounds[0] + axis_bounds[1]) / 2 for axis_bounds in bounds)
        self._set_center_from_xyz(center[0], center[1], center[2])

    def _set_center_from_xyz(self, x: float, y: float, z: float) -> None:
        """Update center spin boxes and emit box preview signal."""
        self.center_x.setValue(x)
        self.center_y.setValue(y)
        self.center_z.setValue(z)
        self.parameters_changed.emit(self.current_parameters())
        self.box_changed.emit(self.current_box())

    def _save_box_preset(self) -> None:
        """Save the current search box under a user-provided name."""
        name, ok = QInputDialog.getText(self, "Salvar caixa", "Nome da predefinição")
        if not ok or not name.strip():
            return
        presets = self._read_box_presets()
        presets[name.strip()] = self.current_box()
        self.box_presets_path.parent.mkdir(parents=True, exist_ok=True)
        self.box_presets_path.write_text(json.dumps(presets, indent=2), encoding="utf-8")
        self._refresh_box_preset_combo(name.strip())

    def _load_box_preset(self, name: str) -> None:
        """Load a saved search-box preset."""
        if not name or name == "Carregar predefinição":
            return
        preset = self._read_box_presets().get(name)
        if not preset:
            return
        self.center_x.setValue(float(preset.get("center_x", self.center_x.value())))
        self.center_y.setValue(float(preset.get("center_y", self.center_y.value())))
        self.center_z.setValue(float(preset.get("center_z", self.center_z.value())))
        self.size_x.setValue(float(preset.get("size_x", self.size_x.value())))
        self.size_y.setValue(float(preset.get("size_y", self.size_y.value())))
        self.size_z.setValue(float(preset.get("size_z", self.size_z.value())))
        self.box_changed.emit(self.current_box())

    def _refresh_box_preset_combo(self, selected: str = "") -> None:
        """Refresh saved preset names in the load combo."""
        presets = self._read_box_presets()
        self.load_box_combo.blockSignals(True)
        self.load_box_combo.clear()
        self.load_box_combo.addItem("Carregar predefinição")
        self.load_box_combo.addItems(sorted(presets))
        if selected:
            self.load_box_combo.setCurrentText(selected)
        self.load_box_combo.blockSignals(False)

    def _read_box_presets(self) -> dict:
        """Read saved search-box presets from local config."""
        if not self.box_presets_path.exists():
            return {}
        try:
            data = json.loads(self.box_presets_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def _refresh_pre_run_checklist(self) -> None:
        """Refresh pre-run quality checks for current inputs and environment."""
        while self.checklist_layout.count():
            item = self.checklist_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for status, message, detail in self._pre_run_checks():
            button = QPushButton(f"{self._check_icon(status)} {message}")
            button.setFlat(True)
            button.setToolTip(detail)
            button.setStyleSheet(self._check_style(status))
            button.clicked.connect(lambda _checked=False, text=detail: QMessageBox.information(self, "Checklist pré-execução", text))
            self.checklist_layout.addWidget(button)

    def _pre_run_checks(self) -> list[tuple[str, str, str]]:
        """Return status/message/detail rows for the pre-run checklist."""
        checks: list[tuple[str, str, str]] = []
        receptor = self.setup_provider.rigid_receptor_path() or self.setup_provider.receptor_path()
        receptor_ok = bool(receptor and is_pdbqt_file(receptor) and pdbqt_coordinate_bounds([receptor]) is not None)
        checks.append(("ok" if receptor_ok else "fail", "Arquivo do receptor carregado e interpretável", "Selecione um arquivo de receptor .pdbqt válido."))

        ligand_paths = self.setup_provider.ligand_paths()
        ligand_bounds = pdbqt_coordinate_bounds(ligand_paths) if ligand_paths else None
        ligand_ok = bool(ligand_paths and ligand_bounds is not None)
        checks.append(("ok" if ligand_ok else "fail", "Arquivo do ligante carregado e interpretável", "Selecione um arquivo de ligante .pdbqt válido ou uma pasta contendo arquivos .pdbqt."))

        if ligand_bounds is None:
            checks.append(("fail", "Sobreposição ligante/caixa indisponível", "Carregue as coordenadas do ligante antes de verificar a sobreposição com a grade."))
        elif self._bounds_overlap_box(ligand_bounds):
            checks.append(("ok", "Coordenadas do ligante sobrepõem a caixa de busca", "Os limites do ligante sobrepõem a grade atual do Vina."))
        else:
            checks.append(("fail", "Coordenadas do ligante não sobrepõem a caixa de busca", "Mova ou redimensione a caixa de busca para que as coordenadas do ligante sobreponham a grade."))

        obabel_ok = find_obabel_executable() is not None
        checks.append(("ok" if obabel_ok else "fail", "OpenBabel disponível", "Instale o OpenBabel ou execute o inicializador para reparar o suporte de conversão."))

        report = EnvironmentManager(Path(__file__).resolve().parents[1]).cached_status_report()
        scoring_statuses = report.get("scoring_functions", {}) if report else {}
        for scoring_key in self.scoring_selector.selected_keys():
            option = self.scoring_selector._option_for_key(scoring_key)
            label = option["label_en"] if option else scoring_key
            if scoring_key in {"vina", "vinardo", "ad4", "gnina"}:
                unavailable = self.scoring_selector._unavailable_reason(option, self.lang) if option else ""
                checks.append(("fail" if unavailable else "ok", f"Pontuação {label}", unavailable or "Função de pontuação selecionada disponível."))
                continue
            status = scoring_statuses.get(scoring_key, {})
            if status.get("available", False):
                checks.append(("ok", f"Pontuação {label}", "Função de pontuação selecionada disponível."))
            else:
                checks.append(("warn", f"Pontuação {label} desativada", status.get("reason", "Dependência opcional de pontuação ausente.")))

        vina_ok = bool(report.get("vina_functional", False)) if report else True
        checks.append(("ok" if vina_ok else "fail", "Executável Vina encontrado", "Execute o inicializador para instalar o Vina ou restaurar o fallback CLI incluído."))
        return checks

    def _bounds_overlap_box(self, bounds: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]) -> bool:
        """Return True when ligand coordinate bounds overlap the current search box."""
        center = (self.center_x.value(), self.center_y.value(), self.center_z.value())
        size = (self.size_x.value(), self.size_y.value(), self.size_z.value())
        for axis, axis_bounds in enumerate(bounds):
            box_min = center[axis] - size[axis] / 2
            box_max = center[axis] + size[axis] / 2
            if axis_bounds[1] < box_min or axis_bounds[0] > box_max:
                return False
        return True

    @staticmethod
    def _check_icon(status: str) -> str:
        """Return a compact status icon."""
        return {"ok": "[OK]", "warn": "[!]", "fail": "[X]"}.get(status, "[ ]")

    @staticmethod
    def _check_style(status: str) -> str:
        """Return stylesheet for checklist status rows."""
        colors = {"ok": "#1f6b3a", "warn": "#8a5a00", "fail": "#9b1c1c"}
        return f"text-align: left; color: {colors.get(status, '#2C2C2C')}; font-weight: 600; border: none;"

    def _build_atom_center_group(self) -> QGroupBox:
        """Build receptor atom selection controls for search-box center."""
        layout = QVBoxLayout(self.atom_center_group)
        control_row = QHBoxLayout()
        control_row.addWidget(self.atom_center_checkbox)
        control_row.addWidget(self.reload_atoms_button)
        control_row.addStretch()
        layout.addLayout(control_row)
        self.atom_tree.setColumnCount(4)
        self.atom_tree.setHeaderLabels(["Residue/Atom", "X", "Y", "Z"])
        self.atom_tree.setRootIsDecorated(True)
        self.atom_tree.setUniformRowHeights(True)
        self.atom_tree.setVisible(False)
        self.reload_atoms_button.setVisible(False)
        self.atom_status_label.setObjectName("label_muted")
        self.atom_status_label.setWordWrap(True)
        layout.addWidget(self.atom_status_label)
        layout.addWidget(self.atom_tree)
        return self.atom_center_group

    def _atom_center_toggled(self, checked: bool) -> None:
        """Toggle receptor atom center controls."""
        self.atom_tree.setVisible(checked)
        self.reload_atoms_button.setVisible(checked)
        if checked:
            self._load_receptor_atoms()

    def _setup_selection_changed(self) -> None:
        """Refresh receptor atoms when the receptor file changes."""
        if self.atom_center_checkbox.isChecked():
            self._load_receptor_atoms()

    def _load_receptor_atoms(self) -> None:
        """Populate the receptor residue/atom tree from the selected PDBQT."""
        self.atom_tree.clear()
        receptor_path = self.setup_provider.rigid_receptor_path() or self.setup_provider.receptor_path()
        if receptor_path is None or not receptor_path.exists():
            self.atom_status_label.setText("Selecione primeiro um arquivo PDBQT do receptor.")
            return

        atoms = pdbqt_receptor_atoms(receptor_path)
        if not atoms:
            self.atom_status_label.setText("Nenhum átomo do receptor pôde ser lido do arquivo PDBQT.")
            return

        residue_items: dict[tuple[str, str, str], QTreeWidgetItem] = {}
        for atom in atoms:
            residue_key = (atom["chain_id"], atom["residue_number"], atom["resname"])
            residue_item = residue_items.get(residue_key)
            if residue_item is None:
                residue_label = (
                    f"{atom['one_letter']} {atom['resname']} "
                    f"{atom['chain_id']}{atom['residue_number']}"
                ).strip()
                residue_item = QTreeWidgetItem([residue_label, "", "", ""])
                residue_items[residue_key] = residue_item
                self.atom_tree.addTopLevelItem(residue_item)
            atom_item = QTreeWidgetItem(
                [
                    atom["atom_name"],
                    f"{atom['x']:.3f}",
                    f"{atom['y']:.3f}",
                    f"{atom['z']:.3f}",
                ]
            )
            atom_item.setData(0, Qt.UserRole, atom)
            residue_item.addChild(atom_item)
        self.atom_tree.expandItem(self.atom_tree.topLevelItem(0))
        for column in range(self.atom_tree.columnCount()):
            self.atom_tree.resizeColumnToContents(column)
        self.atom_status_label.setText(
            f"Carregados {len(atoms)} átomos em {len(residue_items)} resíduos de {receptor_path.name}."
        )

    def _atom_tree_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Move the search-box center to the selected atom coordinates."""
        atom = item.data(0, Qt.UserRole)
        if not atom:
            return
        self.center_x.setValue(float(atom["x"]))
        self.center_y.setValue(float(atom["y"]))
        self.center_z.setValue(float(atom["z"]))
        self.atom_status_label.setText(
            f"Centro definido para {atom['resname']} {atom['chain_id']}{atom['residue_number']} "
            f"{atom['atom_name']} ({atom['x']:.3f}, {atom['y']:.3f}, {atom['z']:.3f})."
        )
        self.parameters_changed.emit(self.current_parameters())
        self.box_changed.emit(self.current_box())

    def _refresh_dependency_status(self) -> None:
        """Show a compact dependency readiness indicator in the docking panel."""
        report = EnvironmentManager(Path(__file__).resolve().parents[1]).cached_status_report()
        if not report:
            self.dependency_status_label.setText("Dependências: verificando - execute o inicializador se um pacote obrigatório estiver ausente.")
            self.dependency_status_label.setStyleSheet("color: #8a5a00; font-weight: 600;")
            return
        missing_required = [
            package["pip_name"]
            for package in report.get("packages", [])
            if package.get("required", True) and not package.get("installed", False)
        ]
        disabled_scorers = [
            status.get("label", key)
            for key, status in report.get("scoring_functions", {}).items()
            if not status.get("available", False)
        ]
        if not report.get("venv_ready") or missing_required or not report.get("vina_functional", False):
            self.dependency_status_label.setText("Dependências: vermelho - runtime obrigatório ausente. Use Corrigir agora na barra de status.")
            self.dependency_status_label.setStyleSheet("color: #9b1c1c; font-weight: 600;")
        elif disabled_scorers:
            self.dependency_status_label.setText(
                "Dependências: amarelo - docking principal pronto; pontuação desativada: " + ", ".join(disabled_scorers)
            )
            self.dependency_status_label.setStyleSheet("color: #8a5a00; font-weight: 600;")
        else:
            self.dependency_status_label.setText("Dependências: verde - docking e runtimes opcionais de pontuação prontos.")
            self.dependency_status_label.setStyleSheet("color: #1f6b3a; font-weight: 600;")

    def _set_parameter_explanations(self) -> None:
        """Attach short explanations to every AutoDock Vina parameter."""
        explanations = {
            "scoring_label": "Escolha uma ou mais funções de pontuação; cada método selecionado roda como validação separada.",
            "center_label": "Centro da caixa de busca; use coordenadas conhecidas do sítio ativo ou selecione um átomo do receptor abaixo.",
            "size_label": "Dimensões da caixa em Angstrom; caixas grandes são mais lentas e menos focadas.",
            "exhaustiveness": "Esforço de busca; valores maiores amostram mais poses e levam mais tempo.",
            "num_modes": "Número máximo de poses gravadas por ligante e função de pontuação.",
            "energy_range": "Mantém poses dentro desta janela de kcal/mol em relação à melhor pose.",
            "cpu_label": "Número de threads de CPU; 0 permite que o Vina escolha automaticamente.",
            "seed_label": "Semente aleatória usada quando a reprodutibilidade está habilitada.",
            "min_rmsd": "Separação mínima de poses usada para evitar poses quase duplicadas.",
            "output_dir": "Pasta onde poses, tabelas de resultados e relatórios serão gravados.",
        }
        for key, text in explanations.items():
            self.labels[key].setToolTip(text)

    def _apply_config_values(self, values: dict[str, str]) -> None:
        """Apply parsed config key/value pairs to controls."""
        if "scoring" in values:
            scoring_keys = [key.strip() for key in values["scoring"].split(",") if key.strip()]
            self.scoring_selector.set_selected_keys(scoring_keys)
        for key, widget in {
            "center_x": self.center_x,
            "center_y": self.center_y,
            "center_z": self.center_z,
            "size_x": self.size_x,
            "size_y": self.size_y,
            "size_z": self.size_z,
            "energy_range": self.energy_range,
            "min_rmsd": self.min_rmsd,
        }.items():
            if key in values:
                widget.setValue(float(values[key]))
        for key, widget in {
            "exhaustiveness": self.exhaustiveness,
            "num_modes": self.num_modes,
            "cpu": self.cpu,
            "seed": self.seed,
        }.items():
            if key in values:
                widget.setValue(int(float(values[key])))
        if "seed" in values and int(float(values["seed"])) != 0:
            self.fix_seed.setChecked(True)
        if "out" in values and values["out"]:
            self.output_edit.setText(str(Path(values["out"])))
            self.output_directory_changed.emit(Path(values["out"]))
        self.parameters_changed.emit(self.current_parameters())

    def _pick_output_directory(self) -> None:
        """Pick the output directory for docking results."""
        folder = QFileDialog.getExistingDirectory(self, I18n.get("select_output_dir", self.lang))
        if folder:
            output_directory = Path(folder)
            self.output_edit.setText(str(output_directory))
            self.output_directory_changed.emit(output_directory)
            self.parameters_changed.emit(self.current_parameters())

    def _worker_finished(self) -> None:
        """Re-enable execution controls after worker completion."""
        self.run_button.setEnabled(True)

    def _show_error(self, message: str) -> None:
        """Show a worker error dialog."""
        QMessageBox.critical(self, I18n.get("error_title", self.lang), message)

    def _output_row(self) -> QHBoxLayout:
        """Create output directory picker row."""
        row = QHBoxLayout()
        self.output_button.clicked.connect(self._pick_output_directory)
        row.addWidget(self.output_edit)
        row.addWidget(self.output_button)
        return row

    def _seed_row(self) -> QHBoxLayout:
        """Create seed controls row."""
        row = QHBoxLayout()
        row.addWidget(self.seed)
        row.addWidget(self.fix_seed)
        return row

    @staticmethod
    def _separator() -> QFrame:
        """Create a horizontal visual separator."""
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        return separator

    @staticmethod
    def _xyz_row(x_widget, y_widget, z_widget) -> QGridLayout:
        """Create a compact X/Y/Z spinbox row."""
        row = QGridLayout()
        for column, (label, widget) in enumerate((("X", x_widget), ("Y", y_widget), ("Z", z_widget))):
            axis_label = QLabel(label)
            axis_label.setObjectName("label_muted")
            row.addWidget(axis_label, 0, column * 2)
            row.addWidget(widget, 0, column * 2 + 1)
        return row

    @staticmethod
    def _double_spin(minimum: float, maximum: float, step: float, decimals: int, value: float) -> QDoubleSpinBox:
        """Create a configured QDoubleSpinBox."""
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setDecimals(decimals)
        spin.setValue(value)
        return spin

    @staticmethod
    def _spin(minimum: int, maximum: int, value: int) -> QSpinBox:
        """Create a configured QSpinBox."""
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        return spin


def _gnina_executable() -> Path | None:
    """Return a GNINA executable from PATH or the local tools directory."""
    path_value = shutil.which("gnina") or shutil.which("gnina.exe")
    if path_value:
        return Path(path_value)
    candidates = [
        Path(__file__).resolve().parents[1] / "tools" / "gnina" / "gnina.exe",
        Path.cwd() / "tools" / "gnina" / "gnina.exe",
    ]
    return next((candidate for candidate in candidates if candidate.exists() and candidate.is_file()), None)
