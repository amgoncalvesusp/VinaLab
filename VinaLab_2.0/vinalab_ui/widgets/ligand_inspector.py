"""User-facing element and scoring compatibility inspection for ligand PDBQT files."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from vinalab_core.prepare.element_router import ElementRoute, ElementRouter
from vinalab_core.prepare.pdbqt_validator import PdbqtValidator
from vinalab_core.scoring.registry import ScoringPlan, ScoringRegistry


class LigandInspector(QWidget):
    """Explains score compatibility without mutating the ligand file."""

    ligand_selected = Signal(object)
    route_selected = Signal(object)

    def __init__(
        self, project_root: str | Path | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.router = ElementRouter()
        self.validator = PdbqtValidator()
        self.scoring_registry = ScoringRegistry(project_root or Path.cwd())
        self.route: ElementRoute | None = None
        self.scoring_plan: ScoringPlan | None = None
        layout = QVBoxLayout(self)
        input_row = QHBoxLayout()
        self.path_input = QLineEdit(self)
        self.path_input.setObjectName("ligandInspectorPath")
        self.browse_button = QPushButton("Browse ligand…", self)
        self.browse_button.setObjectName("browseLigandInspector")
        input_row.addWidget(self.path_input)
        input_row.addWidget(self.browse_button)
        layout.addLayout(input_row)
        self.status = QLabel("Select a ligand PDBQT file to inspect elements.", self)
        self.status.setObjectName("ligandRouteStatus")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.browse_button.clicked.connect(self._browse)

    def inspect_path(self, path: str | Path) -> ElementRoute:
        ligand_path = Path(path)
        self.path_input.setText(str(ligand_path))
        content = ligand_path.read_text(encoding="utf-8", errors="replace")
        report = self.validator.validate_text(content)
        if not report.ok:
            raise ValueError(report.errors[0])
        route = self.router.inspect_pdbqt_text(content)
        self.route = route
        self.scoring_plan = self.scoring_registry.plan_for_elements(route.elements)
        if "B" in route.exotic_elements:
            xtb = self.scoring_plan.option("xtb_gfn2")
            availability = "available" if xtb.available else f"not configured ({xtb.reason})"
            self.status.setText(
                "Boron detected. AutoDock Vina scoring is disabled for this ligand; "
                f"use xTB/PM6 exotic rescoring with a compatible pose-generation plan. xTB is {availability}."
            )
        elif route.requires_exotic_scoring:
            self.status.setText(
                f"Exotic elements detected ({', '.join(sorted(route.exotic_elements))}). "
                "Use the exotic rescoring route."
            )
        else:
            self.status.setText(
                f"Elements: {', '.join(sorted(route.elements))}. Standard Vina scoring is compatible."
            )
        self.ligand_selected.emit(ligand_path)
        self.route_selected.emit(route)
        return route

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select ligand PDBQT", self.path_input.text(), "PDBQT files (*.pdbqt);;All files (*)"
        )
        if path:
            self.inspect_path(path)
