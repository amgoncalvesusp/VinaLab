"""Structural validation and assembly, without re-docking or geometry changes.

PDBQT has incomplete chemical topology. MOL2 types/bond orders are perceived by
Open Babel separately for each component; they are not a recovered force field.
Only physical atoms present in the docking inputs are exported (no added
hydrogens). Meeko G0-G3 closure pseudoatoms are omitted and CG0-CG3 are carbon.
Macrocycles use plain PDB staging: topology and MOL2 charges are re-perceived,
not reconstructed from the original molecular graph or PDBQT partial charges.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import tempfile


MACROCYCLE_GHOST_TYPES = frozenset(f"G{index}" for index in range(4))
MACROCYCLE_CARBON_TYPES = frozenset(f"CG{index}" for index in range(4))


@dataclass(frozen=True)
class ExportAtom:
    element: str
    xyz: tuple[float, float, float]


def _mol2_sections(text: str) -> dict[str, tuple[str, ...]]:
    sections: dict[str, tuple[str, ...]] = {}
    for block in text.split("@<TRIPOS>")[1:]:
        lines = block.splitlines()
        section = lines[0].strip()
        if section in sections:
            raise ValueError("Expected one MOL2 molecule with unique sections.")
        sections[section] = tuple(line for line in lines[1:] if line.strip() and not line.startswith("#"))
    return sections


def _mol2_tables(text: str) -> tuple[tuple[tuple[str, ...], ...], tuple[tuple[str, ...], ...]]:
    sections = _mol2_sections(text)
    try:
        counts = sections["MOLECULE"][1].split()
        atoms = tuple(tuple(line.split()) for line in sections["ATOM"])
        bonds = tuple(tuple(line.split()) for line in sections.get("BOND", ()))
        if len(atoms) != int(counts[0]) or len(bonds) != int(counts[1]):
            raise ValueError("MOL2 atom/bond counts disagree with the header.")
        if any(len(atom) < 9 for atom in atoms) or any(len(bond) < 4 for bond in bonds):
            raise ValueError("Incomplete MOL2 atom/bond record.")
        atom_ids = {int(atom[0]) for atom in atoms}
        bond_ids = {int(bond[0]) for bond in bonds}
        if len(atom_ids) != len(atoms) or len(bond_ids) != len(bonds):
            raise ValueError("Duplicate MOL2 atom/bond identifiers.")
        for bond in bonds:
            if not {int(bond[1]), int(bond[2])} <= atom_ids or bond[1] == bond[2]:
                raise ValueError("Invalid MOL2 bond endpoints.")
        if any(not math.isfinite(float(atom[8])) for atom in atoms):
            raise ValueError("Non-finite MOL2 atomic charge.")
        return atoms, bonds
    except (KeyError, IndexError) as exc:
        raise ValueError("Missing MOL2 molecule/atom records.") from exc


def read_export_atoms(text: str, format_name: str) -> tuple[ExportAtom, ...]:
    """Read physical atoms strictly, excluding known Meeko closure pseudoatoms."""
    if format_name == "mol2":
        rows, _ = _mol2_tables(text)
        atoms = tuple(ExportAtom(row[5].split(".")[0].upper(),
                                 tuple(float(value) for value in row[2:5])) for row in rows)
    elif format_name in {"pdb", "pdbqt"}:
        if sum(line.startswith("MODEL") for line in text.splitlines()) > 1:
            raise ValueError("Expected one molecular model for export.")
        rows = tuple(line for line in text.splitlines() if line.startswith(("ATOM  ", "HETATM")))
        if format_name == "pdbqt":
            rows = tuple(line for line in rows if line.split()[-1] not in MACROCYCLE_GHOST_TYPES)
        atoms = tuple(_pdb_atom(line, format_name) for line in rows)
    else:
        raise ValueError(f"Unsupported export validation format: {format_name}")
    if not atoms:
        raise ValueError("No atoms found in molecular export.")
    if any(not math.isfinite(value) for atom in atoms for value in atom.xyz):
        raise ValueError("Non-finite atom coordinates in molecular export.")
    return atoms


def _pdb_atom(line: str, format_name: str) -> ExportAtom:
    xyz = tuple(float(line[start:start + 8]) for start in (30, 38, 46))
    if format_name == "pdbqt":
        token = line.split()[-1]
        element = {"A": "C", "OA": "O", "OS": "O", "NA": "N", "NS": "N",
                   "SA": "S", "HD": "H", "HS": "H"}.get(token, token).upper()
        if token in MACROCYCLE_CARBON_TYPES:
            element = "C"
    else:
        element = line[76:78].strip().upper()
        if not element:
            name = line[12:16]
            element = name.strip()[0] if name.startswith(" ") else name.strip()[:2]
            element = element.upper()
    if not element.isalpha():
        raise ValueError("Missing or invalid atom element in molecular export.")
    return ExportAtom(element, xyz)


def macrocycle_export_pdb(text: str) -> str | None:
    """Return physical PDB records for flexible macrocycles, otherwise None.

    Discard the docking torsion tree together with closure pseudoatoms, avoiding
    references to removed atoms. Open Babel will infer component topology from
    this geometry, without adding hydrogens or recovering original charges.
    """
    rows = tuple(line for line in text.splitlines() if line.startswith(("ATOM  ", "HETATM")))
    if not any(line.split()[-1] in MACROCYCLE_GHOST_TYPES | MACROCYCLE_CARBON_TYPES for line in rows):
        return None
    expected = read_export_atoms(text, "pdbqt")
    physical = tuple(line for line in rows if line.split()[-1] not in MACROCYCLE_GHOST_TYPES)
    if len(physical) > 99999:
        raise ValueError("Macrocycle staging exceeds the PDB limit of 99999 atoms.")
    records = tuple(
        line[:6] + f"{index:5d}" + line[11:66].ljust(55) + "          " + f"{atom.element:>2}"
        for index, (line, atom) in enumerate(zip(physical, expected), 1)
    )
    result = "\n".join((*records, "END", ""))
    validate_export_atoms(expected, result, "pdb")
    return result


def validate_export_atoms(expected: tuple[ExportAtom, ...], text: str, format_name: str) -> None:
    """Reject atom loss, element changes and movement beyond output precision."""
    actual = read_export_atoms(text, format_name)
    if len(actual) != len(expected):
        raise ValueError(f"Export atom count changed: expected {len(expected)}, got {len(actual)}.")
    for index, (before, after) in enumerate(zip(expected, actual), 1):
        if before.element != after.element:
            raise ValueError(f"Export element changed at atom {index}.")
        if any(abs(left - right) > 0.00051 for left, right in zip(before.xyz, after.xyz)):
            raise ValueError(f"Export coordinates changed at atom {index}.")


def atomic_export_bytes(output_path: Path, data: bytes) -> None:
    """Replace only with a complete validated file, on the destination filesystem."""
    with tempfile.NamedTemporaryFile(dir=output_path.parent, prefix=".vinalab-export-",
                                     suffix=".tmp", delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(data)
        except BaseException:
            handle.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(output_path)
    finally:
        temporary.unlink(missing_ok=True)


def build_complex_mol2(receptor_text: str, pose_text: str) -> str:
    """Merge separately perceived components without introducing interface bonds."""
    expected = read_export_atoms(receptor_text, "mol2") + read_export_atoms(pose_text, "mol2")
    atom_lines: list[str] = []
    bond_lines: list[str] = []
    residue_lines: list[str] = []
    for component, text in enumerate((receptor_text, pose_text)):
        atoms, bonds = _mol2_tables(text)
        atom_map = {row[0]: index + len(atom_lines) + 1 for index, row in enumerate(atoms)}
        residue_keys = tuple(dict.fromkeys((row[6], row[7]) for row in atoms))
        residue_map = {key: index + len(residue_lines) + 1 for index, key in enumerate(residue_keys)}
        for row in atoms:
            residue = residue_map[(row[6], row[7])]
            atom_lines.append(" ".join((str(atom_map[row[0]]), *row[1:6], str(residue), *row[7:])))
        for row in bonds:
            bond_lines.append(" ".join((str(len(bond_lines) + 1), str(atom_map[row[1]]),
                                         str(atom_map[row[2]]), *row[3:])))
        for key, residue in residue_map.items():
            root = next(row[0] for row in atoms if (row[6], row[7]) == key)
            chain = "R" if component == 0 else "L"
            residue_lines.append(f"{residue} {key[1]} {atom_map[root]} RESIDUE 1 {chain} {key[1]} 0 ROOT")
    header = ["@<TRIPOS>MOLECULE", "Receptor_pose_complex",
              f"{len(atom_lines)} {len(bond_lines)} {len(residue_lines)} 0 0", "SMALL", "USER_CHARGES",
              "", "# PDBQT-derived topology; components perceived separately; no added atoms."]
    result = "\n".join([*header, "@<TRIPOS>ATOM", *atom_lines, "@<TRIPOS>BOND", *bond_lines,
                        "@<TRIPOS>SUBSTRUCTURE", *residue_lines, ""])
    validate_export_atoms(expected, result, "mol2")
    return result


def _merge_pdb(receptor_text: str, pose_text: str) -> str:
    expected = read_export_atoms(receptor_text, "pdb") + read_export_atoms(pose_text, "pdb")
    if len(expected) > 99999:
        raise ValueError("Complex exceeds the PDB limit of 99999 atoms; use MOL2.")
    chains = {line[21] for line in receptor_text.splitlines() if line.startswith(("ATOM  ", "HETATM"))}
    ligand_chain = next((chain for chain in "ZYXWVUTSRQPONMLKJIHGFEDCBA0123456789" if chain not in chains), None)
    if ligand_chain is None:
        raise ValueError("No free PDB chain identifier for the ligand; use MOL2.")
    atom_lines: list[str] = []
    conect_lines: list[str] = []
    serial_offset = 0
    for component, text in enumerate((receptor_text, pose_text)):
        rows = tuple(line for line in text.splitlines() if line.startswith(("ATOM  ", "HETATM")))
        serial_map = {int(line[6:11]): serial_offset + index + 1 for index, line in enumerate(rows)}
        if len(serial_map) != len(rows):
            raise ValueError("Duplicate PDB atom serial numbers.")
        for line in rows:
            updated = line[:6] + f"{serial_map[int(line[6:11])]:5d}" + line[11:]
            if component:
                updated = "HETATM" + updated[6:21] + ligand_chain + updated[22:]
            atom_lines.append(updated)
        atom_lines.append("TER")
        serial_offset += len(rows)
        for line in text.splitlines():
            if line.startswith("CONECT"):
                ids = tuple(int(line[start:start + 5]) for start in range(6, len(line), 5)
                            if line[start:start + 5].strip())
                if any(serial not in serial_map for serial in ids):
                    raise ValueError("Invalid PDB CONECT atom reference.")
                conect_lines.append("CONECT" + "".join(f"{serial_map[serial]:5d}" for serial in ids))
    result = "\n".join(["REMARK 950 PDBQT-DERIVED TOPOLOGY; NO ADDED ATOMS", *atom_lines, *conect_lines, "END", ""])
    validate_export_atoms(expected, result, "pdb")
    return result


def export_complex(receptor_path: Path, pose_path: Path, output_path: Path) -> Path:
    """Export one receptor plus one selected pose to PDB/MOL2, or raise.

    This headless API is also usable by frozen smoke checks. Inputs are single
    structures; callers must extract the requested model from multi-pose output.
    Existing outputs are replaced only after validation. No atoms are added and
    bond perception never crosses the receptor/ligand interface.
    """
    from core.docking_engine import convert_with_obabel

    format_name = output_path.suffix[1:].lower()
    if format_name not in {"pdb", "mol2"}:
        raise ValueError("Complex export requires a .pdb or .mol2 output path.")
    if output_path.resolve() in {receptor_path.resolve(), pose_path.resolve()}:
        raise ValueError("Complex output must not overwrite an input structure.")
    with tempfile.TemporaryDirectory(prefix="vinalab-complex-") as directory:
        receptor = Path(directory) / ("receptor." + format_name)
        ligand = Path(directory) / ("ligand." + format_name)
        convert_with_obabel(receptor_path, receptor)
        convert_with_obabel(pose_path, ligand)
        builder = build_complex_mol2 if format_name == "mol2" else _merge_pdb
        text = builder(receptor.read_text(encoding="utf-8"), ligand.read_text(encoding="utf-8"))
        atomic_export_bytes(output_path, text.encode("utf-8"))
    return output_path
