"""Input and execution controls for a Vina docking run."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from vinalab_core.docking.search_box import SearchBox
from vinalab_core.prepare.element_router import ElementRoute, ElementRouter
from vinalab_core.prepare.pdbqt_validator import PdbqtValidator


@dataclass(frozen=True, slots=True)
class DockingRequest:
    receptor: Path
    ligand: Path
    search_box: SearchBox
    cpu_threads: int
    exhaustiveness: int
    seed: int
    scoring: str = "vina"
    num_modes: int = 9


class DockingPanel(QWidget):
    """Collects the minimum validated inputs for a reproducible Vina CPU run."""

    def __init__(
        self, search_box: SearchBox, *, vina_available: bool, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.search_box = search_box
        self.element_route: ElementRoute | None = None
        self.vina_available = vina_available
        self.validation_message = ""
        self.busy = False
        layout = QFormLayout(self)
        self.receptor_input = QLineEdit(self)
        self.receptor_input.setObjectName("receptorPath")
        self.receptor_browse_button = QPushButton("Browse…", self)
        self.receptor_browse_button.setObjectName("browseReceptor")
        self.ligand_input = QLineEdit(self)
        self.ligand_input.setObjectName("ligandPath")
        self.ligand_browse_button = QPushButton("Browse…", self)
        self.ligand_browse_button.setObjectName("browseLigand")
        self.run_button = QPushButton("Run Vina", self)
        self.run_button.setObjectName("runDocking")
        self.cpu_input = QSpinBox(self)
        self.cpu_input.setObjectName("cpuThreads")
        self.cpu_input.setRange(1, max(1, os.cpu_count() or 1))
        self.cpu_input.setValue(max(1, (os.cpu_count() or 2) - 1))
        self.exhaustiveness_input = QSpinBox(self)
        self.exhaustiveness_input.setObjectName("exhaustiveness")
        self.exhaustiveness_input.setRange(1, 128)
        self.exhaustiveness_input.setValue(8)
        self.seed_input = QSpinBox(self)
        self.seed_input.setObjectName("seed")
        self.seed_input.setRange(0, 2_147_483_647)
        self.seed_input.setValue(0)
        self.seed_input.setToolTip("0 lets Vina choose a random seed. Use a positive seed to repeat a run.")
        self.exhaustiveness_input.setToolTip("Search effort: larger values increase runtime and sampling.")
        self.cpu_input.setToolTip("Maximum CPU threads passed to Vina.")
        self.scoring_input = QComboBox(self)
        self.scoring_input.addItems(["Vina", "Vinardo"])
        self.modes_input = QSpinBox(self)
        self.modes_input.setRange(1, 100)
        self.modes_input.setValue(9)
        self.modes_input.setToolTip("Maximum output poses; Vina may find fewer distinct modes.")
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        self.status.setObjectName("dockingValidation")
        layout.addRow("Receptor PDBQT", self._path_row(self.receptor_input, self.receptor_browse_button))
        layout.addRow("Ligand PDBQT", self._path_row(self.ligand_input, self.ligand_browse_button))
        layout.addRow("CPU threads", self.cpu_input)
        layout.addRow("Exhaustiveness", self.exhaustiveness_input)
        layout.addRow("Seed", self.seed_input)
        layout.addRow("Scoring function", self.scoring_input)
        layout.addRow("Maximum poses", self.modes_input)
        layout.addRow(self.run_button)
        layout.addRow("Run status", self.status)
        self.receptor_input.textChanged.connect(self._validate)
        self.ligand_input.textChanged.connect(self._validate)
        self.receptor_browse_button.clicked.connect(lambda: self._browse_into(self.receptor_input, "Select receptor PDBQT"))
        self.ligand_browse_button.clicked.connect(lambda: self._browse_into(self.ligand_input, "Select ligand PDBQT"))
        self.run_button.clicked.connect(self._request_run)
        self._validate()

    def set_inputs(self, receptor: str | Path, ligand: str | Path) -> None:
        self.receptor_input.setText(str(receptor))
        self.ligand_input.setText(str(ligand))

    def _path_row(self, path_input: QLineEdit, browse_button: QPushButton) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(path_input)
        layout.addWidget(browse_button)
        return container

    def _browse_into(self, path_input: QLineEdit, title: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, title, path_input.text(), "PDBQT files (*.pdbqt);;All files (*)")
        if path:
            path_input.setText(path)
            path_input.editingFinished.emit()

    def set_search_box(self, search_box: SearchBox) -> None:
        self.search_box = search_box
        self._validate()

    def set_element_route(self, route: ElementRoute) -> None:
        # Always inspect the selected file; an inspector's cached route may be stale.
        self._validate()

    def _validate(self) -> None:
        self.validation_message = self._input_error() or "Ready to run Vina"
        self.run_button.setEnabled(not self.busy and self.validation_message == "Ready to run Vina")
        if not self.busy:
            self.status.setText(self.validation_message)

    def _input_error(self) -> str:
        receptor = Path(self.receptor_input.text())
        ligand = Path(self.ligand_input.text())
        if not self.vina_available:
            return "Vina is not available; open Diagnostics for details"
        self.element_route = None
        if ligand.is_file():
            try:
                self.element_route = ElementRouter().inspect_pdbqt_text(ligand.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, ValueError) as error:
                return f"Cannot read ligand: {error}"
        if self.element_route and self.element_route.requires_exotic_scoring:
            elements = ", ".join(sorted(self.element_route.exotic_elements))
            prefix = "Boron" if "B" in self.element_route.exotic_elements else "Exotic elements"
            return (
                f"{prefix} ({elements}) requires an exotic pose-generation/scoring route; "
                "Vina is blocked for this ligand"
            )
        for label, path in (("receptor", receptor), ("ligand", ligand)):
            if not path.is_file():
                return f"Select an existing {label} PDBQT file"
            try:
                report = PdbqtValidator().validate_text(path.read_text(encoding="utf-8"))
                if not report.ok:
                    return f"Invalid {label}: {report.errors[0]}"
            except (OSError, UnicodeError) as error:
                return f"Cannot read {label}: {error}"
        return ""

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        for widget in (self.receptor_input, self.ligand_input, self.receptor_browse_button,
                       self.ligand_browse_button, self.cpu_input, self.exhaustiveness_input,
                       self.seed_input, self.scoring_input, self.modes_input):
            widget.setEnabled(not busy)
        message = self.status.text()
        self._validate()
        self.status.setText(message)

    def _request_run(self) -> None:
        self._validate()
        if not self.run_button.isEnabled():
            return
        self.run_requested.emit(
            DockingRequest(
                receptor=Path(self.receptor_input.text()),
                ligand=Path(self.ligand_input.text()),
                search_box=self.search_box,
                cpu_threads=self.cpu_input.value(),
                exhaustiveness=self.exhaustiveness_input.value(),
                seed=self.seed_input.value(),
                scoring=self.scoring_input.currentText().lower(),
                num_modes=self.modes_input.value(),
            )
        )
    run_requested = Signal(object)
