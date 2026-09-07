"""Strict prepared-XYZ validation for frozen quantum interaction energies."""
import math
from dataclasses import dataclass
from pathlib import Path

from vinalab_core.prepare.molecule import validate_coordinates


@dataclass(frozen=True, slots=True)
class XYZStructure:
    elements: tuple[str, ...]
    coordinates: tuple[tuple[float, float, float], ...]


def read_xyz(path):
    from rdkit import Chem
    path = Path(path)
    if path.suffix.lower() != ".xyz":
        raise ValueError("Quantum scoring requires prepared hydrogen-complete XYZ, not PDBQT")
    lines = path.read_text().splitlines()
    try:
        count = int(lines[0])
        if count < 1 or len(lines) != count + 2:
            raise ValueError("XYZ atom count does not match records")
        records = tuple(line.split() for line in lines[2:])
        if any(len(record) != 4 for record in records):
            raise ValueError("XYZ requires element and three coordinates per atom")
        table = Chem.GetPeriodicTable()
        symbols = frozenset(table.GetElementSymbol(i) for i in range(1, 119))
        elements = tuple(row[0] for row in records)
        if any(element not in symbols for element in elements):
            raise ValueError("Unknown XYZ element")
        coordinates = validate_coordinates(row[1:] for row in records)
        for i, point in enumerate(coordinates):
            if any(math.dist(point, other) < .1 for other in coordinates[:i]):
                raise ValueError("Overlapping XYZ atoms (<0.1 Angstrom)")
        return XYZStructure(elements, coordinates)
    except (IndexError, TypeError) as exc:
        raise ValueError("Malformed XYZ") from exc


def validate_electronic_state(structure, charge, uhf):
    from rdkit import Chem
    if type(charge) is not int or type(uhf) is not int or uhf < 0:
        raise ValueError("Charge and unpaired-electron count (uhf) must be explicit integers; uhf >= 0")
    electrons = sum(Chem.GetPeriodicTable().GetAtomicNumber(e) for e in structure.elements) - charge
    if electrons < 0 or uhf > electrons or (electrons - uhf) % 2:
        raise ValueError("Charge/uhf inconsistent with electron count")


def validate_fragments(complex_structure, receptor, ligand):
    if complex_structure.elements != receptor.elements + ligand.elements:
        raise ValueError("Complex atom count/order/elements must equal receptor followed by ligand")
    if any(math.dist(a, b) > 1e-7 for a, b in zip(complex_structure.coordinates, receptor.coordinates + ligand.coordinates)):
        raise ValueError("Complex coordinates must match frozen fragment coordinates")


def write_xyz(path, structure):
    lines = [str(len(structure.elements)), "VinaLab frozen prepared fragments"]
    lines.extend(f"{e} {x:.12f} {y:.12f} {z:.12f}" for e, (x, y, z) in zip(structure.elements, structure.coordinates))
    Path(path).write_text("\n".join(lines) + "\n", encoding="ascii")
