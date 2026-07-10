from __future__ import annotations

import importlib
from pathlib import Path

from vinalab_core.docking.vina_runner import VinaProcessResult


def _scorer_type():
    try:
        module = importlib.import_module("vinalab_core.scoring.xtb_scorer")
    except ModuleNotFoundError:
        return None
    return getattr(module, "XtbScorer", None)


def test_xtb_scorer_is_available_as_the_exotic_rescoring_plugin() -> None:
    assert _scorer_type() is not None


def test_xtb_scorer_builds_a_solvated_gfn2_single_point_command(tmp_path: Path) -> None:
    scorer_type = _scorer_type()
    assert scorer_type is not None
    executable = tmp_path / "tools" / "xtb" / "xtb.exe"
    executable.parent.mkdir(parents=True)
    executable.write_text("placeholder", encoding="utf-8")
    structure = tmp_path / "complex.xyz"
    structure.write_text("1\ncomment\nB 0 0 0\n", encoding="utf-8")
    scorer = scorer_type(tmp_path)

    command = scorer.build_single_point_command(structure, charge=-1)

    assert command == [
        str(executable),
        str(structure),
        "--gfn", "2",
        "--alpb", "water",
        "--chrg", "-1",
    ]


def test_xtb_scorer_parses_total_energy_in_hartree() -> None:
    scorer_type = _scorer_type()
    assert scorer_type is not None

    energy = scorer_type.parse_total_energy(":: total energy             -5.080125650447 Eh    ::\n")

    assert energy == -5.080125650447


def test_xtb_scorer_executes_and_converts_hartree_to_kcal_per_mol(tmp_path: Path) -> None:
    scorer_type = _scorer_type()
    assert scorer_type is not None
    executable = tmp_path / "tools" / "xtb" / "xtb.exe"
    executable.parent.mkdir(parents=True)
    executable.write_text("placeholder", encoding="utf-8")
    structure = tmp_path / "complex.xyz"
    structure.write_text("1\ncomment\nB 0 0 0\n", encoding="utf-8")

    class StubRunner:
        def execute(self, command, **_kwargs):
            return VinaProcessResult(tuple(command), 0, ":: total energy -1.000000 Eh ::\n", "")

    result = scorer_type(tmp_path, runner=StubRunner()).score_single_point(structure, charge=0, cpu_threads=2)

    assert result.hartree == -1.0
    assert result.kcal_per_mol == -627.5094740631


def test_xtb_scorer_runs_in_an_isolated_temporary_working_directory(tmp_path: Path) -> None:
    scorer_type = _scorer_type()
    assert scorer_type is not None
    executable = tmp_path / "tools" / "xtb" / "xtb.exe"
    executable.parent.mkdir(parents=True)
    executable.write_text("placeholder", encoding="utf-8")
    structure = tmp_path / "complex.xyz"
    structure.write_text("1\ncomment\nB 0 0 0\n", encoding="utf-8")
    received: dict[str, object] = {}
    working_directory_was_available = False

    class StubRunner:
        def execute(self, command, **kwargs):
            nonlocal working_directory_was_available
            received.update(kwargs)
            working_directory_was_available = Path(kwargs["working_directory"]).is_dir()
            return VinaProcessResult(tuple(command), 0, ":: total energy -1.000000 Eh ::\n", "")

    scorer_type(tmp_path, runner=StubRunner()).score_single_point(structure, charge=0, cpu_threads=1)

    assert "working_directory" in received
    assert working_directory_was_available
