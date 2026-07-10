from __future__ import annotations

import importlib
from pathlib import Path

from vinalab_core.docking.search_box import SearchBox
from vinalab_core.docking.vina_results import VinaPoseResult


def _project_store_type():
    try:
        module = importlib.import_module("vinalab_core.io.project_store")
    except ModuleNotFoundError:
        return None
    return getattr(module, "ProjectStore", None)


def test_project_store_is_available_for_persistent_runs() -> None:
    assert _project_store_type() is not None


def test_project_store_persists_the_exact_search_box_for_a_run(tmp_path: Path) -> None:
    project_store_type = _project_store_type()
    assert project_store_type is not None
    search_box = SearchBox(
        center=(10.0, 20.0, 30.0),
        size=(24.0, 22.0, 20.0),
        coordinate_frame="receptor:abc123",
        margin=4.0,
        source="reference_ligand",
    )

    with project_store_type(tmp_path / "study.vinalab.sqlite") as store:
        run = store.create_run(
            receptor_hash="abc123",
            search_box=search_box,
            engine_key="vina",
            seed=42,
            cpu_threads=4,
        )

    with project_store_type(tmp_path / "study.vinalab.sqlite") as store:
        persisted = store.get_run(run.id)

    assert persisted.id == run.id
    assert persisted.search_box == search_box
    assert persisted.engine_key == "vina"
    assert persisted.seed == 42
    assert persisted.cpu_threads == 4


def test_project_store_persists_vina_pose_results_for_a_run(tmp_path: Path) -> None:
    project_store_type = _project_store_type()
    assert project_store_type is not None
    search_box = SearchBox(
        center=(0.0, 0.0, 0.0),
        size=(20.0, 20.0, 20.0),
        coordinate_frame="receptor:abc123",
        margin=4.0,
        source="user",
    )
    with project_store_type(tmp_path / "study.vinalab.sqlite") as store:
        run = store.create_run(
            receptor_hash="abc123",
            search_box=search_box,
            engine_key="vina",
            seed=42,
            cpu_threads=4,
        )
        store.record_vina_poses(run.id, [VinaPoseResult(1, -8.4, 0.0, 0.0)])
        poses = store.list_vina_poses(run.id)

    assert poses == (VinaPoseResult(1, -8.4, 0.0, 0.0),)
