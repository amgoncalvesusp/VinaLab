"""Reference-ligand validation in the receptor coordinate frame."""

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from vinalab_ui.widgets.form_helpers import export_table, file_field


class ValidationPanel(QWidget):
    validate_requested = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)
        row, self.reference_input = file_field(self, "Reference with bond topology (*.sdf *.mol)")
        layout.addRow("Reference ligand", row)
        self.reference_input.setToolTip("Use SDF/MOL with known bond topology in the prepared receptor frame.")
        row, self.poses_input = file_field(self, "Docked poses (*.pdbqt *.sdf)")
        layout.addRow("Docked poses", row)
        self.poses_input.setToolTip("SDF poses or Meeko PDBQT retaining SMILES and atom-index mapping remarks.")
        self.frame_confirmed = QCheckBox("Reference and poses use the same receptor coordinate frame", self)
        layout.addRow(self.frame_confirmed)
        self.run_button = QPushButton("Calculate reference RMSD", self)
        layout.addRow(self.run_button)
        self.table = QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(["Pose", "Heavy-atom RMSD (A)", "Comparable", "Details"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addRow(self.table)
        self.export_button = QPushButton("Export validation CSV", self)
        self.export_button.setEnabled(False)
        layout.addRow(self.export_button)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        layout.addRow(self.status)
        self.run_button.clicked.connect(self._request)
        self.export_button.clicked.connect(self._export)
        self.reference_input.textChanged.connect(self._invalidate)
        self.poses_input.textChanged.connect(self._invalidate)

    def _invalidate(self):
        self.frame_confirmed.setChecked(False)
        self.table.setRowCount(0)
        self.export_button.setEnabled(False)
        self.status.clear()

    def _request(self):
        reference, poses = Path(self.reference_input.text()), Path(self.poses_input.text())
        if not reference.is_file() or not poses.is_file():
            self.status.setText("Select existing reference and pose files.")
        elif not self.frame_confirmed.isChecked():
            self.status.setText("Confirm a common receptor frame. Ligands are not independently superimposed.")
        else:
            self.validate_requested.emit(poses, reference)

    def show_rows(self, rows):
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(str(value)))
        self.export_button.setEnabled(bool(rows))
        self.status.setText("Reference comparison complete. No ligand superposition was applied.")

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export validation", "validation.csv", "CSV (*.csv)")
        if path:
            try:
                export_table(self.table, path)
                self.status.setText(f"Exported: {path}")
            except OSError as error:
                self.status.setText(str(error))
