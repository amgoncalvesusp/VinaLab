
import pytest
from rdkit import Chem
from rdkit.Chem import AllChem

from vinalab_core.analysis.poses import (
    fit_reference_coordinates,
    pose_rmsd,
    read_poses,
    split_pose_blocks,
    validate_reference_poses,
)
from vinalab_core.analysis.pymol import export_pymol
from vinalab_core.prepare.conversion import convert_ligand, convert_receptor


def molecule(smiles="CCO"):
    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    assert AllChem.EmbedMolecule(mol, randomSeed=17) == 0
    return mol


@pytest.mark.parametrize("suffix", ["sdf", "pdb"])
def test_conversion_keeps_heavy_coordinates_and_topology(tmp_path, suffix):
    mol = molecule("c1ccccc1O")
    source = tmp_path / f"ligand.{suffix}"
    if suffix == "sdf":
        with Chem.SDWriter(str(source)) as writer:
            writer.write(mol)
    else:
        Chem.MolToPDBFile(mol, str(source))
    out = tmp_path / "ligand.pdbqt"
    result = convert_ligand(source, out)
    assert result.success, result.errors
    poses = read_poses(out)
    assert len(poses) == 1
    assert pose_rmsd(poses[0], mol) < .002
    assert "TORSDOF" in out.read_text()


def test_rmsd_does_not_superpose_or_mutate():
    ref = molecule()
    moved = Chem.Mol(ref)
    for i, p in enumerate(ref.GetConformer().GetPositions()):
        moved.GetConformer().SetAtomPosition(i, tuple(p + [3, 0, 0]))
    before = moved.GetConformer().GetPositions().copy()
    assert pose_rmsd(moved, ref) == pytest.approx(3)
    assert (moved.GetConformer().GetPositions() == before).all()


def test_graph_symmetry_and_wrong_topology():
    ref = molecule("CC(C)O")
    reordered = Chem.RenumberAtoms(ref, list(reversed(range(ref.GetNumAtoms()))))
    assert pose_rmsd(reordered, ref) < 1e-6
    with pytest.raises(ValueError, match="topology"):
        pose_rmsd(molecule("CCCO"), ref)


def test_coordinate_fit_requires_explicit_bijection():
    ref = molecule()
    positions = Chem.RemoveHs(ref).GetConformer().GetPositions()
    fitted = fit_reference_coordinates(ref, positions, atom_map=(0, 1, 2))
    assert pose_rmsd(fitted, ref) < 1e-6
    with pytest.raises(ValueError):
        fit_reference_coordinates(ref, positions, atom_map=(0, 0, 2))


def test_pdbqt_without_topology_fails_explicitly(tmp_path):
    file = tmp_path / "pose.pdbqt"
    file.write_text("ROOT\nATOM      1  C   LIG A   1       0.000   0.000   0.000  1.00  0.00     0.000 C\nENDROOT\nTORSDOF 0\n")
    with pytest.raises(ValueError, match="topology|mapping"):
        read_poses(file)


def test_pymol_paths_are_python_literals(tmp_path):
    source = tmp_path / 'a;quit.pdb'
    source.write_text("END\n")
    output = export_pymol(source, (), tmp_path / "view.pml")
    text = output.read_text()
    assert "python\n" in text
    assert "cmd.load(" in text
    compile(text.split("python\n", 1)[1].split("python end", 1)[0], "export", "exec")


@pytest.mark.parametrize("suffix", ["sdf", "mol2", "pdb"])
def test_receptor_binding_preserves_coordinates(tmp_path, suffix):
    from openbabel import openbabel as ob
    source = tmp_path / f"receptor.{suffix}"
    mol = molecule()
    converter = ob.OBConversion()
    converter.SetInAndOutFormats("mol", suffix)
    obmol = ob.OBMol()
    assert converter.ReadString(obmol, Chem.MolToMolBlock(mol))
    assert converter.WriteFile(obmol, str(source))
    converter.CloseOutFile()
    result = convert_receptor(source, tmp_path / "receptor.pdbqt")
    assert result.success, result.errors
    text = result.output_path.read_text()
    assert "ROOT" not in text and "TORSDOF" not in text
    from vinalab_core.prepare.molecule import read_coordinates
    assert len(read_coordinates(result.output_path)) >= 3


def test_conversion_will_not_overwrite(tmp_path):
    output = tmp_path / "protected.pdbqt"
    output.write_text("existing")
    result = convert_ligand(tmp_path / "missing.sdf", output)
    assert not result.success and "exists" in result.errors
    assert output.read_text() == "existing"


def test_mol2_ligand_and_multi_pose_reference(tmp_path):
    from openbabel import openbabel as ob
    mol = molecule("c1ccccc1O")
    source = tmp_path / "input.mol2"
    conversion = ob.OBConversion()
    conversion.SetInAndOutFormats("mol", "mol2")
    obmol = ob.OBMol()
    assert conversion.ReadString(obmol, Chem.MolToMolBlock(mol))
    source.write_text(conversion.WriteString(obmol))
    out = tmp_path / "ligand.pdbqt"
    assert convert_ligand(source, out).success
    reference = tmp_path / "ref.sdf"
    with Chem.SDWriter(str(reference)) as writer:
        writer.write(mol)
    text = out.read_text()
    multiple = tmp_path / "poses.pdbqt"
    multiple.write_text(f"MODEL 1\n{text}ENDMDL\nMODEL 2\n{text}ENDMDL\n")
    records = validate_reference_poses(multiple, reference)
    assert len(records) == 2
    assert all(r.comparable and r.rmsd < .002 for r in records)
    assert len(read_poses(reference)) == 1
    assert validate_reference_poses(multiple, source)[0].comparable is False


@pytest.mark.parametrize("text", ["MODEL 1\nMODEL 2\n", "MODEL 1\n", "ENDMDL\nMODEL 1\n"])
def test_bad_pose_blocks(text):
    with pytest.raises(ValueError):
        split_pose_blocks(text)


def test_readers_and_2d_generation(tmp_path):
    from vinalab_core.prepare.molecule import load_molecule, read_coordinates
    mol = Chem.MolFromSmiles("CCO")
    AllChem.Compute2DCoords(mol)
    source = tmp_path / "two.mol"
    Chem.MolToMolFile(mol, str(source))
    assert len(read_coordinates(source)) == 3
    assert len(read_poses(source)) == 1
    result = convert_ligand(source, tmp_path / "ligand.pdbqt")
    assert result.success and "Generated" in result.log
    for suffix, text in [("xyz", "1\nx\nH 0 0 0\n"), ("pdb", "MODEL 1\nMODEL 2\n"),
                         ("mol2", "bad"), ("csv", "bad"), ("sdf", "bad")]:
        path = tmp_path / f"bad.{suffix}"
        path.write_text(text)
        if suffix == "xyz":
            assert read_coordinates(path) == ((0., 0., 0.),)
        else:
            with pytest.raises(ValueError):
                load_molecule(path)
    with pytest.raises(ValueError):
        read_coordinates(tmp_path / "bad.pdb")


def test_conversion_failures_and_service(tmp_path):
    from vinalab_core.prepare.conversion import ConversionService, _validate_output
    source = tmp_path / "salt.mol"
    Chem.MolToMolFile(Chem.MolFromSmiles("CC.[Na+]"), str(source))
    assert not ConversionService.convert(source, tmp_path / "salt.pdbqt").success
    with pytest.raises(ValueError):
        ConversionService.convert(source, tmp_path / "salt.pdbqt", "invalid")
    assert not ConversionService.convert(source, source).success
    assert not ConversionService.convert(tmp_path / "bad.xyz", tmp_path / "receptor.pdbqt", "receptor").success
    assert not convert_receptor(tmp_path / "missing.pdb", tmp_path / "receptor.pdbqt").success
    atom = "ATOM      1  C   LIG A   1       0.000   0.000   0.000  1.00  0.00     0.000 C\n"
    with pytest.raises(ValueError, match="torsion"):
        _validate_output(atom, ligand=True)
    with pytest.raises(ValueError, match="rigid"):
        _validate_output(atom + "ROOT\n", ligand=False)
    with pytest.raises(ValueError, match="Nonfinite"):
        _validate_output(atom.replace("0.000 C", "  nan C"), ligand=False)


def test_pymol_launch_and_box(tmp_path, monkeypatch):
    from vinalab_core.analysis import pymol
    source = tmp_path / "a.pdb"
    source.write_text("END\n")
    calls = []
    monkeypatch.setattr(pymol.shutil, "which", lambda _: "pymol.exe")
    monkeypatch.setattr(pymol.subprocess, "Popen", lambda args, **kwargs: calls.append((args, kwargs)))
    script = pymol.launch_pymol(source, (source,), reference=source, search_box={"center": [0, 0, 0], "size": [10, 12, 14]})
    assert calls[0][1] == {"shell": False}
    assert "cmd.load_cgo" in script.read_text()
    monkeypatch.setattr(pymol.shutil, "which", lambda _: None)
    assert pymol.pymol_launch_arguments(script) is None
    with pytest.raises(ValueError):
        pymol.pymol_launch_arguments(source)
    with pytest.raises(ValueError):
        pymol.export_pymol(source, (), tmp_path / "x.pml", search_box={"center": [0, 0, 0], "size": [-1, 2, 3]})
    with pytest.raises(ValueError):
        pymol.export_pymol(source, (), tmp_path / "x.txt")
    with pytest.raises(ValueError):
        pymol.export_pymol(tmp_path / "missing.pdb", (), tmp_path / "x.pml")
    bad = tmp_path / "evil.py"
    bad.write_text("pass")
    with pytest.raises(ValueError):
        pymol.export_pymol(bad, (), tmp_path / "x.pml")
