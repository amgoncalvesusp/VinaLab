"""Table presentation for parsed Vina docking poses."""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vinalab_core.docking.vina_results import VinaPoseResult
from vinalab_ui.widgets.form_helpers import export_table


class ResultsPanel(QWidget):
    """Displays Vina result rows in a deterministic, export-friendly order."""

    pymol_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 4, self)
        self.table.setObjectName("resultsTable")
        self.table.setHorizontalHeaderLabels(["Mode", "Affinity (kcal/mol)", "RMSD l.b. (Å)", "RMSD u.b. (Å)"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        buttons = QHBoxLayout()
        self.export_button = QPushButton("Export scores CSV", self)
        self.save_poses_button = QPushButton("Export poses PDBQT", self)
        self.pymol_button = QPushButton("Open in PyMOL", self)
        for button in (self.export_button, self.save_poses_button, self.pymol_button):
            button.setEnabled(False)
            buttons.addWidget(button)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.output_path = None
        self.export_button.clicked.connect(self._export_csv)
        self.save_poses_button.clicked.connect(self._export_poses)
        self.pymol_button.clicked.connect(self.pymol_requested)

    def show_poses(self, poses: Iterable[VinaPoseResult]) -> None:
        rows = tuple(poses)
        self.table.setRowCount(len(rows))
        for row_index, pose in enumerate(rows):
            values = (str(pose.mode), f"{pose.affinity:.3f}", f"{pose.rmsd_lb:.3f}", f"{pose.rmsd_ub:.3f}")
            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))
        self.export_button.setEnabled(bool(rows))

    def set_output(self, path, *, pymol_available=False):
        self.output_path = Path(path) if path else None
        available = self.output_path is not None and self.output_path.is_file()
        self.save_poses_button.setEnabled(available)
        self.pymol_button.setEnabled(available and pymol_available)
        self.pymol_button.setToolTip("Open saved artifacts" if pymol_available else "PyMOL was not found on PATH")
        self.status.setText(str(path) if available else "No saved pose file for this run.")

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export scores", "scores.csv", "CSV (*.csv)")
        if path:
            try:
                export_table(self.table, path)
                self.status.setText(f"Exported: {path}")
            except OSError as error:
                self.status.setText(str(error))

    def _export_poses(self):
        if self.output_path is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export poses", "poses.pdbqt", "PDBQT (*.pdbqt)")
        if path:
            try:
                if Path(path).resolve() == self.output_path.resolve():
                    raise ValueError("Choose a destination outside the original run artifact.")
                shutil.copyfile(self.output_path, path)
                self.status.setText(f"Exported: {path}")
            except (OSError, ValueError) as error:
                self.status.setText(str(error))
