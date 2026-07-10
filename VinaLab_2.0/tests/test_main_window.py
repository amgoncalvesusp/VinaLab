from __future__ import annotations

import importlib
import os
from pathlib import Path
from threading import Event
from time import monotonic, sleep

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabWidget
from vinalab_core.docking.docking_service import DockingRunResult
from vinalab_core.docking.vina_runner import VinaProcessResult
from vinalab_core.docking.vina_results import VinaPoseResult
from vinalab_core.io.project_store import ProjectStore
from vinalab_ui.widgets.diagnostics_panel import DiagnosticsPanel
from vinalab_ui.widgets.docking_panel import DockingPanel
from vinalab_ui.widgets.ligand_inspector import LigandInspector
from vinalab_ui.widgets.receptor_selector import ReceptorSelector
from vinalab_ui.widgets.results_panel import ResultsPanel
from vinalab_ui.widgets.scoring_panel import ScoringPanel
from vinalab_ui.widgets.search_box_editor import SearchBoxEditor


def _main_window_type():
    try:
        module = importlib.import_module("vinalab_ui.mainwindow")
    except ModuleNotFoundError:
        return None
    return getattr(module, "MainWindow", None)


def test_main_window_is_available() -> None:
    assert _main_window_type() is not None


def test_main_window_exposes_the_english_docking_workflow() -> None:
    application = QApplication.instance() or QApplication([])
    main_window_type = _main_window_type()
    assert main_window_type is not None

    window = main_window_type()
    tabs = window.findChild(QTabWidget, "workflowTabs")

    assert application is not None
    assert tabs is not None
    assert [tabs.tabText(index) for index in range(tabs.count())] == [
        "Project",
        "Receptor",
        "Ligand",
        "Search Box",
        "Pose Generation",
        "Rescoring",
        "Results",
        "Validation",
        "Diagnostics",
    ]


def test_main_window_uses_the_search_box_editor_for_the_search_box_tab() -> None:
    QApplication.instance() or QApplication([])
    main_window_type = _main_window_type()
    assert main_window_type is not None

    window = main_window_type()

    assert isinstance(window.findChild(SearchBoxEditor), SearchBoxEditor)


def test_main_window_includes_native_tool_diagnostics() -> None:
    QApplication.instance() or QApplication([])
    main_window_type = _main_window_type()
    assert main_window_type is not None

    window = main_window_type()

    assert isinstance(window.findChild(DiagnosticsPanel), DiagnosticsPanel)


def test_main_window_includes_the_vina_execution_panel() -> None:
    QApplication.instance() or QApplication([])
    main_window_type = _main_window_type()
    assert main_window_type is not None

    window = main_window_type()

    assert isinstance(window.findChild(DockingPanel), DockingPanel)


def test_main_window_includes_the_results_table() -> None:
    QApplication.instance() or QApplication([])
    main_window_type = _main_window_type()
    assert main_window_type is not None

    window = main_window_type()

    assert isinstance(window.findChild(ResultsPanel), ResultsPanel)


def test_main_window_includes_ligand_element_inspection() -> None:
    QApplication.instance() or QApplication([])
    main_window_type = _main_window_type()
    assert main_window_type is not None

    window = main_window_type()

    assert isinstance(window.findChild(LigandInspector), LigandInspector)


def test_main_window_sends_inspected_ligand_to_the_docking_panel(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    ligand = tmp_path / "ligand.pdbqt"
    ligand.write_text(
        "ATOM      1  C1  LIG     1       0.000   0.000   0.000  0.00  0.00     0.000 C\n",
        encoding="utf-8",
    )
    main_window_type = _main_window_type()
    assert main_window_type is not None
    window = main_window_type()

    window.ligand_inspector.inspect_path(ligand)

    assert window.docking_panel.ligand_input.text() == str(ligand)


def test_main_window_uses_bundled_resources_for_ligand_scoring_diagnostics(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    main_window_type = _main_window_type()
    assert main_window_type is not None

    window = main_window_type(project_root=tmp_path)

    assert window.project_root == tmp_path
    assert window.ligand_inspector.scoring_registry.locator.project_root == window.resource_root


def test_main_window_sends_selected_receptor_to_the_docking_panel(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    receptor = tmp_path / "receptor.pdbqt"
    receptor.write_text(
        "ATOM      1  C1  REC     1       1.000   2.000   3.000  0.00  0.00     0.100 C\n",
        encoding="utf-8",
    )
    main_window_type = _main_window_type()
    assert main_window_type is not None
    window = main_window_type()

    window.receptor_selector.select_path(receptor)

    assert window.docking_panel.receptor_input.text() == str(receptor)


def test_main_window_blocks_vina_after_boron_ligand_inspection(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    ligand = tmp_path / "boron_ligand.pdbqt"
    ligand.write_text(
        "ATOM      1  B1  LIG     1       0.000   0.000   0.000  0.00  0.00     0.000 B\n",
        encoding="utf-8",
    )
    main_window_type = _main_window_type()
    assert main_window_type is not None
    window = main_window_type()

    window.ligand_inspector.inspect_path(ligand)

    assert not window.docking_panel.run_button.isEnabled()
    assert "Boron" in window.docking_panel.validation_message


def test_main_window_updates_rescoring_plan_after_ligand_inspection(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    ligand = tmp_path / "boron_ligand.pdbqt"
    ligand.write_text(
        "ATOM      1  B1  LIG     1       0.000   0.000   0.000  0.00  0.00     0.000 B\n",
        encoding="utf-8",
    )
    main_window_type = _main_window_type()
    assert main_window_type is not None
    window = main_window_type(project_root=tmp_path)

    window.ligand_inspector.inspect_path(ligand)

    assert isinstance(window.scoring_panel, ScoringPanel)
    assert "xTB" in window.scoring_panel.recommendation.text()


def test_main_window_runs_a_docking_request_and_updates_results(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])

    class StubDockingService:
        def run(self, **_kwargs):
            return DockingRunResult(
                process=VinaProcessResult((), 0, "", ""),
                poses=(VinaPoseResult(1, -8.4, 0.0, 0.0),),
            )

    receptor = tmp_path / "receptor.pdbqt"
    ligand = tmp_path / "ligand.pdbqt"
    receptor.write_text("RECEPTOR", encoding="utf-8")
    ligand.write_text("LIGAND", encoding="utf-8")
    main_window_type = _main_window_type()
    assert main_window_type is not None
    window = main_window_type(project_root=tmp_path, docking_service=StubDockingService())
    window.docking_panel.set_inputs(receptor, ligand)

    window.docking_panel.run_button.click()

    table = window.results_panel.table
    application = QApplication.instance()
    assert application is not None
    for _ in range(20):
        application.processEvents()
        if table.rowCount() == 1:
            break
        sleep(0.01)
    assert table.rowCount() == 1
    assert table.item(0, 1).text() == "-8.400"


def test_main_window_starts_docking_without_blocking_the_ui_thread(tmp_path: Path) -> None:
    application = QApplication.instance() or QApplication([])
    release_service = Event()

    class SlowDockingService:
        def run(self, **_kwargs):
            release_service.wait(0.2)
            return DockingRunResult(
                process=VinaProcessResult((), 0, "", ""),
                poses=(VinaPoseResult(1, -8.4, 0.0, 0.0),),
            )

    receptor = tmp_path / "receptor.pdbqt"
    ligand = tmp_path / "ligand.pdbqt"
    receptor.write_text("RECEPTOR", encoding="utf-8")
    ligand.write_text("LIGAND", encoding="utf-8")
    main_window_type = _main_window_type()
    assert main_window_type is not None
    window = main_window_type(project_root=tmp_path, docking_service=SlowDockingService())
    window.docking_panel.set_inputs(receptor, ligand)

    started = monotonic()
    window.docking_panel.run_button.click()
    elapsed = monotonic() - started

    assert elapsed < 0.1
    release_service.set()
    for _ in range(20):
        application.processEvents()
        if window.results_panel.table.rowCount() == 1:
            break
        sleep(0.01)
    assert window.results_panel.table.rowCount() == 1


def test_main_window_persists_completed_vina_poses_in_the_project_database(tmp_path: Path) -> None:
    application = QApplication.instance() or QApplication([])

    class StubDockingService:
        def run(self, **_kwargs):
            return DockingRunResult(
                process=VinaProcessResult((), 0, "", ""),
                poses=(VinaPoseResult(1, -8.4, 0.0, 0.0),),
            )

    receptor = tmp_path / "receptor.pdbqt"
    ligand = tmp_path / "ligand.pdbqt"
    receptor.write_text("RECEPTOR", encoding="utf-8")
    ligand.write_text("LIGAND", encoding="utf-8")
    main_window_type = _main_window_type()
    assert main_window_type is not None
    window = main_window_type(project_root=tmp_path, docking_service=StubDockingService())
    window.docking_panel.set_inputs(receptor, ligand)

    window.docking_panel.run_button.click()
    for _ in range(20):
        application.processEvents()
        if window.results_panel.table.rowCount() == 1:
            break
        sleep(0.01)

    with ProjectStore(tmp_path / "vinalab.sqlite") as store:
        persisted_run = store.connection.execute("SELECT id FROM runs").fetchone()
        assert persisted_run is not None
        assert store.list_vina_poses(persisted_run["id"]) == (VinaPoseResult(1, -8.4, 0.0, 0.0),)
