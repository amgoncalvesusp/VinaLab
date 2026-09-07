"""Strict molecular readers; no coordinate optimization of supplied 3D input."""
import math
from pathlib import Path


def load_molecule(path):
    from rdkit import Chem
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".sdf", ".mol"}:
        if suffix == ".mol":
            mol = Chem.MolFromMolFile(str(path), removeHs=False)
        else:
            molecules = list(Chem.SDMolSupplier(str(path), removeHs=False))
            if len(molecules) != 1:
                raise ValueError("Expected exactly one molecule; split multi-molecule SDF first")
            mol = molecules[0]
    elif suffix == ".pdb":
        if path.read_text().count("MODEL ") > 1:
            raise ValueError("Expected a single PDB model")
        mol = Chem.MolFromPDBFile(str(path), removeHs=False)
    elif suffix == ".mol2":
        if path.read_text().upper().count("@<TRIPOS>MOLECULE") != 1:
            raise ValueError("Expected exactly one MOL2 molecule")
        mol = Chem.MolFromMol2File(str(path), removeHs=False)
    else:
        raise ValueError("Supported molecule formats: PDB, MOL2, SDF, MOL")
    if mol is None or not mol.GetNumAtoms():
        raise ValueError(f"Cannot parse molecular topology: {path.name}")
    if mol.GetNumConformers():
        validate_coordinates(mol.GetConformer().GetPositions())
    return mol


def validate_coordinates(coordinates):
    points = tuple(tuple(float(v) for v in xyz) for xyz in coordinates)
    if not points or any(len(p) != 3 or not all(math.isfinite(v) for v in p) for p in points):
        raise ValueError("Coordinates must be nonempty finite XYZ triples")
    return points


def read_coordinates(path):
    """Read one structure in Angstrom; refuses ambiguous multi-model files."""
    path = Path(path)
    if path.suffix.lower() == ".xyz":
        from vinalab_core.scoring.xyz import read_xyz
        return read_xyz(path).coordinates
    if path.suffix.lower() in {".pdb", ".pdbqt"}:
        text = path.read_text()
        if sum(line.startswith("MODEL") for line in text.splitlines()) > 1:
            raise ValueError("Select a single pose before reading coordinates")
        return validate_coordinates(
            (float(line[30:38]), float(line[38:46]), float(line[46:54]))
            for line in text.splitlines() if line.startswith(("ATOM  ", "HETATM")))
    mol = load_molecule(path)
    if not mol.GetNumConformers():
        raise ValueError("Molecule has no coordinates")
    return validate_coordinates(mol.GetConformer().GetPositions())
