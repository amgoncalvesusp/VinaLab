"""Real format conversion regressions, including source/data preservation."""

from pathlib import Path

import pytest
from rdkit import Chem
from rdkit.Chem import AllChem
from openbabel import pybel

from core.converter import FileConverter
from core.file_utils import validate_ligand_pdbqt, validate_pdbqt_charges


def ligand_file(root, fmt, smiles="CC(=O)Oc1ccccc1C(=O)O", two_d=False):
    molecule = Chem.AddHs(Chem.MolFromSmiles(smiles))
    if two_d:
        AllChem.Compute2DCoords(molecule)
    else:
        assert AllChem.EmbedMolecule(molecule, randomSeed=42) == 0
    path = root / f"ligand.{fmt}"
    block = Chem.MolToMolBlock(molecule)
    if fmt == "pdb":
        path.write_text("REMARK header\n" * 90 + Chem.MolToPDBBlock(molecule))
    elif fmt == "mol2":
        path.write_text(pybel.readstring("mol", block).write("mol2"))
    else:
        path.write_text(block + "$$$$\n")
    return path, molecule


@pytest.mark.parametrize("fmt", ["pdb", "mol2", "sdf"])
@pytest.mark.parametrize("smiles", ["CC(=O)Oc1ccccc1C(=O)O", "C[N+](C)(C)CC(=O)[O-]", "CC(=O)NCCO"])
def test_real_ligand_formats(tmp_path, fmt, smiles):
    tmp_path = tmp_path / "conversão α"
    tmp_path.mkdir()
    source, molecule = ligand_file(tmp_path, fmt, smiles)
    original = source.read_bytes()
    result = FileConverter.auto_convert(source, "ligand")
    assert result.success, result.log + result.errors
    assert "Meeko" in result.log
    integrity = validate_ligand_pdbqt(result.output_path)
    assert integrity.heavy_atom_count == molecule.GetNumHeavyAtoms()
    assert validate_pdbqt_charges(result.output_path)
    assert source.read_bytes() == original


def test_two_dimensional_ligand_is_embedded(tmp_path):
    source, _ = ligand_file(tmp_path, "sdf", two_d=True)
    result = FileConverter.auto_convert(source, "ligand")
    assert result.success, result.errors
    atoms = FileConverter._pdbqt_atoms(result.output_path)
    assert max(a["xyz"][2] for a in atoms) - min(a["xyz"][2] for a in atoms) > 0.1


def test_receptor_with_long_header(tmp_path):
    peptide = Chem.AddHs(Chem.MolFromSequence("AG"))
    AllChem.EmbedMolecule(peptide, randomSeed=42)
    source = tmp_path / "receptor.pdb"
    source.write_text("REMARK header\n" * 90 + Chem.MolToPDBBlock(Chem.RemoveHs(peptide)))
    result = FileConverter.auto_convert(source, "receptor")
    assert result.success, result.log + result.errors
    assert validate_pdbqt_charges(result.output_path)


def test_conversion_never_overwrites_source(tmp_path):
    source, _ = ligand_file(tmp_path, "sdf")
    original = source.read_bytes()
    result = FileConverter._convert_ligand_rdkit_meeko(source, source, "sdf")
    assert not result.success
    assert source.read_bytes() == original


def test_failed_conversion_preserves_existing_output(tmp_path):
    source = tmp_path / "broken.pdb"
    source.write_text("ATOM invalid\n")
    output = tmp_path / "existing.pdbqt"
    output.write_text("previous result")
    result = FileConverter.convert_pdb_to_pdbqt_receptor(source, output)
    assert not result.success
    assert output.read_text() == "previous result"


def test_invalid_pdbqt_is_not_success(tmp_path):
    source = tmp_path / "bad.pdbqt"
    source.write_text("ROOT\nENDROOT\nTORSDOF 0\n")
    assert not FileConverter.auto_convert(source, "ligand").success


@pytest.mark.parametrize("fmt", ["mol2", "sdf"])
def test_receptor_intermediate_formats(tmp_path, fmt):
    peptide = Chem.AddHs(Chem.MolFromSequence("AG"))
    AllChem.EmbedMolecule(peptide, randomSeed=42)
    source = tmp_path / f"protein.{fmt}"
    molecule = pybel.readstring("pdb", Chem.MolToPDBBlock(peptide))
    source.write_text(molecule.write(fmt))
    result = FileConverter.auto_convert(source, "receptor")
    assert result.success, result.log + result.errors
    assert validate_pdbqt_charges(result.output_path)


def test_batch_duplicate_names_are_rejected_without_overwrite(tmp_path):
    from ui.converter_widget import ConversionWorker
    one, two = tmp_path / "one", tmp_path / "two"
    one.mkdir()
    two.mkdir()
    sources = [ligand_file(folder, "sdf")[0] for folder in (one, two)]
    worker = ConversionWorker(sources, tmp_path / "output", "ligand")
    results = []
    worker.finished_signal.connect(results.extend)
    worker.run()
    assert len(results) == 2
    assert all(not result.success for result in results)
    assert not (tmp_path / "output" / "ligand.pdbqt").exists()


def test_biovia_shifted_columns_are_normalized_without_moving_atoms(tmp_path):
    from core.receptor_input import normalize_receptor_pdb
    peptide = Chem.AddHs(Chem.MolFromSequence("AG"))
    AllChem.EmbedMolecule(peptide, randomSeed=42)
    pdb = Chem.MolToPDBBlock(Chem.RemoveHs(peptide))
    broken = "\n".join(line[:54] + "  -0.00" + line[60:] if line.startswith("ATOM") else line
                       for line in pdb.splitlines())
    fixed, count = normalize_receptor_pdb(broken)
    assert count == peptide.GetNumHeavyAtoms()
    assert [x[:54] for x in fixed.splitlines()] == [x[:54] for x in broken.splitlines()]
    source = tmp_path / "biovia.pdb"
    source.write_text(broken)
    result = FileConverter.auto_convert(source, "receptor")
    assert result.success, result.log + result.errors


@pytest.mark.parametrize("role", ["ligand", "receptor"])
def test_explicit_openbabel_handles_unicode_paths(tmp_path, role):
    directory = tmp_path / "conversão α"
    directory.mkdir()
    source, _ = ligand_file(directory, "sdf", smiles="CCO")
    result = FileConverter._convert_via_openbabel(source, directory / "out.pdbqt", role == "receptor", "explicit")
    assert result.success, result.errors


@pytest.mark.parametrize("element", ["Cl", "Br", "C"])
def test_shifted_element_identity(element):
    from core.receptor_input import normalize_receptor_pdb
    molecule = Chem.MolFromSmiles("C" + (element if element != "C" else "C"))
    AllChem.EmbedMolecule(molecule, randomSeed=42)
    text = Chem.MolToPDBBlock(molecule)
    shifted = "\n".join(line[:54] + "  -0.00" + line[60:] if line.startswith("HETATM") else line for line in text.splitlines())
    normalized, _ = normalize_receptor_pdb(shifted)
    restored = Chem.MolFromPDBBlock(normalized)
    assert restored is not None
    assert [a.GetAtomicNum() for a in restored.GetAtoms()] == [a.GetAtomicNum() for a in molecule.GetAtoms()]


@pytest.mark.parametrize("fields", ["  1.00100.00", "      100.00"])
def test_standard_pdb_numeric_fields(fields):
    from core.receptor_input import normalize_receptor_pdb
    line = "ATOM      1  CA  ALA A   1       0.000   0.000   0.000" + fields + "           C  "
    normalized, _ = normalize_receptor_pdb(line)
    assert float(normalized[60:66]) == 100
    assert normalized[76:78].strip() == "C"


def test_openbabel_2d_is_not_successfully_exported_as_flat(tmp_path):
    source, _ = ligand_file(tmp_path, "sdf", smiles="C1CCCCC1", two_d=True)
    result = FileConverter._convert_ligand_via_obabel(source, tmp_path / "out.pdbqt")
    assert not result.success or max(abs(a["xyz"][2]) for a in FileConverter._pdbqt_atoms(result.output_path)) > 0.1


@pytest.mark.parametrize("backend", ["meeko", "openbabel"])
def test_multirecord_receptor_rejected(tmp_path, backend):
    source, _ = ligand_file(tmp_path, "sdf")
    source.write_text(source.read_text() * 2)
    if backend == "meeko":
        result = FileConverter.convert_mol2_to_pdbqt_receptor(source, tmp_path / "out.pdbqt")
    else:
        result = FileConverter._convert_via_openbabel(source, tmp_path / "out.pdbqt", True, "explicit")
    assert not result.success


@pytest.mark.parametrize("name,role", [("receptor.pdb", "receptor_path"), ("ligand.sdf", "ligand_path")])
def test_smoke_rejects_input_inside_output_without_modifying_it(tmp_path, name, role):
    from core.release_smoke import run
    source = tmp_path / name
    source.write_text("original input")
    assert run(str(tmp_path), **{role: str(source)}) == 1
    assert source.read_text() == "original input"


@pytest.mark.parametrize("smiles", ["C[NH3+]", "CC(=O)[O-]"])
def test_missing_element_does_not_erase_formal_charge(smiles):
    from core.receptor_input import normalize_receptor_pdb
    molecule = Chem.AddHs(Chem.MolFromSmiles(smiles))
    AllChem.EmbedMolecule(molecule, randomSeed=42)
    original = Chem.MolToPDBBlock(molecule)
    missing = "\n".join(line[:76] + "  " + line[78:] if line.startswith("HETATM") else line for line in original.splitlines())
    normalized, _ = normalize_receptor_pdb(missing)
    restored = Chem.MolFromPDBBlock(normalized, removeHs=False)
    assert restored is not None
    assert [a.GetFormalCharge() for a in restored.GetAtoms()] == [a.GetFormalCharge() for a in molecule.GetAtoms()]


def test_meeko_flexible_macrocycle(tmp_path):
    source, _ = ligand_file(tmp_path, "sdf", smiles="C1CCCCCCCCCCC1")
    result = FileConverter.auto_convert(source, "ligand")
    assert result.success, result.errors
    assert "CG0" in result.output_path.read_text()
    assert "G0" in result.output_path.read_text()
    from core.file_utils import sanitize_pdbqt_for_vina
    sanitized = sanitize_pdbqt_for_vina(result.output_path, tmp_path, "ligand")
    assert not sanitized.changed
    from core.native_tools import find_vina_executable, native_tool_env
    import subprocess
    vina = find_vina_executable()
    assert vina is not None
    receptor = tmp_path / "receptor.pdbqt"
    receptor.write_text("ATOM      1  C   REC A   1       0.000   0.000   0.000  1.00  0.00     0.000 C\nEND\n")
    output = tmp_path / "docked.pdbqt"
    completed = subprocess.run([str(vina), "--receptor", str(receptor), "--ligand", str(result.output_path),
        "--center_x", "0", "--center_y", "0", "--center_z", "0", "--size_x", "20", "--size_y", "20", "--size_z", "20",
        "--exhaustiveness", "1", "--cpu", "1", "--seed", "42", "--num_modes", "1", "--out", str(output)],
        env=native_tool_env(vina), capture_output=True, text=True, timeout=90,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert completed.returncode == 0, completed.stderr
    assert "REMARK VINA RESULT:" in output.read_text()
