from __future__ import annotations

import importlib
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from vinalab_core.docking.docking_service import DockingRunResult
from vinalab_core.docking.search_box import SearchBox
from vinalab_core.docking.vina_runner import VinaProcessResult
from vinalab_core.docking.vina_results import VinaPoseResult
from vinalab_ui.widgets.docking_panel import DockingRequest


def _worker_type():
    try:
        module = importlib.import_module("vinalab_ui.workers.docking_worker")
    except ModuleNotFoundError:
        return None
    return getattr(module, "DockingWorker", None)


def test_docking_worker_is_available_to_run_vina_off_the_ui_thread() -> None:
    assert _worker_type() is not None


def test_docking_worker_emits_completed_result_from_the_service(tmp_path: Path) -> None:
    worker_type = _worker_type()
    assert worker_type is not None

    class StubDockingService:
        def run(self, **_kwargs):
            return DockingRunResult(
                process=VinaProcessResult((), 0, "", ""),
                poses=(VinaPoseResult(1, -8.4, 0.0, 0.0),),
            )

    request = DockingRequest(
        receptor=tmp_path / "receptor.pdbqt",
        ligand=tmp_path / "ligand.pdbqt",
        search_box=SearchBox(
            center=(0.0, 0.0, 0.0),
            size=(20.0, 20.0, 20.0),
            coordinate_frame="receptor:test",
            margin=4.0,
            source="user",
        ),
        cpu_threads=1,
        exhaustiveness=8,
        seed=0,
    )
    worker = worker_type(StubDockingService(), request, tmp_path / "poses.pdbqt")
    completed = []
    worker.completed.connect(completed.append)

    worker.run()

    assert completed[0].poses[0].affinity == -8.4
