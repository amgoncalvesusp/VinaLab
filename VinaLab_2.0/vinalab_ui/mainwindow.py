"""The VinaLab 2.0 application window."""

from pathlib import Path
from typing import Protocol
import hashlib

from PySide6.QtWidgets import QLabel, QMainWindow, QTabWidget

from vinalab_core.docking.docking_service import DockingRunResult, DockingService
from vinalab_core.docking.search_box import SearchBox
from vinalab_core.io.project_store import ProjectStore
from vinalab_core.runtime_paths import default_project_root, resource_root
from vinalab_core.tools.tool_locator import ToolLocator
from vinalab_ui.widgets.diagnostics_panel import DiagnosticsPanel
from vinalab_ui.widgets.docking_panel import DockingPanel, DockingRequest
from vinalab_ui.widgets.ligand_inspector import LigandInspector
from vinalab_ui.widgets.receptor_selector import ReceptorSelector
from vinalab_ui.widgets.results_panel import ResultsPanel
from vinalab_ui.widgets.scoring_panel import ScoringPanel
from vinalab_ui.widgets.search_box_editor import SearchBoxEditor
from vinalab_ui.workers.docking_worker import DockingWorker


class DockingServiceProtocol(Protocol):
    def run(self, **kwargs: object) -> DockingRunResult: ...


class MainWindow(QMainWindow):
    """English first-run workflow for a reproducible docking project."""

    TAB_NAMES = (
        "Project",
        "Receptor",
        "Ligand",
        "Search Box",
        "Pose Generation",
        "Rescoring",
        "Results",
        "Validation",
        "Diagnostics",
    )

    def __init__(
        self,
        *,
        project_root: Path | None = None,
        docking_service: DockingServiceProtocol | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("VinaLab 2.0")
        self.resize(1280, 800)
        self.resource_root = resource_root()
        self.project_root = project_root or default_project_root()
        self.project_root.mkdir(parents=True, exist_ok=True)
        self.project_store = ProjectStore(self.project_root / "vinalab.sqlite")
        vina_path = ToolLocator(self.resource_root).find("vina")
        self.docking_service = docking_service or (DockingService(vina_path) if vina_path else None)
        self.active_worker: DockingWorker | None = None
        self.search_box = SearchBox(
            center=(0.0, 0.0, 0.0),
            size=(20.0, 20.0, 20.0),
            coordinate_frame="unconfigured-receptor",
            margin=4.0,
            source="user",
        )
        tabs = QTabWidget(self)
        tabs.setObjectName("workflowTabs")
        for name in self.TAB_NAMES:
            page = self._build_page(name)
            tabs.addTab(page, name)
        self.setCentralWidget(tabs)

    def _build_page(self, name: str):
        if name == "Search Box":
            editor = SearchBoxEditor(self.search_box)
            editor.search_box_changed.connect(self._set_search_box)
            return editor
        if name == "Ligand":
            self.ligand_inspector = LigandInspector(project_root=self.resource_root)
            return self.ligand_inspector
        if name == "Receptor":
            self.receptor_selector = ReceptorSelector()
            return self.receptor_selector
        if name == "Pose Generation":
            self.docking_panel = DockingPanel(
                self.search_box,
                vina_available=self.docking_service is not None,
            )
            self.ligand_inspector.ligand_selected.connect(
                lambda ligand_path: self.docking_panel.ligand_input.setText(str(ligand_path))
            )
            self.ligand_inspector.route_selected.connect(self.docking_panel.set_element_route)
            self.receptor_selector.receptor_selected.connect(
                lambda receptor_path: self.docking_panel.receptor_input.setText(str(receptor_path))
            )
            self.docking_panel.run_requested.connect(self._run_docking)
            return self.docking_panel
        if name == "Rescoring":
            self.scoring_panel = ScoringPanel()
            self.ligand_inspector.route_selected.connect(self._show_ligand_scoring_plan)
            return self.scoring_panel
        if name == "Results":
            self.results_panel = ResultsPanel()
            return self.results_panel
        if name == "Diagnostics":
            return DiagnosticsPanel(self.resource_root)
        return QLabel(f"{name} setup")

    def _set_search_box(self, search_box: SearchBox) -> None:
        self.search_box = search_box
        self.docking_panel.set_search_box(search_box)

    def _show_ligand_scoring_plan(self, _route: object) -> None:
        if self.ligand_inspector.scoring_plan is not None:
            self.scoring_panel.show_plan(self.ligand_inspector.scoring_plan)

    def _run_docking(self, request: DockingRequest) -> None:
        if self.docking_service is None:
            self.docking_panel.validation_message = "Vina is not available; open Diagnostics for details"
            self.docking_panel.status.setText(self.docking_panel.validation_message)
            return
        if self.active_worker is not None:
            return
        output_directory = self.project_root / "runs"
        output_directory.mkdir(parents=True, exist_ok=True)
        output = output_directory / f"{request.ligand.stem}_vina_poses.pdbqt"
        persisted_run = self.project_store.create_run(
            receptor_hash=self._hash_file(request.receptor),
            search_box=request.search_box,
            engine_key="vina",
            seed=request.seed,
            cpu_threads=request.cpu_threads,
        )
        worker = DockingWorker(self.docking_service, request, output)
        worker.completed.connect(
            lambda result: self._handle_docking_completed(result, output, persisted_run.id)
        )
        worker.failed.connect(self._handle_docking_failed)
        worker.finished.connect(self._finish_docking_worker)
        self.active_worker = worker
        self.docking_panel.run_button.setEnabled(False)
        self.docking_panel.status.setText("Running Vina in the background…")
        worker.start()

    def _handle_docking_completed(self, result: DockingRunResult, output: Path, run_id: str) -> None:
        self.project_store.record_vina_poses(run_id, list(result.poses))
        self.results_panel.show_poses(result.poses)
        self.docking_panel.status.setText(f"Completed: {len(result.poses)} pose(s) saved to {output}")

    def _handle_docking_failed(self, error: str) -> None:
        self.docking_panel.status.setText(f"Docking failed: {error}")

    def _finish_docking_worker(self) -> None:
        worker = self.active_worker
        self.active_worker = None
        if worker is not None:
            worker.deleteLater()
        self.docking_panel._validate()

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
