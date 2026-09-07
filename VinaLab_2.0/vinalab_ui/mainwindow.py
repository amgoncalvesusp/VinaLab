"""Desktop orchestration for persistent docking and analysis workflows."""

import hashlib
import json
import math
import shutil
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from PySide6.QtWidgets import QMainWindow, QScrollArea, QTabWidget

from vinalab_core.docking.docking_service import DockingService
from vinalab_core.docking.search_box import SearchBox
from vinalab_core.io.project_store import ProjectStore
from vinalab_core.runtime_paths import default_project_root, resource_root
from vinalab_core.tools.tool_locator import ToolLocator
from vinalab_ui.widgets.diagnostics_panel import DiagnosticsPanel
from vinalab_ui.widgets.docking_panel import DockingPanel
from vinalab_ui.widgets.ligand_inspector import LigandInspector
from vinalab_ui.widgets.project_panel import ProjectPanel
from vinalab_ui.widgets.receptor_selector import ReceptorSelector
from vinalab_ui.widgets.results_panel import ResultsPanel
from vinalab_ui.widgets.scoring_panel import ScoringPanel
from vinalab_ui.widgets.search_box_editor import SearchBoxEditor
from vinalab_ui.widgets.validation_panel import ValidationPanel
from vinalab_ui.workers.docking_worker import DockingWorker
from vinalab_ui.workers.task_worker import TaskWorker


class MainWindow(QMainWindow):
    TAB_NAMES = ("Project", "Receptor", "Ligand", "Search Box", "Pose Generation",
                 "Rescoring", "Results", "Validation", "Diagnostics")

    def __init__(self, *, project_root=None, docking_service=None):
        super().__init__()
        self.setWindowTitle("VinaLab 2.0")
        self.resize(1280, 800)
        self.resource_root = resource_root()
        self.project_root = Path(project_root or default_project_root()).resolve()
        self.project_root.mkdir(parents=True, exist_ok=True)
        self.project_store = ProjectStore(self.project_root / "vinalab.sqlite")
        vina = ToolLocator(self.resource_root).find("vina")
        self.docking_service = docking_service or (DockingService(vina) if vina else None)
        self.active_worker = None
        self.current_run_id = None
        self._closed = False
        self.search_box = SearchBox((0.0, 0.0, 0.0), (20.0, 20.0, 20.0),
                                    "unconfigured-receptor", 4.0, "user")
        self.project_panel = ProjectPanel()
        self.receptor_selector = ReceptorSelector()
        self.ligand_inspector = LigandInspector(project_root=self.resource_root)
        self.search_box_editor = SearchBoxEditor(self.search_box)
        self.docking_panel = DockingPanel(self.search_box, vina_available=self.docking_service is not None)
        self.scoring_panel = ScoringPanel()
        self.results_panel = ResultsPanel()
        self.validation_panel = ValidationPanel()
        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("workflowTabs")
        pages = (self.project_panel, self.receptor_selector, self.ligand_inspector,
                 self.search_box_editor, self.docking_panel, self.scoring_panel,
                 self.results_panel, self.validation_panel, DiagnosticsPanel(self.resource_root))
        for name, page in zip(self.TAB_NAMES, pages, strict=True):
            if name in {"Receptor", "Ligand", "Rescoring", "Validation"}:
                scroll = QScrollArea(self)
                scroll.setWidgetResizable(True)
                scroll.setFrameShape(QScrollArea.Shape.NoFrame)
                scroll.setWidget(page)
                page = scroll
            self.tabs.addTab(page, name)
        self.setCentralWidget(self.tabs)
        self._connect_workflow()
        self._refresh_project()

    def _connect_workflow(self):
        self.project_panel.project_requested.connect(self._open_project_safely)
        self.project_panel.run_selected.connect(self._load_run_safely)
        self.project_panel.analysis_selected.connect(self._load_analysis)
        self.receptor_selector.path_input.textChanged.connect(self.docking_panel.receptor_input.setText)
        self.ligand_inspector.path_input.textChanged.connect(self.docking_panel.ligand_input.setText)
        self.receptor_selector.receptor_selected.connect(self._set_receptor)
        self.docking_panel.receptor_input.editingFinished.connect(
            lambda: self._set_receptor(Path(self.docking_panel.receptor_input.text())))
        self.ligand_inspector.ligand_selected.connect(
            lambda path: self.docking_panel.ligand_input.setText(str(path)))
        self.ligand_inspector.route_selected.connect(self.docking_panel.set_element_route)
        self.ligand_inspector.route_selected.connect(self._show_ligand_scoring_plan)
        self.search_box_editor.search_box_changed.connect(self._set_search_box)
        self.search_box_editor.reference_selected.connect(self._set_reference)
        self.docking_panel.run_requested.connect(self._run_docking)
        for selector in (self.receptor_selector, self.ligand_inspector):
            selector.conversion.convert_requested.connect(self._convert)
        self.validation_panel.validate_requested.connect(self._validate_reference)
        self.scoring_panel.score_requested.connect(self._rescore)
        self.results_panel.pymol_requested.connect(self._open_pymol)

    def _refresh_project(self):
        self.project_panel.show_project(self.project_root, self.project_store.list_runs())
        analyses = []
        for path in sorted((self.project_root / "analyses").glob("*/*.json")):
            if path.name not in {"validation.json", "rescoring.json"}:
                continue
            try:
                data = self._read_manifest(path)
                timestamp = data.get("created_at")
                if not isinstance(timestamp, str):
                    raise ValueError("Missing or invalid analysis timestamp")  # noqa: TRY004 - Invalid external data uses the manifest validation contract.
                datetime.fromisoformat(timestamp)
                analyses.append((path, data))
            except (OSError, ValueError) as error:
                self.project_panel.status.setText(f"Unreadable analysis {path.name}: {error}")
        self.project_panel.show_analyses(sorted(analyses, key=lambda item: item[1].get("created_at", ""), reverse=True))

    def open_project(self, path):
        if self.active_worker is not None:
            raise ValueError("Wait for the active operation before changing projects.")
        root = Path(path).resolve()
        root.mkdir(parents=True, exist_ok=True)
        store = ProjectStore(root / "vinalab.sqlite")
        self.project_store.close()
        self.project_store, self.project_root = store, root
        self.current_run_id = None
        self.results_panel.show_poses(())
        self.results_panel.set_output(None)
        self.validation_panel.poses_input.clear()
        self.validation_panel.table.setRowCount(0)
        self.validation_panel.export_button.setEnabled(False)
        self.validation_panel.reference_input.clear()
        self.receptor_selector.path_input.clear()
        self.ligand_inspector.path_input.clear()
        self.docking_panel.set_inputs("", "")
        self.scoring_panel.receptor_input.clear()
        self.scoring_panel.ligand_input.clear()
        self.scoring_panel.result_label.clear()
        self.search_box_editor.clear_reference()
        self.search_box_editor.clear_structure()
        box = SearchBox((0., 0., 0.), (20., 20., 20.), "unconfigured-receptor", 4., "user")
        self.search_box_editor.set_search_box(box)
        self._set_search_box(box)
        self._refresh_project()
        self.setWindowTitle(f"VinaLab 2.0 - {root.name}")

    def _open_project_safely(self, path):
        try:
            self.open_project(path)
        except Exception as error:  # noqa: BLE001 - Report project-open failures at the Qt slot boundary.
            self.project_panel.status.setText(str(error))

    def _set_receptor(self, path):
        try:
            receptor_hash = self._hash_file(Path(path))
            if receptor_hash != self.search_box.coordinate_frame:
                self.search_box_editor.clear_reference()
                self.validation_panel.reference_input.clear()
            self.docking_panel.receptor_input.setText(str(path))
            box = replace(self.search_box, coordinate_frame=receptor_hash, source="user")
            self.search_box_editor.set_search_box(box)
            self._set_search_box(box)
            self.search_box_editor.set_structure(path)
        except (OSError, ValueError) as error:
            self.receptor_selector.status.setText(str(error))

    def _set_reference(self, path):
        self.validation_panel.reference_input.setText(str(path))
        self.validation_panel.frame_confirmed.setChecked(False)

    def _set_search_box(self, search_box):
        self.search_box = search_box
        self.docking_panel.set_search_box(search_box)

    def _show_ligand_scoring_plan(self, _route):
        if self.ligand_inspector.scoring_plan is not None:
            self.scoring_panel.show_plan(self.ligand_inspector.scoring_plan)

    def _set_busy(self, busy):
        self.docking_panel.set_busy(busy)
        for panel in (self.receptor_selector, self.ligand_inspector, self.search_box_editor,
                      self.scoring_panel, self.validation_panel):
            panel.setEnabled(not busy)
        for button in (self.project_panel.new_button, self.project_panel.open_button,
                       self.project_panel.load_button):
            button.setEnabled(not busy)

    def _run_docking(self, request):
        if self.active_worker is not None or self.docking_service is None:
            return
        error = self.docking_panel._input_error()
        if error:
            self.docking_panel.status.setText(error)
            return
        try:
            run_id = str(uuid4())
            run_directory = self.project_root / "runs" / run_id
            run_directory.mkdir(parents=True)
            receptor, ligand = run_directory / "receptor.pdbqt", run_directory / "ligand.pdbqt"
            shutil.copyfile(request.receptor, receptor)
            shutil.copyfile(request.ligand, ligand)
            receptor_hash = self._hash_file(receptor)
            box = replace(request.search_box, coordinate_frame=receptor_hash)
            prepared = replace(request, receptor=receptor, ligand=ligand, search_box=box)
            output = run_directory / "poses.pdbqt"
            metadata = {"original_receptor": str(request.receptor.resolve()),
                        "original_ligand": str(request.ligand.resolve()),
                        "scoring": request.scoring, "num_modes": request.num_modes}
            run = self.project_store.create_run(
                receptor_hash=receptor_hash, ligand_hash=self._hash_file(ligand),
                search_box=box, engine_key="vina", scoring=request.scoring,
                num_modes=request.num_modes, run_id=run_id, seed=request.seed,
                cpu_threads=request.cpu_threads, exhaustiveness=request.exhaustiveness,
                receptor_path=receptor.relative_to(self.project_root).as_posix(),
                ligand_path=ligand.relative_to(self.project_root).as_posix(),
                output_path=output.relative_to(self.project_root).as_posix(),
                status="running", metadata=metadata)
            self.current_run_id = run.id
            self._write_json(run_directory / "request.json", {**asdict(prepared), "run_id": run.id})
            worker = DockingWorker(self.docking_service, prepared, output)
            worker.process_finished.connect(lambda process: self._save_process_logs(run.id, run_directory, process))
            worker.completed.connect(lambda result: self._handle_docking_completed(result, output, run.id))
            worker.failed.connect(lambda message: self._handle_docking_failed(message, run.id, run_directory))
            worker.finished.connect(self._finish_docking_worker)
            self.active_worker = worker
            self._set_busy(True)
            self.results_panel.show_poses(())
            self.results_panel.set_output(None)
            self.docking_panel.status.setText(f"Running {request.scoring} in the background...")
            self._refresh_project()
            worker.start()
        except Exception as error:  # noqa: BLE001 - Recover failed run setup at the Qt slot boundary.
            if 'run' in locals():
                self.project_store.update_run_status(run.id, "failed", error=str(error))
            if self.active_worker is not None and not self.active_worker.isRunning():
                self._finish_docking_worker()
            self.docking_panel.status.setText(f"Cannot start docking: {error}")

    def _save_process_logs(self, run_id, directory, process):
        try:
            self.project_store.update_run_status(run_id, "running", stdout=process.stdout, stderr=process.stderr)
            (directory / "stdout.log").write_text(process.stdout, encoding="utf-8")
            (directory / "stderr.log").write_text(process.stderr, encoding="utf-8")
        except Exception as error:  # noqa: BLE001 - Keep log persistence failures inside the Qt callback.
            self.statusBar().showMessage(f"Could not persist process logs: {error}")

    def _handle_docking_completed(self, result, output, run_id):
        try:
            self.project_store.record_vina_poses(run_id, list(result.poses))
            old = self.project_store.get_run(run_id)
            metadata = {**old.metadata, "output_hash": self._hash_file(output)} if output.is_file() else dict(old.metadata)
            self.project_store.update_run_status(run_id, "completed", metadata=metadata)
            (output.parent / "stdout.log").write_text(result.process.stdout, encoding="utf-8")
            (output.parent / "stderr.log").write_text(result.process.stderr, encoding="utf-8")
            self.results_panel.show_poses(result.poses)
            self.results_panel.set_output(output, pymol_available=self._pymol_available())
            self.validation_panel.poses_input.setText(str(output))
            self.docking_panel.status.setText(f"Completed: {len(result.poses)} pose(s) saved to {output}")
            self._refresh_project()
        except Exception as error:  # noqa: BLE001 - Preserve failure reporting from the completion callback.
            self._handle_docking_failed(f"Result persistence failed: {error}", run_id, output.parent)

    def _handle_docking_failed(self, error, run_id=None, run_directory=None):
        self.docking_panel.status.setText(f"Docking failed: {error}")
        if run_id is not None:
            try:
                self.project_store.update_run_status(run_id, "failed", error=str(error))
                (run_directory / "failure.log").write_text(str(error), encoding="utf-8")
                self._refresh_project()
            except Exception as persistence_error:  # noqa: BLE001 - Report secondary persistence failures without escaping Qt.
                self.docking_panel.status.setText(f"Docking failed: {error}; history error: {persistence_error}")

    def _finish_docking_worker(self):
        worker = self.active_worker
        self.active_worker = None
        if worker is not None:
            worker.deleteLater()
        self._set_busy(False)

    def _start_task(self, operation, completed, status):
        if self.active_worker is not None:
            return
        worker = TaskWorker(operation)

        def receive(value):
            try:
                completed(value)
            except Exception as error:  # noqa: BLE001 - Arbitrary task callbacks must not unwind through Qt.
                status.setText(f"Operation failed: {error}")

        worker.completed.connect(receive)
        worker.failed.connect(lambda error: status.setText(f"Operation failed: {error}"))
        worker.finished.connect(self._finish_docking_worker)
        self.active_worker = worker
        self._set_busy(True)
        status.setText("Running in the background...")
        worker.start()

    def _convert(self, source, output, role):
        from vinalab_core.prepare.conversion import ConversionService
        selector = self.receptor_selector if role == "receptor" else self.ligand_inspector

        def completed(result):
            if not result.success:
                raise ValueError(result.errors)
            selector.conversion.status.setText(f"Prepared: {result.output_path}\n{result.log}")
            if role == "receptor":
                selector.select_path(result.output_path)
            else:
                selector.inspect_path(result.output_path)

        self._start_task(lambda: ConversionService().convert(source, output, role=role),
                         completed, selector.conversion.status)

    def _validate_reference(self, poses, reference):
        from vinalab_core.analysis.poses import validate_reference_poses
        output_directory = self.project_root / "analyses" / str(uuid4())
        source_run = self.project_store.get_run(self.current_run_id) if self.current_run_id else None
        saved_poses = output_directory / ("poses" + poses.suffix)
        saved_reference = output_directory / ("reference" + reference.suffix)

        def operation():
            output_directory.mkdir(parents=True)
            shutil.copyfile(poses, saved_poses)
            shutil.copyfile(reference, saved_reference)
            return validate_reference_poses(saved_poses, saved_reference)

        def completed(results):
            source_run_id = None
            if (source_run and self._artifact_path(source_run.output_path) == poses.resolve()
                    and source_run.metadata.get("output_hash") == self._hash_file(saved_poses)):
                source_run_id = source_run.id
            self._write_json(output_directory / "validation.json",
                             {"poses": str(poses), "reference": str(reference),
                              "pose_hash": self._hash_file(saved_poses), "reference_hash": self._hash_file(saved_reference),
                              "source_run_id": source_run_id,
                              "frame_confirmed": True, "results": [asdict(result) for result in results]})
            self._link_analysis(source_run_id, output_directory / "validation.json")
            rows = [(result.mode, f"{result.rmsd:.4f}" if result.comparable else "",
                     "Yes" if result.comparable else "No", result.reason) for result in results]
            self.validation_panel.show_rows(rows)
            self._refresh_project()

        self._start_task(operation, completed,
                         self.validation_panel.status)

    def _rescore(self, request):
        from vinalab_core.scoring.xtb_scorer import XtbScorer
        output_directory = self.project_root / "analyses" / str(uuid4())
        receptor = output_directory / "receptor.xyz"
        ligand = output_directory / "ligand.xyz"

        def operation():
            output_directory.mkdir(parents=True)
            shutil.copyfile(request["receptor_xyz"], receptor)
            shutil.copyfile(request["ligand_xyz"], ligand)
            parameters = {**request, "receptor_xyz": receptor, "ligand_xyz": ligand,
                          "hydrogen_complete": True}
            self._write_json(output_directory / "request.json",
                             {**parameters, "receptor_hash": self._hash_file(receptor),
                              "ligand_hash": self._hash_file(ligand)})
            return XtbScorer(self.resource_root).score_interaction(**parameters)

        def completed(result):
            self._write_json(output_directory / "rescoring.json", {**asdict(result), "source_run_id": None})
            self.scoring_panel.show_result(result, output_directory / "rescoring.json")
            self._refresh_project()

        self._start_task(operation, completed, self.scoring_panel.status)

    def _load_run_safely(self, run_id):
        if self.active_worker is not None:
            return
        try:
            run = self.project_store.get_run(run_id)
            self.search_box_editor.clear_reference()
            self.search_box_editor.clear_structure()
            self.validation_panel.reference_input.clear()
            self.scoring_panel.result_label.clear()
            self.current_run_id = run_id
            self.results_panel.show_poses(self.project_store.list_vina_poses(run_id))
            output = self._artifact_path(run.output_path)
            receptor = self._artifact_path(run.receptor_path)
            ligand = self._artifact_path(run.ligand_path)
            self.results_panel.set_output(output, pymol_available=self._pymol_available())
            self.docking_panel.set_inputs(receptor or "", ligand or "")
            self.docking_panel.scoring_input.setCurrentText(run.scoring.title())
            self.docking_panel.cpu_input.setValue(run.cpu_threads)
            self.docking_panel.seed_input.setValue(run.seed)
            self.docking_panel.exhaustiveness_input.setValue(run.exhaustiveness)
            self.docking_panel.modes_input.setValue(run.num_modes)
            self.search_box_editor.set_search_box(run.search_box)
            self._set_search_box(run.search_box)
            if receptor and receptor.is_file():
                self.search_box_editor.set_structure(receptor)
            self.validation_panel.poses_input.setText(str(output or ""))
            self.docking_panel.status.setText(f"Run {run.id}: {run.status}. {run.error}")
            for artifact in run.metadata.get("analyses", ()):
                self._load_analysis(self._artifact_path(artifact), activate=False)
            self.tabs.setCurrentWidget(self.results_panel)
        except Exception as error:  # noqa: BLE001 - Surface malformed history at the Qt slot boundary.
            self.project_panel.status.setText(f"Cannot load run: {error}")

    def _link_analysis(self, run_id, path):
        if run_id is None:
            return
        run = self.project_store.get_run(run_id)
        analyses = [*run.metadata.get("analyses", ()), path.relative_to(self.project_root).as_posix()]
        self.project_store.update_run_status(run_id, run.status, error=run.error,
                                            metadata={**run.metadata, "analyses": analyses})

    def _load_analysis(self, path, *, activate=True):
        if self.active_worker is not None:
            return
        try:
            path = self._contained_file(path)
            data = self._read_manifest(path)
            if path.name == "validation.json":
                panel = self.validation_panel
                saved_reference = self._contained_file(next(path.parent.glob("reference.*")))
                saved_poses = self._contained_file(next(path.parent.glob("poses.*")))
                self._require_hash(saved_reference, data.get("reference_hash"))
                self._require_hash(saved_poses, data.get("pose_hash"))
                self._validate_saved_rmsd(data)
                panel.reference_input.setText(str(saved_reference))
                panel.poses_input.setText(str(saved_poses))
                panel.frame_confirmed.setChecked(data["frame_confirmed"])
                panel.show_rows([(row["mode"], f"{row['rmsd']:.4f}" if row["comparable"] else "",
                                  "Yes" if row["comparable"] else "No", row["reason"])
                                 for row in data["results"]])
                if activate:
                    self.tabs.setCurrentIndex(7)
            elif path.name == "rescoring.json":
                panel = self.scoring_panel
                request = self._read_manifest(path.with_name("request.json"))
                receptor = self._contained_file(path.parent / "receptor.xyz")
                ligand = self._contained_file(path.parent / "ligand.xyz")
                self._require_hash(receptor, request.get("receptor_hash"))
                self._require_hash(ligand, request.get("ligand_hash"))
                values = [data[name]["hartree"] for name in ("complex_energy", "receptor_energy", "ligand_energy")]
                values += [data["interaction_hartree"], data["interaction_kcal_per_mol"]]
                if not all(type(value) in {int, float} and math.isfinite(value) for value in values):
                    raise ValueError("Invalid saved interaction energies")
                if not math.isclose(values[0] - values[1] - values[2], values[3], abs_tol=1e-8):
                    raise ValueError("Inconsistent interaction energy components")
                from vinalab_core.scoring.xtb_scorer import HARTREE_TO_KCAL_PER_MOL
                if not math.isclose(values[3] * HARTREE_TO_KCAL_PER_MOL, values[4], abs_tol=1e-6):
                    raise ValueError("Inconsistent interaction energy units")
                if request.get("method") not in {"gfn2", "gfnff"}:
                    raise ValueError("Unknown saved scoring method")
                for name in ("charge_receptor", "charge_ligand", "uhf_receptor", "uhf_ligand", "uhf_complex"):
                    if type(request.get(name)) is not int:
                        raise ValueError("Invalid saved charge/spin")
                panel.receptor_input.setText(str(receptor))
                panel.ligand_input.setText(str(ligand))
                panel.method_input.setCurrentIndex(panel.method_input.findData(request["method"]))
                for name in ("charge_receptor", "charge_ligand", "uhf_receptor", "uhf_ligand", "uhf_complex"):
                    getattr(panel, name).setValue(request[name])
                panel.show_saved_result(data, path)
                if activate:
                    self.tabs.setCurrentIndex(5)
        except Exception as error:  # noqa: BLE001 - Surface invalid imported analyses at the Qt slot boundary.
            self.project_panel.status.setText(f"Cannot load analysis: {error}")

    def _contained_file(self, path):
        resolved = Path(path).resolve()
        if not resolved.is_relative_to(self.project_root) or not resolved.is_file():
            raise ValueError("Analysis file is missing or outside this project.")
        return resolved

    def _read_manifest(self, path):
        def reject_constant(value):
            raise ValueError(f"Nonfinite JSON number: {value}")
        data = json.loads(self._contained_file(path).read_text(encoding="utf-8"), parse_constant=reject_constant)
        if not isinstance(data, dict):
            raise ValueError("Expected an analysis JSON object")  # noqa: TRY004 - Invalid external data uses the manifest validation contract.
        return data

    def _require_hash(self, path, expected):
        if not isinstance(expected, str) or self._hash_file(path) != expected:
            raise ValueError(f"Snapshot hash mismatch: {path.name}")

    @staticmethod
    def _validate_saved_rmsd(data):
        if data.get("frame_confirmed") is not True or not isinstance(data.get("results"), list):
            raise ValueError("Invalid reference frame confirmation or RMSD results")
        for row in data["results"]:
            if (not isinstance(row, dict) or type(row.get("mode")) is not int or row["mode"] < 1
                    or type(row.get("comparable")) is not bool or not isinstance(row.get("reason"), str)):
                raise ValueError("Invalid RMSD row")
            value = row.get("rmsd")
            if row["comparable"]:
                if type(value) not in {int, float} or not math.isfinite(value) or value < 0:
                    raise ValueError("RMSD must be finite and nonnegative")
            elif value is not None:
                raise ValueError("Incomparable RMSD must be null")

    @staticmethod
    def _pymol_available():
        return shutil.which("pymol") is not None or shutil.which("pymol.exe") is not None

    def _open_pymol(self):
        from vinalab_core.analysis.pymol import launch_pymol
        if self.current_run_id is None:
            return
        try:
            run = self.project_store.get_run(self.current_run_id)
            reference = Path(self.validation_panel.reference_input.text())
            launch_pymol(self._artifact_path(run.receptor_path), (self._artifact_path(run.output_path),),
                         reference=reference if reference.is_file() else None, search_box=run.search_box)
        except (OSError, ValueError, RuntimeError) as error:
            self.results_panel.status.setText(f"PyMOL could not open: {error}")

    def _artifact_path(self, value):
        if not value:
            return None
        path = Path(value.replace("\\", "/"))
        if path.is_absolute():
            return path
        resolved = (self.project_root / path).resolve()
        if not resolved.is_relative_to(self.project_root):
            raise ValueError("Artifact path escapes the project folder.")
        return resolved

    def closeEvent(self, event):
        if self.active_worker is not None:
            self.statusBar().showMessage("A calculation is still active. Wait for completion before closing.")
            event.ignore()
            return
        if not self._closed:
            self.project_store.close()
            self._closed = True
        event.accept()

    @staticmethod
    def _hash_file(path):
        digest = hashlib.sha256()
        with Path(path).open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _write_json(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"created_at": datetime.now(UTC).isoformat(), **data}
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, default=str, allow_nan=False), encoding="utf-8")
        temporary.replace(path)
