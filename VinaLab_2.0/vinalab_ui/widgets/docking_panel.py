"""Input and execution controls for a Vina docking run."""

from __future__ import annotations

from pathlib import Path
import os
from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
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
from vinalab_core.prepare.element_router import ElementRoute


@dataclass(frozen=True, slots=True)
class DockingRequest:
    receptor: Path
    ligand: Path
    search_box: SearchBox
    cpu_threads: int
    exhaustiveness: int
    seed: int


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
        self.status = QLabel(self)
        self.status.setObjectName("dockingValidation")
        layout.addRow("Receptor PDBQT", self._path_row(self.receptor_input, self.receptor_browse_button))
        layout.addRow("Ligand PDBQT", self._path_row(self.ligand_input, self.ligand_browse_button))
        layout.addRow("CPU threads", self.cpu_input)
        layout.addRow("Exhaustiveness", self.exhaustiveness_input)
        layout.addRow("Seed", self.seed_input)
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

    def set_search_box(self, search_box: SearchBox) -> None:
        self.search_box = search_box
        self._validate()

    def set_element_route(self, route: ElementRoute) -> None:
        self.element_route = route
        self._validate()

    def _validate(self) -> None:
        receptor = Path(self.receptor_input.text())
        ligand = Path(self.ligand_input.text())
        if not self.vina_available:
            self.validation_message = "Vina is not available; open Diagnostics for details"
        elif self.element_route and self.element_route.requires_exotic_scoring:
            elements = ", ".join(sorted(self.element_route.exotic_elements))
            prefix = "Boron" if "B" in self.element_route.exotic_elements else "Exotic elements"
            self.validation_message = (
                f"{prefix} ({elements}) requires an exotic pose-generation/scoring route; "
                "Vina is blocked for this ligand"
            )
        elif not receptor.is_file():
            self.validation_message = "Select an existing receptor PDBQT file"
        elif not ligand.is_file():
            self.validation_message = "Select an existing ligand PDBQT file"
        else:
            self.validation_message = "Ready to run Vina"
        self.run_button.setEnabled(self.validation_message == "Ready to run Vina")
        self.status.setText(self.validation_message)

    def _request_run(self) -> None:
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
            )
        )
    run_requested = Signal(object)
