"""Validation of PDBQT text before it reaches a docking engine."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal

from vinalab_core.prepare.element_router import AUTODOCK_TYPE_ELEMENTS, EXOTIC_ELEMENTS, METALS


def parse_atom_record(record: str) -> tuple[tuple[float, float, float], float, str]:
    """Read PDB coordinates by columns, allowing compact PDBQT charge/type tails."""
    if record[:6].strip() not in {"ATOM", "HETATM"}:
        raise ValueError("not an ATOM or HETATM record")
    try:
        coordinates = tuple(float(record[start : start + 8]) for start in (30, 38, 46))
        tail = record[66:].split()
        if len(tail) != 2:
            raise ValueError("missing charge or atom type")
        charge = float(tail[0])
        atom_type = tail[1]
    except (ValueError, IndexError) as exc:
        raise ValueError("invalid coordinates, charge, or atom type") from exc
    if not all(isfinite(value) for value in (*coordinates, charge)):
        raise ValueError("coordinates and charge must be finite")
    if atom_type not in AUTODOCK_TYPE_ELEMENTS.keys() | EXOTIC_ELEMENTS | METALS:
        raise ValueError(f"unknown AutoDock atom type: {atom_type}")
    return coordinates, charge, atom_type


@dataclass(frozen=True, slots=True)
class PdbqtValidationReport:
    atom_count: int
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


class PdbqtValidator:
    """Performs lightweight structural checks while preserving input verbatim."""

    def validate_text(
        self, pdbqt: str, *, role: Literal["ligand", "receptor"] | None = None
    ) -> PdbqtValidationReport:
        if role not in {None, "ligand", "receptor"}:
            raise ValueError("role must be ligand or receptor")
        lines = pdbqt.splitlines()
        records = [
            (n, line) for n, line in enumerate(lines, 1) if line[:6].strip() in {"ATOM", "HETATM"}
        ]
        if not records:
            return PdbqtValidationReport(
                0, ("No ATOM or HETATM records were found in the PDBQT file",)
            )
        errors: list[str] = []
        for line_number, record in records:
            try:
                parse_atom_record(record)
            except ValueError as exc:
                errors.append(f"ATOM record at line {line_number}: {exc}")
        tags = [line.split()[0] for line in lines if line.strip()]
        if role == "receptor" and any(
            tag in {"ROOT", "ENDROOT", "BRANCH", "ENDBRANCH", "TORSDOF", "MODEL"} for tag in tags
        ):
            errors.append("Rigid receptor must not contain ligand torsion or MODEL records")
        if role == "ligand":
            if "MODEL" in tags or "ENDMDL" in tags:
                errors.append(
                    "Ligand input must contain a single torsion tree without MODEL records"
                )
            if tags.count("ROOT") != 1 or tags.count("ENDROOT") != 1 or tags.count("TORSDOF") != 1:
                errors.append("Ligand requires one ROOT, ENDROOT and TORSDOF record")
            elif not tags.index("ROOT") < tags.index("ENDROOT") < tags.index("TORSDOF"):
                errors.append("Ligand torsion records are out of order")
            branches = []
            for line in lines:
                fields = line.split()
                if not fields:
                    continue
                if fields[0] == "TORSDOF" and (len(fields) != 2 or not fields[1].isdigit()):
                    errors.append("TORSDOF must be a nonnegative integer")
                if fields[0] in {"BRANCH", "ENDBRANCH"}:
                    if len(fields) != 3 or not all(v.isdigit() for v in fields[1:]):
                        errors.append("Invalid branch atom identifiers")
                    elif fields[0] == "BRANCH":
                        branches.append(fields[1:])
                    elif not branches or branches.pop() != fields[1:]:
                        errors.append("Unmatched ENDBRANCH")
            if branches:
                errors.append("Unclosed BRANCH")
        return PdbqtValidationReport(len(records), tuple(errors))
