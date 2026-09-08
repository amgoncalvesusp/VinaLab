# -*- coding: utf-8 -*-
"""Setup tab for receptor and ligand selection."""

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from core.file_utils import discover_pdbqt_files, is_pdbqt_file, validate_optional_pdbqt
from core.i18n import I18n
from core.scrolling import ScrollManager


class SetupTab(QWidget):
    """Collect receptor and ligand inputs for docking."""

    selection_changed = Signal()

    def __init__(self) -> None:
        """Create setup controls and validation labels."""
        super().__init__()
        self.lang = "pt"
        self.receptor_edit = QLineEdit()
        self.rigid_receptor_edit = QLineEdit()
        self.flex_receptor_edit = QLineEdit()
        self.fully_rigid_checkbox = QCheckBox()
        self.ligand_edit = QLineEdit()
        self._ligand_files: list[Path] = []
        self._ligand_folder: Path | None = None
        self.warning_label = QLabel()
        self.batch_count_label = QLabel()
        self.receptor_group = QGroupBox()
        self.ligand_group = QGroupBox()
        self.receptor_file_label = QLabel()
        self.rigid_receptor_label = QLabel()
        self.flex_receptor_label = QLabel()
        self.single_ligand_label = QLabel()
        self.batch_folder_label = QLabel()
        self.file_buttons: list[QPushButton] = []
        self.receptor_form = QFormLayout()
        for label in (
            self.warning_label,
            self.batch_count_label,
            self.receptor_file_label,
            self.rigid_receptor_label,
            self.flex_receptor_label,
            self.single_ligand_label,
            self.batch_folder_label,
        ):
            label.setWordWrap(True)
        self._build_ui()
        self._connect_signals()
        self.retranslate_ui(self.lang)
        self.validate_inputs()

    def receptor_path(self) -> Path | None:
        """Return the selected receptor PDBQT path."""
        return self._path_from_edit(self.receptor_edit)

    def rigid_receptor_path(self) -> Path | None:
        """Return the selected rigid receptor PDBQT path, if any."""
        return self._path_from_edit(self.rigid_receptor_edit)

    def flexible_receptor_path(self) -> Path | None:
        """Return the selected flexible receptor PDBQT path, if any."""
        return self._path_from_edit(self.flex_receptor_edit)

    def set_receptor_file(self, path: str) -> None:
        """Set the receptor field from an external conversion result."""
        self.receptor_edit.setText(str(Path(path)))
        self.validate_inputs()

    def set_ligand_file(self, path: str) -> None:
        """Use a single converted ligand."""
        self.set_ligand_files([path])

    def set_ligand_files(self, paths: list[str]) -> None:
        """Replace the selection with an ordered, unique list of files."""
        self._ligand_files = list(dict.fromkeys(Path(path) for path in paths))
        self._ligand_folder = None
        self.ligand_edit.setText("; ".join(str(path) for path in self._ligand_files))
        self.ligand_edit.setToolTip("\n".join(str(path) for path in self._ligand_files))
        self.validate_inputs()

    def set_ligand_folder(self, path: str) -> None:
        """Set the ligand batch folder from external conversion results."""
        self._ligand_files = []
        self._ligand_folder = Path(path)
        self.ligand_edit.setText(str(self._ligand_folder))
        self.ligand_edit.setToolTip(str(self._ligand_folder))
        self.validate_inputs()

    def ligand_paths(self) -> list[Path]:
        """Return selected ligand paths based on the active ligand mode."""
        if self._ligand_folder is not None:
            return discover_pdbqt_files(self._ligand_folder)
        return list(self._ligand_files)

    def validate_inputs(self) -> bool:
        """Validate selected setup paths and show inline warnings."""
        warnings: list[str] = []
        receptor = self.receptor_path()
        if not is_pdbqt_file(receptor):
            warnings.append(I18n.get("warn_receptor", self.lang))

        rigid = self.rigid_receptor_path()
        flex = self.flexible_receptor_path()
        if not validate_optional_pdbqt(rigid):
            warnings.append(I18n.get("warn_rigid", self.lang))
        if not validate_optional_pdbqt(flex):
            warnings.append(I18n.get("warn_flex", self.lang))

        discovered = self.ligand_paths()
        self.batch_count_label.setText(
            I18n.get("batch_count", self.lang).format(count=len(discovered))
        )
        if not discovered or not all(is_pdbqt_file(path) for path in discovered):
            warnings.append(I18n.get("warn_ligand", self.lang))
        names = [path.stem.casefold() for path in discovered]
        if len(names) != len(set(names)):
            warnings.append("Os ligantes precisam de nomes de arquivo distintos para evitar sobrescrever resultados."
                            if self.lang == "pt" else "Ligands need distinct filenames to avoid overwriting results.")

        self.warning_label.setText(" ".join(warnings))
        self.warning_label.setVisible(bool(warnings))
        self.selection_changed.emit()
        return not warnings

    def retranslate_ui(self, lang: str) -> None:
        """Retranslate setup tab controls."""
        self.lang = lang
        self.receptor_group.setTitle(I18n.get("setup_group", lang))
        self.ligand_group.setTitle(I18n.get("ligand_group", lang))
        self.ligand_group.setToolTip(
            "AutoDock Vina aceita apenas um ligante por arquivo PDBQT. "
            "No Modo Triagem, selecione uma pasta contendo arquivos .pdbqt (um por ligante); "
            "cada arquivo será processado em sequência."
            if lang == "pt"
            else "AutoDock Vina accepts only one ligand per PDBQT file. "
            "In Screening mode, select a folder containing .pdbqt files (one per ligand); "
            "each file is processed sequentially."
        )
        self.rigid_receptor_edit.setToolTip(I18n.get("setup_rigid_tooltip", lang))
        self.flex_receptor_edit.setToolTip(I18n.get("setup_flex_tooltip", lang))
        self.single_ligand_label.setText(
            "Selecione arquivos dos ligantes ou pasta de triagem" if lang == "pt"
            else "Select ligand files or a screening folder"
        )
        self.ligand_files_action.setText("Arquivos de ligantes…" if lang == "pt" else "Ligand files…")
        self.ligand_folder_action.setText("Pasta de triagem…" if lang == "pt" else "Screening folder…")
        for button in self.file_buttons:
            button.setText(I18n.get("browse_button", lang))
        self._refresh_receptor_form_labels()
        self.validate_inputs()

    def _build_ui(self) -> None:
        """Build the tab layout."""
        outer_layout = QVBoxLayout(self)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(self._build_receptor_group())
        layout.addWidget(self._build_ligand_group())
        self.warning_label.setObjectName("warningLabel")
        self.warning_label.setWordWrap(True)
        layout.addWidget(self.warning_label)
        layout.addStretch()
        outer_layout.addWidget(ScrollManager.wrap(content))

    def _build_receptor_group(self) -> QGroupBox:
        """Build receptor file picker controls."""
        self.receptor_form = QFormLayout(self.receptor_group)
        self.receptor_form.addRow(
            self.receptor_file_label,
            self._file_row(self.receptor_edit, self._pick_receptor),
        )
        self.receptor_form.addRow(self.fully_rigid_checkbox)
        self.receptor_form.addRow(
            self.rigid_receptor_label,
            self._file_row(self.rigid_receptor_edit, self._pick_rigid_receptor),
        )
        self.receptor_form.addRow(
            self.flex_receptor_label,
            self._file_row(self.flex_receptor_edit, self._pick_flexible_receptor),
        )
        self.fully_rigid_checkbox.toggled.connect(self._toggle_flex_visibility)
        self.rigid_receptor_edit.setToolTip(I18n.get("setup_rigid_tooltip", self.lang))
        self.flex_receptor_edit.setToolTip(I18n.get("setup_flex_tooltip", self.lang))
        self.rigid_receptor_label.setToolTip(I18n.get("setup_rigid_tooltip", self.lang))
        self.flex_receptor_label.setToolTip(I18n.get("setup_flex_tooltip", self.lang))
        return self.receptor_group

    def _toggle_flex_visibility(self, fully_rigid: bool) -> None:
        """Hide flexible-sidechain input when 'Usar receptor totalmente rígido' is checked."""
        self.flex_receptor_edit.setVisible(not fully_rigid)
        self.flex_receptor_label.setVisible(not fully_rigid)
        if fully_rigid:
            self.flex_receptor_edit.clear()
        self.validate_inputs()

    def _build_ligand_group(self) -> QGroupBox:
        """Build ligand mode and file picker controls."""
        layout = QVBoxLayout(self.ligand_group)
        layout.addWidget(self.single_ligand_label)
        self.ligand_edit.setReadOnly(True)
        self.ligand_menu = QMenu(self)
        self.ligand_files_action = self.ligand_menu.addAction("", self._pick_single_ligand)
        self.ligand_folder_action = self.ligand_menu.addAction("", self._pick_batch_folder)
        button = QPushButton()
        button.setMenu(self.ligand_menu)
        self.file_buttons.append(button)
        row = QHBoxLayout()
        row.addWidget(self.ligand_edit)
        row.addWidget(button)
        layout.addLayout(row)
        layout.addWidget(self.batch_count_label)
        return self.ligand_group

    def _file_row(self, edit: QLineEdit, handler) -> QHBoxLayout:
        """Create a read-only file picker row."""
        edit.setReadOnly(True)
        button = QPushButton()
        self.file_buttons.append(button)
        button.clicked.connect(handler)
        row = QHBoxLayout()
        row.addWidget(edit)
        row.addWidget(button)
        return row

    def _folder_row(self, edit: QLineEdit, handler) -> QHBoxLayout:
        """Create a read-only folder picker row."""
        return self._file_row(edit, handler)

    def _pick_receptor(self) -> None:
        """Pick the main receptor PDBQT file."""
        self._pick_file_into(self.receptor_edit)

    def _pick_rigid_receptor(self) -> None:
        """Pick the rigid receptor PDBQT file."""
        self._pick_file_into(self.rigid_receptor_edit)

    def _pick_flexible_receptor(self) -> None:
        """Pick the flexible sidechain PDBQT file."""
        self._pick_file_into(self.flex_receptor_edit)

    def _pick_single_ligand(self) -> None:
        """Pick a single ligand PDBQT file."""
        paths, _ = QFileDialog.getOpenFileNames(
            self, I18n.get("select_pdbqt", self.lang), "",
            I18n.get("pdbqt_filter", self.lang),
        )
        if paths:
            self.set_ligand_files(paths)

    def _pick_batch_folder(self) -> None:
        """Pick a ligand batch folder."""
        folder = QFileDialog.getExistingDirectory(
            self, I18n.get("select_ligand_folder", self.lang)
        )
        if folder:
            self.set_ligand_folder(folder)

    def _pick_file_into(self, edit: QLineEdit) -> None:
        """Pick a PDBQT file into a line edit."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            I18n.get("select_pdbqt", self.lang),
            "",
            I18n.get("pdbqt_filter", self.lang),
        )
        if file_name:
            edit.setText(str(Path(file_name)))
            self.validate_inputs()

    def _connect_signals(self) -> None:
        """Connect widgets to validation updates."""
        for edit in (
            self.receptor_edit,
            self.rigid_receptor_edit,
            self.flex_receptor_edit,
        ):
            edit.textChanged.connect(self.validate_inputs)

    def _refresh_receptor_form_labels(self) -> None:
        """Refresh receptor form labels."""
        self.receptor_file_label.setText(I18n.get("receptor_label", self.lang))
        self.rigid_receptor_label.setText(I18n.get("rigid_receptor", self.lang))
        self.flex_receptor_label.setText(I18n.get("flexible_receptor", self.lang))
        self.fully_rigid_checkbox.setText(
            "Usar receptor totalmente rígido"
            if self.lang == "pt"
            else "Use fully rigid receptor"
        )
        self.fully_rigid_checkbox.setToolTip(
            "Quando marcado, oculta o campo de cadeias laterais flexíveis e usa o receptor inteiro como rígido."
            if self.lang == "pt"
            else "When checked, hides the flexible sidechain input and uses the entire receptor as rigid."
        )

    @staticmethod
    def _path_from_edit(edit: QLineEdit) -> Path | None:
        """Convert a line edit value into a Path or None."""
        text = edit.text().strip()
        return Path(text) if text else None
