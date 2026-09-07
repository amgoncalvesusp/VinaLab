import os
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from vinalab_core.docking.docking_service import DockingService
from vinalab_core.docking.search_box import SearchBox
from vinalab_core.docking.vina_runner import VinaProcessResult
from vinalab_core.io.project_store import ProjectStore
from vinalab_core.prepare.pdbqt_validator import PdbqtValidator
from vinalab_core.tools import tool_locator

ATOM = "ATOM      1  C1  LIG A   1       1.000   2.000   3.000  0.00  0.00     0.100 C\n"
LIGAND = "ROOT\n" + ATOM + "ENDROOT\nTORSDOF 0\n"


def box():
    return SearchBox((0, 0, 0), (20, 20, 20), "test", 0, "user")


@pytest.mark.parametrize("field", ["center", "size", "margin"])
@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_box_rejects_nonfinite(field, value):
    args = {
        "center": (0, 0, 0), "size": (20, 20, 20), "margin": 0, "coordinate_frame": "test", "source": "user"
    }
    args[field] = value if field == "margin" else (value, 1, 1)
    with pytest.raises(ValueError):
        SearchBox(**args)


@pytest.mark.parametrize(
    "text",
    [
        ATOM[:46] + "     nan" + ATOM[54:],
        ATOM[:70] + "   nan" + ATOM[76:],
        ATOM.rstrip()[:-1] + "NotAnAtom\n",
    ],
)
def test_invalid_pdbqt_fields(text):
    assert not PdbqtValidator().validate_text(text).ok


def test_pdbqt_roles():
    validator = PdbqtValidator()
    assert validator.validate_text(ATOM, role="receptor").ok
    assert validator.validate_text(LIGAND, role="ligand").ok
    assert not validator.validate_text(ATOM, role="ligand").ok
    assert not validator.validate_text(LIGAND, role="receptor").ok


@pytest.mark.parametrize("atom_type", ["CG0", "CG3", "G0", "G3", "At", "Na", "K", "U"])
def test_vina_special_atom_types_are_recognized(atom_type):
    assert PdbqtValidator().validate_text(ATOM.replace(" C\n", f" {atom_type}\n")).ok


def test_ligand_input_must_not_be_output_models():
    assert not PdbqtValidator().validate_text("MODEL 1\n" + LIGAND + "ENDMDL\n", role="ligand").ok


def test_fixed_width_adjacent_negative_coordinates():
    assert PdbqtValidator().validate_text(ATOM[:30] + "-999.999-999.999-999.999" + ATOM[54:]).ok


@pytest.mark.parametrize(
    "torsions",
    [
        "ROOT\nENDROOT\nTORSDOF -1\n",
        "ENDROOT\nROOT\nTORSDOF 0\n",
        "ROOT\nENDROOT\nBRANCH 1 2\nTORSDOF 1\n",
        "ROOT\nENDROOT\nENDBRANCH 1 2\nTORSDOF 1\n",
        "ROOT\nENDROOT\nBRANCH x y\nTORSDOF 1\n",
    ],
)
def test_bad_torsion_records(torsions):
    assert not PdbqtValidator().validate_text(ATOM + torsions, role="ligand").ok


def test_nested_branch_matching():
    text = LIGAND.replace(
        "TORSDOF 0", "BRANCH 1 2\nBRANCH 2 3\nENDBRANCH 2 3\nENDBRANCH 1 2\nTORSDOF 2"
    )
    assert PdbqtValidator().validate_text(text, role="ligand").ok


@pytest.mark.parametrize(
    "change",
    [
        {"cpu_threads": 0},
        {"cpu_threads": 1.5},
        {"exhaustiveness": 0},
        {"num_modes": 0},
        {"scoring": "bad"},
        {"energy_range": float("nan")},
    ],
)
def test_command_rejects_invalid_settings(change):
    from vinalab_core.docking.vina_engine import VinaCommandBuilder

    args = {
        "receptor": "r",
        "ligand": "l",
        "output": "o",
        "search_box": box(),
        "cpu_threads": 1,
        "exhaustiveness": 1,
        "seed": 1,
    }
    with pytest.raises(ValueError):
        VinaCommandBuilder("vina").build(**(args | change))


@pytest.mark.parametrize(
    "text", ["MODEL 2\n" + LIGAND + "ENDMDL", "MODEL 1\n" + LIGAND, "ENDMDL", LIGAND]
)
def test_invalid_output_models(text):
    from vinalab_core.docking.docking_service import _output_models

    with pytest.raises(ValueError):
        _output_models(text)


@pytest.mark.parametrize("text", ["0 -1 0 0", "1 -1 -1 0", "1 -1 2 1", "1 -1 0 0\n1 -1 0 0"])
def test_invalid_pose_tables(text):
    from vinalab_core.docking.vina_results import VinaResultsParser

    assert VinaResultsParser().parse(text) == ()


def test_posix_rejects_windows_and_nonexecutable(tmp_path, monkeypatch):
    monkeypatch.setattr(
        tool_locator,
        "os",
        SimpleNamespace(name="posix", access=lambda p, mode: str(p).endswith("linux"), X_OK=1),
    )
    monkeypatch.setattr(tool_locator.shutil, "which", lambda _: None)
    directory = tmp_path / "tools/vina"
    directory.mkdir(parents=True)
    for name in ["vina.exe", "vina_1_win.exe", "vina"]:
        (directory / name).touch()
    assert tool_locator.ToolLocator(tmp_path).find("vina") is None
    (directory / "vina_linux").touch()
    assert tool_locator.ToolLocator(tmp_path).find("vina") == directory / "vina_linux"


def test_posix_conda_and_path_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(
        tool_locator, "os", SimpleNamespace(name="posix", access=lambda *_: True, X_OK=1)
    )
    prefix = tmp_path / "conda"
    executable = prefix / "bin/vina"
    executable.parent.mkdir(parents=True)
    executable.touch()
    monkeypatch.setattr(tool_locator.shutil, "which", lambda _: None)
    assert tool_locator.ToolLocator(tmp_path, prefix).find("vina") == executable
    monkeypatch.setattr(tool_locator.shutil, "which", lambda _: str(executable))
    assert tool_locator.ToolLocator(tmp_path).find("vina") == executable


def test_windows_path_exe_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(tool_locator, "os", SimpleNamespace(name="nt"))
    executable = tmp_path / "vina.exe"
    executable.touch()
    monkeypatch.setattr(
        tool_locator.shutil,
        "which",
        lambda name: str(executable) if name.endswith(".exe") else None,
    )
    assert tool_locator.ToolLocator(tmp_path).find("vina") == executable


def test_service_preserves_process_failure(tmp_path):
    receptor, ligand, output = (tmp_path / name for name in ("r", "l", "out"))
    receptor.write_text(ATOM)
    ligand.write_text(LIGAND)

    class Runner:
        def execute(self, command, **kwargs):
            return VinaProcessResult(tuple(command), 1, "1 -1 0 0", "engine failed")

    result = DockingService("vina", runner=Runner()).run(
        receptor=receptor,
        ligand=ligand,
        output=output,
        search_box=box(),
        cpu_threads=1,
        exhaustiveness=1,
        seed=1,
    )
    assert not result.ok
    assert result.poses == ()
    assert result.process.stderr == "engine failed"


@pytest.mark.parametrize(
    "output_text,stdout,ok",
    [
        (None, "1 -1 0 0", False),
        (LIGAND, "", False),
        ("garbage", "1 -1 0 0", False),
        ("MODEL 1\n" + LIGAND + "ENDMDL\n", "1 -1 0 0", True),
    ],
)
def test_service_requires_new_valid_output(tmp_path, output_text, stdout, ok):
    receptor, ligand, output = (tmp_path / name for name in ("r.pdbqt", "l.pdbqt", "out.pdbqt"))
    receptor.write_text(ATOM)
    ligand.write_text(LIGAND)

    class Runner:
        def execute(self, command, **kwargs):
            if output_text is not None:
                output.write_text(output_text)
            return VinaProcessResult(tuple(command), 0, stdout, "")

    result = DockingService("vina", runner=Runner()).run(
        receptor=receptor,
        ligand=ligand,
        output=output,
        search_box=box(),
        cpu_threads=1,
        exhaustiveness=1,
        seed=1,
        scoring="vinardo",
    )
    assert result.ok is ok


def test_store_new_fields_and_status(tmp_path):
    with ProjectStore(tmp_path / "project.sqlite") as store:
        first = store.create_run(
            receptor_hash="r", search_box=box(), engine_key="vina", seed=1, cpu_threads=1
        )
        run = store.create_run(
            receptor_hash="r",
            ligand_hash="l",
            receptor_path="r.pdbqt",
            ligand_path="l.pdbqt",
            output_path="out.pdbqt",
            search_box=box(),
            engine_key="vina",
            seed=1,
            cpu_threads=1,
            scoring="vinardo",
            exhaustiveness=16,
            num_modes=4,
            metadata={"source": "test"},
        )
        store.update_run_status(run.id, "failed", error="failure", stdout="log", stderr="err")
        assert store.list_runs()[0].id == run.id
        assert store.get_run(run.id).error == "failure"
        assert store.get_run(run.id).metadata == {"source": "test"}
        assert store.get_output_path(run.id) == Path("out.pdbqt")
        assert store.get_run(first.id).scoring == "vina"


def test_migrate_original_schema(tmp_path):
    path = tmp_path / "old.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE runs (id TEXT PRIMARY KEY, receptor_hash TEXT NOT NULL, center_x REAL, center_y REAL, center_z REAL, size_x REAL, size_y REAL, size_z REAL, coordinate_frame TEXT, margin REAL, box_source TEXT, engine_key TEXT, seed INTEGER, cpu_threads INTEGER, created_at TEXT)"
        )
        connection.execute(
            "INSERT INTO runs VALUES ('old', 'r', 0,0,0,20,20,20,'r',0,'user','vina',1,1,'2026-01-01T00:00:00+00:00')"
        )
    for _ in range(2):
        with ProjectStore(path) as store:
            old = store.get_run("old")
            assert old.status == "unknown"
            assert old.output_path == ""
            assert store.get_output_path("old") is None
            assert old.metadata == {}


def test_store_reopens_and_preserves_logs(tmp_path):
    path = tmp_path / "project.sqlite"
    with ProjectStore(path) as store:
        run = store.create_run(
            run_id="custom-id",
            receptor_hash="r",
            search_box=box(),
            engine_key="vina",
            seed=1,
            cpu_threads=1,
            stdout="before",
            metadata={"nested": [1]},
        )
        store.update_run_status(run.id, "running")
    with ProjectStore(path) as store:
        assert store.get_run(run.id).stdout == "before"
        assert store.get_run(run.id).status == "running"
        with pytest.raises(KeyError):
            store.update_run_status("missing", "failed")
        with pytest.raises(ValueError):
            store.update_run_status(run.id, "typo")


@pytest.mark.parametrize(
    "receptor_text,ligand_text,existing,exception",
    [
        (ATOM, LIGAND, True, FileExistsError),
        ("bad", LIGAND, False, ValueError),
        (ATOM, ATOM, False, ValueError),
        (ATOM, LIGAND.replace(" C\n", " B\n"), False, ValueError),
    ],
)
def test_service_rejects_before_execution(
    tmp_path, receptor_text, ligand_text, existing, exception
):
    receptor, ligand, output = (tmp_path / name for name in ("r", "l", "out"))
    receptor.write_text(receptor_text)
    ligand.write_text(ligand_text)
    if existing:
        output.write_text("old result")

    class Runner:
        def execute(self, *args, **kwargs):
            pytest.fail("invalid request reached Vina")

    with pytest.raises(exception):
        DockingService("vina", runner=Runner()).run(
            receptor=receptor,
            ligand=ligand,
            output=output,
            search_box=box(),
            cpu_threads=1,
            exhaustiveness=1,
            seed=1,
        )
    if existing:
        assert output.read_text() == "old result"


@pytest.mark.parametrize("scoring", ["vina", "vinardo"])
def test_real_vina_cli_smoke(tmp_path, scoring):
    executable = os.environ.get("VINALAB_TEST_VINA")
    if not executable:
        pytest.skip("Set VINALAB_TEST_VINA to a native Vina executable")
    receptor, ligand, output = (tmp_path / name for name in ("r.pdbqt", "l.pdbqt", "out.pdbqt"))
    receptor.write_text(ATOM)
    ligand.write_text(LIGAND)
    result = DockingService(executable).run(
        receptor=receptor,
        ligand=ligand,
        output=output,
        search_box=box(),
        cpu_threads=1,
        exhaustiveness=1,
        seed=42,
        scoring=scoring,
        num_modes=1,
        timeout_seconds=60,
    )
    assert result.ok, (result.process.stderr, result.errors, result.process.stdout)
    assert len(result.poses) == 1
    assert output.is_file()
