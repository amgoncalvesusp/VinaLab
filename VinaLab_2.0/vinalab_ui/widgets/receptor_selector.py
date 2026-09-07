"""Receptor PDBQT selection for the VinaLab 2.0 workflow."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from vinalab_core.prepare.pdbqt_validator import PdbqtValidator
from vinalab_ui.widgets.conversion_panel import ConversionPanel


class ReceptorSelector(QWidget):
    """Selects a receptor PDBQT and exposes the exact path to downstream panels."""

    receptor_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.validator = PdbqtValidator()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select a prepared receptor PDBQT file.", self))
        input_row = QHBoxLayout()
        self.path_input = QLineEdit(self)
        self.path_input.setObjectName("receptorSelectorPath")
        self.browse_button = QPushButton("Browse receptor…", self)
        self.browse_button.setObjectName("browseReceptorSelector")
        input_row.addWidget(self.path_input)
        input_row.addWidget(self.browse_button)
        layout.addLayout(input_row)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.conversion = ConversionPanel("receptor", self)
        layout.addWidget(self.conversion)
        layout.addStretch()
        self.path_input.editingFinished.connect(lambda: self._select_safely(self.path_input.text()))
        self.browse_button.clicked.connect(self._browse)

    def select_path(self, path: str | Path) -> None:
        receptor_path = Path(path)
        if not receptor_path.is_file():
            raise FileNotFoundError(receptor_path)
        report = self.validator.validate_text(receptor_path.read_text(encoding="utf-8", errors="replace"))
        if not report.ok:
            raise ValueError(report.errors[0])
        self.path_input.setText(str(receptor_path))
        self.receptor_selected.emit(receptor_path)
        self.status.setText("Prepared receptor selected.")

    def _select_safely(self, path):
        try:
            self.select_path(path)
        except (OSError, UnicodeError, ValueError) as error:
            self.status.setText(f"Receptor not loaded: {error}")

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select receptor PDBQT", self.path_input.text(), "PDBQT files (*.pdbqt);;All files (*)"
        )
        if path:
            self.path_input.setText(path)
            self._select_safely(path)
