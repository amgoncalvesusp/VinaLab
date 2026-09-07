"""UI for scorer recommendation, compatibility, and availability."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vinalab_core.scoring.registry import ScoringPlan
from vinalab_ui.widgets.form_helpers import file_field


class ScoringPanel(QWidget):
    """Displays a plan without silently enabling unavailable or incompatible scorers."""

    score_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.recommendation = QLabel("Inspect a ligand to choose a scoring plan.", self)
        self.recommendation.setObjectName("scoringRecommendation")
        self.recommendation.setWordWrap(True)
        self.table = QTableWidget(0, 4, self)
        self.table.setObjectName("scoringTable")
        self.table.setHorizontalHeaderLabels(["Scorer", "Compatible", "Available", "Details"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMaximumHeight(175)
        layout.addWidget(self.recommendation)
        layout.addWidget(self.table)
        form = QFormLayout()
        self.method_input = QComboBox(self)
        self.method_input.addItem("GFN2-xTB / ALPB water", "gfn2")
        self.method_input.addItem("GFN-FF / ALPB water", "gfnff")
        form.addRow("Interaction method", self.method_input)
        row, self.receptor_input = file_field(self, "Prepared receptor/pocket (*.xyz)")
        form.addRow("Prepared receptor / pocket XYZ", row)
        row, self.ligand_input = file_field(self, "Prepared ligand pose (*.xyz)")
        form.addRow("Prepared ligand pose XYZ", row)
        self.charge_receptor = self._spin(-100, 100)
        self.charge_ligand = self._spin(-100, 100)
        self.uhf_receptor = self._spin(0, 100)
        self.uhf_ligand = self._spin(0, 100)
        self.uhf_complex = self._spin(0, 100)
        self.cpu_input = self._spin(1, max(1, os.cpu_count() or 1))
        for label, entry in (("Receptor charge", self.charge_receptor),
                             ("Ligand charge", self.charge_ligand),
                             ("Receptor unpaired electrons", self.uhf_receptor),
                             ("Ligand unpaired electrons", self.uhf_ligand),
                             ("Complex unpaired electrons", self.uhf_complex),
                             ("CPU threads", self.cpu_input)):
            form.addRow(label, entry)
        self.prepared_confirmed = QCheckBox("Prepared noncovalent fragments; complete hydrogens; same frame", self)
        form.addRow(self.prepared_confirmed)
        self.run_button = QPushButton("Calculate frozen interaction energy", self)
        form.addRow(self.run_button)
        layout.addLayout(form)
        self.result_label = QLabel(self)
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addStretch()
        self.run_button.clicked.connect(self._request)
        for entry in (self.receptor_input, self.ligand_input):
            entry.textChanged.connect(self._invalidate)
        self.method_input.currentIndexChanged.connect(self._invalidate)
        for entry in (self.charge_receptor, self.charge_ligand, self.uhf_receptor,
                      self.uhf_ligand, self.uhf_complex, self.cpu_input):
            entry.valueChanged.connect(self._invalidate)

    def _invalidate(self):
        self.prepared_confirmed.setChecked(False)
        self.result_label.clear()
        self.status.clear()

    def _spin(self, minimum, maximum):
        spin = QSpinBox(self)
        spin.setRange(minimum, maximum)
        return spin

    def _request(self):
        receptor, ligand = Path(self.receptor_input.text()), Path(self.ligand_input.text())
        if not receptor.is_file() or not ligand.is_file():
            self.status.setText("Select both prepared XYZ fragment files.")
        elif not self.prepared_confirmed.isChecked():
            self.status.setText("Confirm fragment preparation. PDBQT does not contain all quantum-chemistry hydrogens.")
        else:
            self.score_requested.emit({
                "receptor_xyz": receptor, "ligand_xyz": ligand,
                "method": self.method_input.currentData(),
                "charge_receptor": self.charge_receptor.value(),
                "charge_ligand": self.charge_ligand.value(),
                "uhf_receptor": self.uhf_receptor.value(),
                "uhf_ligand": self.uhf_ligand.value(),
                "uhf_complex": self.uhf_complex.value(),
                "cpu_threads": self.cpu_input.value(),
            })

    def show_result(self, result, path):
        from dataclasses import asdict
        self.show_saved_result(asdict(result), path)

    def show_saved_result(self, result, path):
        self.result_label.setText(f"Frozen interaction energy: {result['interaction_kcal_per_mol']:.6f} kcal/mol\n"
                                 "E(complex) - E(receptor) - E(ligand); not binding free energy.")
        self.status.setText(f"Components, protocol and provenance saved: {path}")

    def show_plan(self, plan: ScoringPlan) -> None:
        recommended = plan.option(plan.recommended_key)
        availability = "available" if recommended.available else f"not configured: {recommended.reason}"
        self.recommendation.setText(
            f"Recommended scorer: {recommended.label} ({availability})."
        )
        self.table.setRowCount(len(plan.options))
        for row_index, option in enumerate(plan.options):
            values = (
                option.label,
                "Yes" if option.compatible else "No",
                "Yes" if option.available else "No",
                option.reason,
            )
            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))
