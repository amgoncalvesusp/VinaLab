"""Real chemistry and failure-boundary checks for result complex exports."""

import os
from pathlib import Path
import subprocess
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from core.docking_engine import convert_with_obabel, find_obabel_executable
from core.native_tools import native_tool_env
from tabs.results_dialogs import ExportComplexDialog, ExportWorker


APP = QApplication.instance() or QApplication([])


def atom_coordinates(text):
    return np.array([
        [float(line[start:start + 8]) for start in (30, 38, 46)]
        for line in text.splitlines() if line.startswith(("ATOM  ", "HETATM"))
    ])


def read_molecule(path):
    from openbabel import openbabel as ob
    conversion = ob.OBConversion()
    assert conversion.SetInFormat(path.suffix[1:])
    molecule = ob.OBMol()
    assert conversion.ReadString(molecule, path.read_text(encoding="utf-8"))
    coordinates = np.array([
        [atom.GetX(), atom.GetY(), atom.GetZ()] for atom in ob.OBMolAtomIter(molecule)
    ])
    return molecule, coordinates


@pytest.fixture
def chemistry(tmp_path):
    """Generate a real peptide and Meeko ligand, including two distinct poses."""
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from meeko import MoleculePreparation, PDBQTWriterLegacy

    assert find_obabel_executable(), "Real Open Babel CLI is required for this suite"
    peptide = Chem.AddHs(Chem.MolFromSequence("AG"))
    assert AllChem.EmbedMolecule(peptide, randomSeed=42) == 0
    executable = Path(find_obabel_executable())
    result = subprocess.run(
        [str(executable), "-ipdb", "-opdbqt", "-xr"],
        input=Chem.MolToPDBBlock(peptide), capture_output=True, text=True,
        env=native_tool_env(executable), timeout=30,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert result.returncode == 0 and "ATOM" in result.stdout, result.stderr
    receptor = tmp_path / "receptor.pdbqt"
    receptor.write_text(result.stdout, encoding="utf-8")
    ligand = Chem.AddHs(Chem.MolFromSmiles("CCO"))
    assert AllChem.EmbedMolecule(ligand, randomSeed=73) == 0
    setups = MoleculePreparation().prepare(ligand)
    pose, success, error = PDBQTWriterLegacy.write_string(setups[0])
    assert success, error
    second_pose = "\n".join(
        line[:30] + f"{float(line[30:38]) + 8:8.3f}" + line[38:]
        if line.startswith(("ATOM", "HETATM")) else line
        for line in pose.splitlines()
    ) + "\n"
    docking = tmp_path / "docking.pdbqt"
    docking.write_text(f"MODEL 1\n{pose}ENDMDL\nMODEL 2\n{second_pose}ENDMDL\n")
    return dict(
        row=dict(_export_name="ethanol_vina_pose2", ligand_name="ethanol", mode=2,
                 affinity=-1.0, scoring_key="vina", output_file=str(docking),
                 receptor_file=str(receptor)),
        receptor=result.stdout, pose=second_pose,
    )


@pytest.mark.parametrize("format_name", ["pdbqt", "pdb", "mol2"])
def test_real_complex_contains_receptor_and_selected_pose(chemistry, tmp_path, format_name):
    output = tmp_path / "exports"
    worker = ExportWorker([chemistry["row"]], output, format_name, True, "en")
    completed = []
    worker.completed.connect(lambda *args: completed.append(args))
    worker.run()
    assert completed == [(1, "", False)]
    base = chemistry["row"]["_export_name"]
    complex_format = "mol2" if format_name == "mol2" else "pdb"
    complex_path = output / f"{base}_complex.{complex_format}"
    assert complex_path.is_file(), "The selected format must contain the full complex"
    molecule, xyz = read_molecule(complex_path)
    receptor_xyz = atom_coordinates(chemistry["receptor"])
    ligand_xyz = atom_coordinates(chemistry["pose"])
    expected = np.concatenate([receptor_xyz, ligand_xyz])
    assert molecule.NumAtoms() == len(expected)
    np.testing.assert_allclose(xyz, expected, atol=0.00051, rtol=0)
    _, pose_xyz = read_molecule(output / f"{base}.{format_name}")
    np.testing.assert_allclose(pose_xyz, ligand_xyz, atol=0.00051, rtol=0)
    if format_name == "mol2":
        from openbabel import openbabel as ob
        for bond in ob.OBMolBondIter(molecule):
            assert (bond.GetBeginAtomIdx() <= len(receptor_xyz)) == (
                bond.GetEndAtomIdx() <= len(receptor_xyz)
            ), "No covalent receptor-ligand bonds may be invented"


@pytest.mark.parametrize("format_name", ["pdb", "mol2"])
def test_real_conversion_accepts_unicode_paths(chemistry, tmp_path, format_name):
    folder = tmp_path / "exporta\u00e7\u00e3o \u03b1"
    folder.mkdir()
    source = folder / "posi\u00e7\u00e3o.pdbqt"
    source.write_text(chemistry["pose"], encoding="utf-8")
    target = folder / ("sa\u00edda." + format_name)
    assert convert_with_obabel(source, target) == target
    _, xyz = read_molecule(target)
    np.testing.assert_allclose(xyz, atom_coordinates(chemistry["pose"]), atol=0.00051, rtol=0)


@pytest.mark.parametrize("format_name", ["pdb", "mol2"])
def test_real_zero_molecules_is_failure_and_preserves_target(tmp_path, format_name):
    source = tmp_path / "empty.pdbqt"
    source.write_text("REMARK no atoms\n")
    target = tmp_path / ("existing." + format_name)
    target.write_text("existing user data")
    with pytest.raises((ValueError, RuntimeError), match="(?i)atom|molecul|empty"):
        convert_with_obabel(source, target)
    assert target.read_text() == "existing user data"


@pytest.mark.parametrize("failure", ["empty", "missing", "partial", "moved", "exit", "timeout"])
def test_conversion_failure_never_publishes_partial_output(chemistry, tmp_path, failure):
    source = Path(chemistry["row"]["receptor_file"])
    target = tmp_path / "existing.pdb"
    target.write_text("previous export")

    def fake_run(args, **kwargs):
        assert kwargs["timeout"] == 120
        assert kwargs["env"]
        path = Path(args[args.index("-O") + 1])
        if not path.is_absolute():
            path = Path(kwargs["cwd"]) / path
        if failure == "timeout":
            path.write_text("partial")
            raise subprocess.TimeoutExpired(args, 120)
        if failure == "partial":
            path.write_text("\n".join(chemistry["receptor"].splitlines()[:1]) + "\n")
        elif failure == "moved":
            path.write_text("\n".join(
                line[:30] + f"{float(line[30:38]) + 1:8.3f}" + line[38:]
                if line.startswith(("ATOM", "HETATM")) else line
                for line in chemistry["receptor"].splitlines()
            ))
        elif failure != "missing":
            path.write_text("")
        return subprocess.CompletedProcess(args, 1 if failure == "exit" else 0,
                                           "", "native conversion failed" if failure == "exit" else "")

    with patch("core.docking_engine.subprocess.run", side_effect=fake_run):
        with pytest.raises((ValueError, RuntimeError)):
            convert_with_obabel(source, target)
    assert target.read_text() == "previous export"


def test_worker_missing_receptor_publishes_nothing(chemistry, tmp_path):
    row = {**chemistry["row"], "receptor_file": ""}
    output = tmp_path / "exports"
    worker = ExportWorker([row], output, "mol2", True, "en")
    completed = []
    worker.completed.connect(lambda *args: completed.append(args))
    worker.run()
    assert completed[0][0] == 0 and completed[0][1]
    assert list(output.iterdir()) == []


def test_mol2_preview_and_collision_match_actual_complex(chemistry, tmp_path):
    dialog = ExportComplexDialog([chemistry["row"]], lang="en")
    dialog.all_radio.setChecked(True)
    dialog.format_combo.setCurrentText("mol2")
    dialog.folder_edit.setText(str(tmp_path))
    assert "_complex.mol2" in dialog.preview_label.text()
    assert "MOL2" in dialog.complex_checkbox.text()
    assert "{format}" not in dialog.complex_checkbox.text()
    old_path = tmp_path / (chemistry["row"]["_export_name"] + "_complex.mol2")
    old_path.write_text("existing")
    assert dialog._planned_rows()[0]["_export_name"].endswith("_2")
    dialog.close()


@pytest.mark.parametrize("format_name", ["pdb", "mol2"])
def test_public_complex_api(chemistry, tmp_path, format_name):
    from core.complex_export import export_complex
    pose = tmp_path / "selected.pdbqt"
    pose.write_text(chemistry["pose"])
    target = tmp_path / ("complex." + format_name)
    assert export_complex(Path(chemistry["row"]["receptor_file"]), pose, target) == target
    molecule, xyz = read_molecule(target)
    expected = np.concatenate([atom_coordinates(chemistry["receptor"]),
                               atom_coordinates(chemistry["pose"])])
    assert molecule.NumAtoms() == len(expected)
    np.testing.assert_allclose(xyz, expected, atol=0.00051, rtol=0)


@pytest.mark.parametrize("format_name", ["pdb", "mol2"])
def test_optional_private_inputs(tmp_path, format_name):
    """Opt-in local reproduction; never copy private inputs into the repository."""
    from core.complex_export import export_complex
    directory = os.environ.get("VINALAB_EXPORT_INPUT_DIR")
    if not directory:
        pytest.skip("Set VINALAB_EXPORT_INPUT_DIR for private local chemistry validation")
    receptor = Path(directory) / "receptor.pdbqt"
    ligand = Path(directory) / "ligand.pdbqt"
    target = tmp_path / ("complex." + format_name)
    export_complex(receptor, ligand, target)
    _, xyz = read_molecule(target)
    expected = np.concatenate([atom_coordinates(receptor.read_text()), atom_coordinates(ligand.read_text())])
    np.testing.assert_allclose(xyz, expected, atol=0.00051, rtol=0)


def test_publish_collision_rolls_back_only_current_row(chemistry, tmp_path):
    output = tmp_path / "exports"
    output.mkdir()
    base = chemistry["row"]["_export_name"]
    collision = output / (base + "_complex.pdb")
    collision.write_text("existing complex")
    worker = ExportWorker([chemistry["row"]], output, "pdb", True, "en")
    result = []
    worker.completed.connect(lambda *args: result.append(args))
    worker.run()
    assert result[0][0] == 0 and result[0][1]
    assert list(output.iterdir()) == [collision]
    assert collision.read_text() == "existing complex"


@pytest.mark.parametrize("format_name", ["pdb", "mol2"])
def test_worker_unicode_source_and_output_paths(chemistry, tmp_path, format_name):
    folder = tmp_path / "mol\u00e9culas \u03b1"
    folder.mkdir()
    receptor = folder / "prote\u00edna.pdbqt"
    receptor.write_text(chemistry["receptor"], encoding="utf-8")
    docking = folder / "posi\u00e7\u00e3o.pdbqt"
    docking.write_bytes(Path(chemistry["row"]["output_file"]).read_bytes())
    row = {**chemistry["row"], "receptor_file": str(receptor), "output_file": str(docking),
           "_export_name": "liga\u00e7\u00e3o"}
    output = folder / "sa\u00edda"
    worker = ExportWorker([row], output, format_name, True, "en")
    completed = []
    worker.completed.connect(lambda *args: completed.append(args))
    worker.run()
    assert completed == [(1, "", False)]
    _, xyz = read_molecule(output / (row["_export_name"] + "_complex." + format_name))
    np.testing.assert_allclose(xyz, np.concatenate([atom_coordinates(chemistry["receptor"]),
                                                   atom_coordinates(chemistry["pose"])]),
                               atol=0.00051, rtol=0)


def test_validation_rejects_changed_coordinates_and_elements(chemistry):
    from core.complex_export import ExportAtom, read_export_atoms, validate_export_atoms
    atoms = read_export_atoms(chemistry["pose"], "pdbqt")
    moved = (ExportAtom(atoms[0].element, (99.0, 0.0, 0.0)), *atoms[1:])
    with pytest.raises(ValueError, match="coordinates"):
        validate_export_atoms(moved, chemistry["pose"], "pdbqt")
    changed = (ExportAtom("ZN", atoms[0].xyz), *atoms[1:])
    with pytest.raises(ValueError, match="element"):
        validate_export_atoms(changed, chemistry["pose"], "pdbqt")
    with pytest.raises(ValueError, match="one molecular model"):
        read_export_atoms("MODEL 1\n" + chemistry["pose"] + "MODEL 2\n" + chemistry["pose"], "pdbqt")


@pytest.mark.parametrize("corruption", ["count", "duplicate", "endpoint", "nan", "record", "section"])
def test_mol2_validation_rejects_corruption(corruption):
    from core.complex_export import read_export_atoms
    text = ("@<TRIPOS>MOLECULE\ntest\n2 1 0 0 0\nSMALL\nUSER_CHARGES\n\n"
            "@<TRIPOS>ATOM\n1 C1 0 0 0 C.3 1 LIG 0.1\n2 C2 1.5 0 0 C.3 1 LIG -0.1\n"
            "@<TRIPOS>BOND\n1 1 2 1\n")
    replacements = {
        "count": ("2 1 0 0 0", "3 1 0 0 0"),
        "duplicate": ("2 C2", "1 C2"),
        "endpoint": ("1 1 2 1", "1 1 3 1"),
        "nan": ("LIG 0.1", "LIG nan"),
        "record": ("C.3 1 LIG 0.1", "C.3"),
        "section": ("@<TRIPOS>BOND", "@<TRIPOS>ATOM"),
    }
    with pytest.raises(ValueError):
        read_export_atoms(text.replace(*replacements[corruption]), "mol2")


def test_public_api_rejects_overwriting_input_and_invalid_format(chemistry, tmp_path):
    from core.complex_export import export_complex
    receptor = Path(chemistry["row"]["receptor_file"])
    pose = tmp_path / "pose.pdb"
    pose.write_text("original")
    with pytest.raises(ValueError, match="overwrite"):
        export_complex(receptor, pose, pose)
    with pytest.raises(ValueError, match=".pdb or .mol2"):
        export_complex(receptor, pose, tmp_path / "complex.xyz")
    assert pose.read_text() == "original"


def test_missing_cli_has_clear_error_and_keeps_existing(chemistry, tmp_path):
    target = tmp_path / "existing.pdb"
    target.write_text("original")
    with patch("core.docking_engine.find_obabel_executable", return_value=None):
        with pytest.raises(RuntimeError, match="OpenBabel"):
            convert_with_obabel(Path(chemistry["row"]["receptor_file"]), target)
    assert target.read_text() == "original"


@pytest.fixture
def macrocycle():
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from meeko import MoleculePreparation, PDBQTWriterLegacy
    molecule = Chem.AddHs(Chem.MolFromSmiles("C1CCCCCCCCCCC1"))
    assert AllChem.EmbedMolecule(molecule, randomSeed=42) == 0
    setup = MoleculePreparation().prepare(molecule)[0]
    text, success, error = PDBQTWriterLegacy.write_string(setup)
    assert success, error
    assert "CG0" in text and " G0" in text
    return text


@pytest.mark.parametrize("closure", range(4))
@pytest.mark.parametrize("format_name", ["pdbqt", "pdb", "mol2"])
def test_macrocycle_exports_physical_atoms_only(chemistry, macrocycle, tmp_path, format_name, closure):
    from core.complex_export import read_export_atoms
    pose = macrocycle.replace("CG0", f"CG{closure}").replace(" G0", f" G{closure}")
    physical = "\n".join(line for line in pose.splitlines()
                         if line.startswith(("ATOM  ", "HETATM")) and line.split()[-1] != f"G{closure}")
    expected_pose = atom_coordinates(physical)
    assert len(expected_pose) == 12
    source = tmp_path / "macrocycle.pdbqt"
    source.write_text(pose)
    row = {**chemistry["row"], "mode": 1, "output_file": str(source), "_export_name": "macrocycle"}
    output = tmp_path / "exports"
    worker = ExportWorker([row], output, format_name, True, "en")
    result = []
    worker.completed.connect(lambda *args: result.append(args))
    worker.run()
    assert result == [(1, "", False)]
    atoms = read_export_atoms(pose, "pdbqt")
    assert len(atoms) == 12 and all(atom.element == "C" for atom in atoms)
    complex_format = "mol2" if format_name == "mol2" else "pdb"
    _, xyz = read_molecule(output / ("macrocycle_complex." + complex_format))
    np.testing.assert_allclose(xyz, np.concatenate([atom_coordinates(chemistry["receptor"]), expected_pose]),
                               atol=0.00051, rtol=0)
    if format_name == "pdbqt":
        assert f" G{closure}" in (output / "macrocycle.pdbqt").read_text()
    else:
        molecule, xyz = read_molecule(output / ("macrocycle." + format_name))
        assert molecule.NumAtoms() == 12
        np.testing.assert_allclose(xyz, expected_pose, atol=0.00051, rtol=0)
    assert source.read_text() == pose


@pytest.mark.parametrize("format_name", ["pdb", "mol2"])
def test_macrocycle_native_staging_has_no_torsion_or_ghost_records(macrocycle, tmp_path, format_name):
    source = tmp_path / "macrocycle.pdbqt"
    source.write_text(macrocycle)
    native_run = subprocess.run

    def inspect_run(args, **kwargs):
        staged = Path(kwargs["cwd"]) / args[1]
        assert staged.suffix == ".pdb"
        text = staged.read_text()
        assert not any(token in text for token in ("ROOT", "BRANCH", "TORSDOF", "CG0", " G0"))
        assert len(atom_coordinates(text)) == 12
        return native_run(args, **kwargs)

    with patch("core.docking_engine.subprocess.run", side_effect=inspect_run):
        convert_with_obabel(source, tmp_path / ("macrocycle." + format_name))
