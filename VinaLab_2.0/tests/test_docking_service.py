from __future__ import annotations

import importlib
from pathlib import Path

from vinalab_core.docking.search_box import SearchBox
from vinalab_core.docking.vina_runner import VinaProcessResult


def _service_type():
    try:
        module = importlib.import_module("vinalab_core.docking.docking_service")
    except ModuleNotFoundError:
        return None
    return getattr(module, "DockingService", None)


def test_docking_service_is_available_for_an_end_to_end_vina_run() -> None:
    assert _service_type() is not None


def test_docking_service_builds_runs_and_parses_vina_poses(tmp_path: Path) -> None:
    service_type = _service_type()
    assert service_type is not None

    class StubRunner:
        def __init__(self) -> None:
            self.command = ()

        def execute(self, command, **_kwargs):
            self.command = tuple(command)
            return VinaProcessResult(
                command=self.command,
                returncode=0,
                stdout="""
mode | affinity | dist from best mode
-----+----------+----------+----------
   1       -8.4          0          0
""",
                stderr="",
            )

    runner = StubRunner()
    service = service_type(Path("C:/tools/vina.exe"), runner=runner)
    result = service.run(
        receptor=tmp_path / "receptor.pdbqt",
        ligand=tmp_path / "ligand.pdbqt",
        output=tmp_path / "poses.pdbqt",
        search_box=SearchBox(
            center=(1.0, 2.0, 3.0),
            size=(20.0, 20.0, 20.0),
            coordinate_frame="receptor:test",
            margin=4.0,
            source="user",
        ),
        cpu_threads=4,
        exhaustiveness=8,
        seed=7,
    )

    assert result.ok
    assert result.poses[0].affinity == -8.4
    assert "--center_x" in runner.command
    assert runner.command[runner.command.index("--cpu") + 1] == "4"
