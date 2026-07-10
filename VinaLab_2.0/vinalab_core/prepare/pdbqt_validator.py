"""Validation of PDBQT text before it reaches a docking engine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PdbqtValidationReport:
    atom_count: int
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


class PdbqtValidator:
    """Performs lightweight structural checks while preserving input verbatim."""

    def validate_text(self, pdbqt: str) -> PdbqtValidationReport:
        records = [line for line in pdbqt.splitlines() if line.startswith(("ATOM", "HETATM"))]
        if not records:
            return PdbqtValidationReport(0, ("No ATOM or HETATM records were found in the PDBQT file",))
        errors: list[str] = []
        for line_number, record in enumerate(records, start=1):
            tokens = record.split()
            if len(tokens) < 12:
                errors.append(f"ATOM record {line_number} is missing coordinates, charge, or atom type")
                continue
            try:
                float(tokens[5])
                float(tokens[6])
                float(tokens[7])
                float(tokens[-2])
            except ValueError:
                errors.append(f"ATOM record {line_number} contains invalid numeric coordinates or charge")
            if not tokens[-1].strip():
                errors.append(f"ATOM record {line_number} is missing an AutoDock atom type")
        return PdbqtValidationReport(len(records), tuple(errors))
