"""Heavy-atom, graph-mapped RMSD in the unchanged receptor coordinate frame."""
from dataclasses import dataclass
from pathlib import Path

from vinalab_core.prepare.molecule import load_molecule, validate_coordinates


@dataclass(frozen=True, slots=True)
class PoseComparison:
    mode: int
    rmsd: float | None
    comparable: bool
    reason: str = ""


def split_pose_blocks(text):
    """Return complete single-pose PDBQT blocks, retaining global remarks."""
    lines = text.splitlines()
    if not any(line.startswith("MODEL") for line in lines):
        return (text,)
    blocks, current, header = [], None, []
    for line in lines:
        if line.startswith("MODEL"):
            if current is not None:
                raise ValueError("Nested MODEL records")
            current = list(header)
        elif line.startswith("ENDMDL"):
            if current is None:
                raise ValueError("ENDMDL without MODEL")
            blocks.append("\n".join(current) + "\n")
            current = None
        elif current is not None:
            current.append(line)
        elif not blocks:
            header.append(line)
    if current is not None:
        raise ValueError("Unterminated MODEL record")
    return tuple(blocks)


def fit_reference_coordinates(reference, coordinates, *, atom_map):
    """Copy reference heavy topology and install coordinates, WITHOUT alignment.

    atom_map[i] is the reference heavy-atom index for coordinates[i]. A complete
    explicit bijection is required; proximity is not evidence of atom identity.
    """
    from rdkit import Chem
    ref = load_molecule(reference) if isinstance(reference, (str, Path)) else reference
    result = Chem.RemoveHs(Chem.Mol(ref))
    points = validate_coordinates(coordinates)
    mapping = tuple(atom_map)
    if (len(points) != result.GetNumAtoms() or len(mapping) != len(points)
            or any(type(i) is not int for i in mapping)
            or set(mapping) != set(range(result.GetNumAtoms()))):
        raise ValueError("Atom mapping must be a complete heavy-atom bijection")
    conf = Chem.Conformer(result.GetNumAtoms())
    conf.Set3D(True)
    for index, xyz in zip(mapping, points):
        conf.SetAtomPosition(index, xyz)
    result.RemoveAllConformers()
    result.AddConformer(conf)
    return result


def _heavy(mol):
    from rdkit import Chem
    result = Chem.RemoveHs(Chem.Mol(mol))
    if not result.GetNumConformers():
        raise ValueError("Molecule has no coordinates")
    validate_coordinates(result.GetConformer().GetPositions())
    return result


def _graph_maps(probe, reference, max_matches=10000):
    from rdkit import Chem
    if (probe.GetNumAtoms() != reference.GetNumAtoms()
            or Chem.MolToSmiles(probe) != Chem.MolToSmiles(reference)):
        raise ValueError("Incompatible molecular topology, charge, or stereochemistry")
    matches = reference.GetSubstructMatches(probe, uniquify=False, useChirality=True, maxMatches=max_matches + 1)
    if not matches:
        raise ValueError("Unsupported topology mapping")
    if len(matches) > max_matches:
        raise ValueError("Topology symmetry mapping limit exceeded")
    return [list(enumerate(match)) for match in matches]


def pose_rmsd(probe, reference):
    from rdkit.Chem import rdMolAlign
    a, b = _heavy(probe), _heavy(reference)
    maps = _graph_maps(a, b)
    return float(rdMolAlign.CalcRMS(a, b, map=maps, symmetrizeConjugatedTerminalGroups=False))


def read_poses(path, reference_path=None):
    """Read SDF or mapped Meeko PDBQT; never infer bond order from distances."""
    from rdkit import Chem
    path = Path(path)
    if path.suffix.lower() == ".sdf":
        mols = tuple(Chem.SDMolSupplier(str(path), removeHs=False))
        if not mols or any(mol is None for mol in mols):
            raise ValueError("Invalid SDF pose record")
        return tuple(_heavy(mol) for mol in mols)
    if path.suffix.lower() != ".pdbqt":
        return (_heavy(load_molecule(path)),)
    poses = []
    reference = _heavy(load_molecule(reference_path)) if reference_path else None
    for block in split_pose_blocks(path.read_text()):
        poses.append(_read_pdbqt_block(block, reference))
    return tuple(poses)


def _read_pdbqt_block(block, reference=None):
    from meeko import PDBQTMolecule, RDKitMolCreate
    if "REMARK SMILES " not in block or "REMARK SMILES IDX" not in block:
        raise ValueError("PDBQT lacks topology/mapping metadata; supply Meeko SMILES/IDX or an explicit atom mapping")
    try:
        mols = RDKitMolCreate.from_pdbqt_mol(PDBQTMolecule(block, skip_typing=True))
        if len(mols) != 1 or mols[0] is None:
            raise ValueError("Expected exactly one mapped ligand")
        pose = _heavy(mols[0])
        if reference is not None:
            mapping = _graph_maps(pose, reference)[0]
            pose = fit_reference_coordinates(reference, pose.GetConformer().GetPositions(),
                atom_map=tuple(ref_index for _, ref_index in mapping))
        return pose
    except (RuntimeError, IndexError, KeyError) as exc:
        raise ValueError(f"Unsupported PDBQT topology mapping: {exc}") from exc


def validate_reference_poses(poses_path, reference_path):
    try:
        if Path(reference_path).suffix.lower() not in {".sdf", ".mol"}:
            raise ValueError("Reference requires explicit topology from SDF/MOL in the same receptor frame")
        reference = load_molecule(reference_path)
        if not reference.GetNumConformers() or not reference.GetConformer().Is3D():
            raise ValueError("Reference must have 3D coordinates in the same receptor frame")
        pdbqt = Path(poses_path).suffix.lower() == ".pdbqt"
        poses = split_pose_blocks(Path(poses_path).read_text()) if pdbqt else read_poses(poses_path)
    except (ValueError, OSError, RuntimeError) as exc:
        return (PoseComparison(1, None, False, str(exc)),)
    records = []
    for mode, pose in enumerate(poses, 1):
        try:
            if pdbqt:
                pose = _read_pdbqt_block(pose, _heavy(reference))
            records.append(PoseComparison(mode, pose_rmsd(pose, reference), True))
        except (ValueError, RuntimeError) as exc:
            records.append(PoseComparison(mode, None, False, str(exc)))
    return tuple(records)
