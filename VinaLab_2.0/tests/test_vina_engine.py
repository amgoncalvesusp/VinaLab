from __future__ import annotations

import importlib
from pathlib import Path

from vinalab_core.docking.search_box import SearchBox


def _command_builder_type():
    try:
        module = importlib.import_module("vinalab_core.docking.vina_engine")
    except ModuleNotFoundError:
        return None
    return getattr(module, "VinaCommandBuilder", None)


def test_vina_command_builder_is_available_for_cpu_docking() -> None:
    assert _command_builder_type() is not None


def test_vina_command_builder_uses_the_exact_search_box_and_cpu_budget() -> None:
    command_builder_type = _command_builder_type()
    assert command_builder_type is not None
    search_box = SearchBox(
        center=(11.0, -2.5, 33.25),
        size=(24.0, 22.0, 20.0),
        coordinate_frame="receptor:abc123",
        margin=4.0,
        source="user",
    )

    command = command_builder_type(Path("C:/tools/vina.exe")).build(
        receptor=Path("C:/input/receptor.pdbqt"),
        ligand=Path("C:/input/ligand.pdbqt"),
        output=Path("C:/output/poses.pdbqt"),
        search_box=search_box,
        cpu_threads=4,
        exhaustiveness=16,
        seed=42,
    )

    assert command == [
        str(Path("C:/tools/vina.exe")),
        "--receptor", str(Path("C:/input/receptor.pdbqt")),
        "--ligand", str(Path("C:/input/ligand.pdbqt")),
        "--out", str(Path("C:/output/poses.pdbqt")),
        "--center_x", "11",
        "--center_y", "-2.5",
        "--center_z", "33.25",
        "--size_x", "24",
        "--size_y", "22",
        "--size_z", "20",
        "--cpu", "4",
        "--exhaustiveness", "16",
        "--seed", "42",
    ]
