"""Table presentation for parsed Vina docking poses."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from vinalab_core.docking.vina_results import VinaPoseResult


class ResultsPanel(QWidget):
    """Displays Vina result rows in a deterministic, export-friendly order."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 4, self)
        self.table.setObjectName("resultsTable")
        self.table.setHorizontalHeaderLabels(["Mode", "Affinity (kcal/mol)", "RMSD l.b. (Å)", "RMSD u.b. (Å)"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def show_poses(self, poses: Iterable[VinaPoseResult]) -> None:
        rows = tuple(poses)
        self.table.setRowCount(len(rows))
        for row_index, pose in enumerate(rows):
            values = (str(pose.mode), f"{pose.affinity:.3f}", f"{pose.rmsd_lb:.3f}", f"{pose.rmsd_ub:.3f}")
            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))
