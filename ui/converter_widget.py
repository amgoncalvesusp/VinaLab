# -*- coding: utf-8 -*-
"""PDB/MOL2/PDBQT conversion panel for VinaLab."""

from pathlib import Path
import shutil

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.converter import ConversionResult, FileConverter
from core.i18n import I18n
from core.scrolling import ScrollManager


class ConversionWorker(QThread):
    """Run one or more file conversions off the GUI thread."""

    finished_signal = Signal(object)
    log_signal = Signal(str)

    def __init__(self, input_paths: list[Path], output_target: Path, molecule_type: str) -> None:
        """Initialize the worker with conversion paths and molecule type."""
        super().__init__()
        self.input_paths = list(input_paths)
        self.output_target = output_target
        self.molecule_type = molecule_type

    def run(self) -> None:
        """Execute all requested conversions and emit a list of results."""
        results: list[ConversionResult] = []
        output_is_folder = len(self.input_paths) > 1 or self.output_target.suffix.lower() != ".pdbqt"
        if output_is_folder:
            self.output_target.mkdir(parents=True, exist_ok=True)

        for input_path in self.input_paths:
            output_path = self._output_path_for(input_path, output_is_folder)
            self.log_signal.emit(f"Convertendo {input_path.name} -> {output_path.name}")
            result = self._convert_one(input_path, output_path)
            if result.log:
                self.log_signal.emit(result.log)
            if result.errors:
                self.log_signal.emit(result.errors)
            results.append(result)
        self.finished_signal.emit(results)

    def _output_path_for(self, input_path: Path, output_is_folder: bool) -> Path:
        """Return the output path for one conversion."""
        if output_is_folder:
            return self.output_target / input_path.with_suffix(".pdbqt").name
        return self.output_target

    def _convert_one(self, input_path: Path, output_path: Path) -> ConversionResult:
        """Convert one file to PDBQT using the selected molecule type."""
        detected = FileConverter._detect_format(input_path)
        if detected == "pdbqt":
            if input_path.resolve() != output_path.resolve():
                output_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(input_path, output_path)
                return ConversionResult(True, output_path, "Arquivo já está em PDBQT; copiado para a saída.", "")
            return ConversionResult(True, input_path, "Arquivo já está em PDBQT; conversão não necessária.", "")
        if detected == "unknown":
            return ConversionResult(False, output_path, "", "Formato de arquivo não reconhecido.")
        if self.molecule_type == "receptor":
            if detected == "pdb":
                return FileConverter.convert_pdb_to_pdbqt_receptor(input_path, output_path)
            if detected == "mol2":
                return FileConverter.convert_mol2_to_pdbqt_receptor(input_path, output_path)
            return ConversionResult(False, output_path, "", "A conversão de receptor aceita entrada PDB, MOL2 ou PDBQT.")
        if detected == "pdb":
            return FileConverter.convert_pdb_to_pdbqt_ligand(input_path, output_path)
        if detected == "mol2":
            return FileConverter.convert_mol2_to_pdbqt_ligand(input_path, output_path)
        return ConversionResult(False, output_path, "", "Formato de arquivo não reconhecido.")


class ConverterWidget(QWidget):
    """Standalone molecular file conversion panel."""

    conversion_ready = Signal(str, str)

    def __init__(self) -> None:
        """Create conversion controls and dependency status indicators."""
        super().__init__()
        self.lang = "pt"
        self.worker: ConversionWorker | None = None
        self.input_paths: list[Path] = []
        self.last_results: list[ConversionResult] = []
        self.last_output_target: Path | None = None
        self.title_label = QLabel()
        self.subtitle_label = QLabel()
        self.note_label = QLabel()
        self.input_label = QLabel()
        self.output_label = QLabel()
        self.type_label = QLabel()
        self.input_edit = QLineEdit()
        self.output_edit = QLineEdit()
        self.input_button = QPushButton()
        self.output_button = QPushButton()
        self.type_combo = QComboBox()
        self.dep_label = QLabel()
        self.dep_row = QHBoxLayout()
        self.convert_button = QPushButton()
        self.log_console = QTextEdit()
        self.result_label = QLabel()
        self.use_button = QPushButton()
        self._build_ui()
        self._connect_signals()
        self.retranslate_ui(self.lang)
        self.refresh_dependencies()

    def retranslate_ui(self, lang: str) -> None:
        """Retranslate converter panel labels."""
        self.lang = lang
        self.title_label.setText(I18n.get("converter_title", lang))
        self.subtitle_label.setText(I18n.get("converter_subtitle", lang))
        self.note_label.setText(I18n.get("converter_pdbqt_note", lang))
        self.input_label.setText(I18n.get("input_file", lang))
        self.output_label.setText(I18n.get("output_folder" if self._is_batch_selection() else "output_file", lang))
        self.type_label.setText(I18n.get("molecule_type", lang))
        self.input_button.setText(I18n.get("browse_button", lang))
        self.output_button.setText(I18n.get("browse_button", lang))
        self.convert_button.setText(I18n.get("convert_button", lang))
        self.dep_label.setText(I18n.get("dep_status_title", lang))
        self.type_combo.setItemText(0, I18n.get("mol_type_ligand", lang))
        self.type_combo.setItemText(1, I18n.get("mol_type_receptor", lang))
        self._refresh_use_button()
        self.refresh_dependencies()

    def refresh_dependencies(self) -> None:
        """Refresh colored dependency status indicators."""
        while self.dep_row.count() > 1:
            item = self.dep_row.takeAt(1)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        deps = FileConverter.check_dependencies()
        for key, tooltip_key in (("rdkit", "tip_rdkit"), ("meeko", "tip_rdkit"), ("obabel_cli", "tip_openbabel")):
            color = "#27AE60" if deps.get(key) else "#C0392B"
            dot = QLabel(f"● {key}")
            dot.setStyleSheet(f"color: {color};")
            dot.setToolTip(I18n.get(tooltip_key, self.lang))
            self.dep_row.addWidget(dot)
        self.dep_row.addStretch()

    def start_conversion(self) -> None:
        """Start conversion in a background thread."""
        if not self.input_paths:
            self._show_failure(I18n.get("conv_no_input", self.lang))
            return
        if self._current_molecule_type() == "receptor" and len(self.input_paths) > 1:
            self._show_failure(I18n.get("conv_receptor_single", self.lang))
            return

        output_target = self._current_output_target()
        molecule_type = self._current_molecule_type()
        self.result_label.clear()
        self.use_button.hide()
        self.log_console.append(f"{I18n.get('convert_button', self.lang)}: {len(self.input_paths)} arquivo(s)")
        self.convert_button.setEnabled(False)
        self.worker = ConversionWorker(self.input_paths, output_target, molecule_type)
        self.worker.log_signal.connect(self.log_console.append)
        self.worker.finished_signal.connect(self._conversion_finished)
        self.worker.start()

    def _build_ui(self) -> None:
        """Build the converter layout."""
        outer_layout = QVBoxLayout(self)
        content = QWidget()
        layout = QVBoxLayout(content)
        self.title_label.setObjectName("label_section_title")
        self.subtitle_label.setWordWrap(True)
        self.note_label.setObjectName("label_warning")
        self.note_label.setWordWrap(True)
        self.input_edit.setReadOnly(True)
        self.output_edit.setReadOnly(True)
        self.log_console.setReadOnly(True)
        self.log_console.setObjectName("log_console")
        self.result_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.note_label)
        layout.addLayout(self._file_row(self.input_label, self.input_edit, self.input_button))
        type_row = QHBoxLayout()
        self.type_combo.addItems(["", ""])
        type_row.addWidget(self.type_label)
        type_row.addWidget(self.type_combo)
        layout.addLayout(type_row)
        layout.addLayout(self._file_row(self.output_label, self.output_edit, self.output_button))
        self.dep_row.addWidget(self.dep_label)
        layout.addLayout(self.dep_row)
        layout.addWidget(self.convert_button)
        layout.addWidget(self.log_console)
        layout.addWidget(self.result_label)
        layout.addWidget(self.use_button)
        self.use_button.hide()
        layout.addStretch()
        outer_layout.addWidget(ScrollManager.wrap(content))

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        self.input_button.clicked.connect(self._pick_input)
        self.output_button.clicked.connect(self._pick_output)
        self.type_combo.currentIndexChanged.connect(lambda *_: self._type_changed())
        self.convert_button.clicked.connect(self.start_conversion)
        self.use_button.clicked.connect(self._emit_current_result)

    def _pick_input(self) -> None:
        """Pick one or more molecular input files; show detected formats."""
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            I18n.get("select_input_files", self.lang),
            "",
            "Estruturas moleculares (*.pdbqt *.mol2 *.sdf *.mol *.pdb);;"
            "PDBQT (*.pdbqt);;MOL2 (*.mol2);;SDF (*.sdf);;MOL (*.mol);;PDB (*.pdb);;"
            "Todos os arquivos (*)",
        )
        if file_names:
            self.input_paths = [Path(file_name) for file_name in file_names]
            self.input_edit.setText(self._input_display_text())
            self._suggest_output()
            self.last_results = []
            self.use_button.hide()
            detected = ", ".join(
                f"{path.name} → {FileConverter._detect_format(path).upper()}"
                for path in self.input_paths
            )
            self.log_console.append(f"Formato(s) detectado(s): {detected}")

    def _pick_output(self) -> None:
        """Pick an output PDBQT file or output folder."""
        if self._is_batch_selection():
            folder = QFileDialog.getExistingDirectory(self, I18n.get("select_output_folder", self.lang))
            if folder:
                self.output_edit.setText(str(Path(folder)))
            return
        file_name, _ = QFileDialog.getSaveFileName(self, I18n.get("output_file", self.lang), "", "PDBQT (*.pdbqt)")
        if file_name:
            self.output_edit.setText(str(Path(file_name)))

    def _suggest_output(self) -> None:
        """Suggest a PDBQT output file or conversion output folder."""
        if not self.input_paths:
            return
        if self._is_batch_selection():
            output_folder = self.input_paths[0].parent / "pdbqt_converted"
            self.output_edit.setText(str(output_folder))
        else:
            self.output_edit.setText(str(self.input_paths[0].with_suffix(".pdbqt")))
        self.output_label.setText(I18n.get("output_folder" if self._is_batch_selection() else "output_file", self.lang))

    def _conversion_finished(self, results: list[ConversionResult]) -> None:
        """Handle conversion completion in the GUI thread."""
        self.convert_button.setEnabled(True)
        self.last_results = list(results)
        self.last_output_target = self._current_output_target()
        ok_results = [result for result in results if result.success]
        failed_results = [result for result in results if not result.success]
        if failed_results:
            self.result_label.setStyleSheet("color: #f39c12;" if ok_results else "color: #C0392B;")
            self.result_label.setText(
                I18n.get("conv_batch_partial", self.lang).format(ok=len(ok_results), total=len(results))
            )
        elif self._is_batch_selection():
            self.result_label.setStyleSheet("color: #27AE60;")
            self.result_label.setText(I18n.get("conv_batch_success", self.lang).format(count=len(ok_results)))
        elif ok_results:
            self.result_label.setStyleSheet("color: #27AE60;")
            self.result_label.setText(f"{I18n.get('conv_success', self.lang)}: {ok_results[0].output_path}")
        else:
            self._show_failure(I18n.get("conv_failure", self.lang))
            return
        self._refresh_use_button()
        if ok_results and not (self._current_molecule_type() == "receptor" and len(ok_results) != 1):
            self.use_button.show()

    def _emit_current_result(self) -> None:
        """Emit converted file or folder path and molecule type."""
        ok_results = [result for result in self.last_results if result.success]
        if not ok_results:
            return
        if self._current_molecule_type() == "receptor":
            self.conversion_ready.emit(str(ok_results[0].output_path), "receptor")
        elif self._is_batch_selection():
            self.conversion_ready.emit(str(self._current_output_target()), "ligand_batch")
        else:
            self.conversion_ready.emit(str(ok_results[0].output_path), "ligand")

    def _refresh_use_button(self) -> None:
        """Refresh the use-in-setup button label."""
        if self._current_molecule_type() == "receptor":
            self.use_button.setText(I18n.get("use_as_receptor", self.lang))
        elif self._is_batch_selection():
            self.use_button.setText(I18n.get("use_as_ligand_batch", self.lang))
        else:
            self.use_button.setText(I18n.get("use_as_ligand", self.lang))

    def _type_changed(self) -> None:
        """Refresh output suggestions when molecule type changes."""
        self._refresh_use_button()
        self._suggest_output()

    def _current_output_target(self) -> Path:
        """Return the selected output target, falling back to a suggested target."""
        text = self.output_edit.text().strip()
        if text:
            return Path(text)
        if self._is_batch_selection():
            return self.input_paths[0].parent / "pdbqt_converted"
        return self.input_paths[0].with_suffix(".pdbqt")

    def _input_display_text(self) -> str:
        """Return compact text for the selected input files."""
        if len(self.input_paths) == 1:
            return str(self.input_paths[0])
        return I18n.get("selected_files", self.lang).format(count=len(self.input_paths))

    def _show_failure(self, message: str) -> None:
        """Show a conversion failure message."""
        self.result_label.setStyleSheet("color: #C0392B;")
        self.result_label.setText(f"{I18n.get('conv_failure', self.lang)}: {message}")
        self.use_button.hide()

    def _is_batch_selection(self) -> bool:
        """Return True when multiple input files are selected."""
        return len(self.input_paths) > 1

    def _current_molecule_type(self) -> str:
        """Return the selected molecule type key."""
        return "receptor" if self.type_combo.currentIndex() == 1 else "ligand"

    @staticmethod
    def _file_row(label: QLabel, edit: QLineEdit, button: QPushButton) -> QHBoxLayout:
        """Create a file picker row."""
        row = QHBoxLayout()
        row.addWidget(label)
        row.addWidget(edit)
        row.addWidget(button)
        return row
