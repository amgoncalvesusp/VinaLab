"""xTB GFN2/ALPB rescoring plugin for exotic-element complexes."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

from vinalab_core.docking.vina_runner import VinaProcessResult, VinaRunner
from vinalab_core.scoring.xyz import (
    XYZStructure,
    read_xyz,
    validate_electronic_state,
    validate_fragments,
    write_xyz,
)
from vinalab_core.tools.tool_locator import ToolLocator

HARTREE_TO_KCAL_PER_MOL = 627.5094740631


class XtbRunner(Protocol):
    def execute(
        self,
        command: list[str],
        *,
        cpu_threads: int,
        timeout_seconds: float,
        working_directory: str | Path | None = None,
    ) -> VinaProcessResult: ...


@dataclass(frozen=True, slots=True)
class XtbEnergyResult:
    hartree: float
    kcal_per_mol: float
    stdout: str = ""
    stderr: str = ""
    command: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class XtbInteractionResult:
    complex_energy: XtbEnergyResult
    receptor_energy: XtbEnergyResult
    ligand_energy: XtbEnergyResult
    interaction_hartree: float
    interaction_kcal_per_mol: float
    protocol: str
    interpretation: str = "Frozen interaction energy, not binding affinity or binding free energy; no entropy, relaxation or standard-state correction."


class XtbScorer:
    """Builds deterministic solvated GFN2-xTB single-point invocations."""

    key = "xtb_gfn2"
    label = "xTB GFN2 + ALPB water frozen interaction energy"

    def __init__(self, project_root: str | Path, *, runner: XtbRunner | None = None) -> None:
        self.locator = ToolLocator(project_root)
        self.runner = runner or VinaRunner()

    def is_available(self) -> tuple[bool, str]:
        if self.locator.find("xtb") is None:
            return False, "xTB binary is not configured"
        return True, ""

    def build_single_point_command(self, structure: str | Path, *, charge: int, uhf: int | None = None, method: str = "gfn2") -> list[str]:
        executable = self.locator.find("xtb")
        if executable is None:
            raise RuntimeError("xTB binary is not configured")
        if method not in {"gfn2", "gfnff"}:
            raise ValueError("method must be gfn2 or gfnff")
        if type(charge) is not int or (uhf is not None and (type(uhf) is not int or uhf < 0)):
            raise ValueError("Charge and uhf must be integers; uhf >= 0")
        return [
            str(executable),
            str(structure),
            *(["--gfn", "2"] if method == "gfn2" else ["--gfnff"]),
            "--alpb", "water",
            "--chrg", str(charge),
            *(["--uhf", str(uhf)] if uhf is not None else []),
        ]

    def score_single_point(
        self,
        structure: str | Path,
        *,
        charge: int,
        cpu_threads: int,
        timeout_seconds: float = 3600,
        uhf: int | None = None,
        method: str = "gfn2",
    ) -> XtbEnergyResult:
        structure_path = Path(structure).resolve()
        structure_data = read_xyz(structure_path)
        if uhf is not None:
            validate_electronic_state(structure_data, charge, uhf)
        with TemporaryDirectory(prefix="vinalab-xtb-") as temporary_directory:
            process = self.runner.execute(
                self.build_single_point_command(structure_path, charge=charge, uhf=uhf, method=method),
                cpu_threads=cpu_threads,
                timeout_seconds=timeout_seconds,
                working_directory=temporary_directory,
            )
        diagnostics = process.stdout + "\n" + process.stderr
        failed_convergence = re.search(r"(?:not converged|failed to converge|convergence failure|SCC is not converged|abnormal termination)", diagnostics, re.IGNORECASE)
        if failed_convergence:
            raise RuntimeError("xTB did not converge: " + diagnostics)
        if not process.ok:
            raise RuntimeError(diagnostics.strip() or "xTB exited without a total energy")
        hartree = self.parse_total_energy(process.stdout)
        return XtbEnergyResult(hartree=hartree, kcal_per_mol=hartree * HARTREE_TO_KCAL_PER_MOL,
            stdout=process.stdout, stderr=process.stderr, command=tuple(process.command))

    def score_interaction(
        self, receptor_xyz, ligand_xyz, *, charge_receptor: int, charge_ligand: int,
        uhf_receptor: int, uhf_ligand: int, uhf_complex: int,
        hydrogen_complete: bool, method: str = "gfn2", cpu_threads: int = 1,
        timeout_seconds: float = 3600,
    ) -> XtbInteractionResult:
        """E(complex)-E(receptor)-E(ligand); input XYZ already in one frame.

        Hydrogen completeness is a required user attestation, not inferred from
        XYZ connectivity. uhf is the number of unpaired electrons, not multiplicity.
        """
        if hydrogen_complete is not True:
            raise ValueError("Explicit confirmation of prepared hydrogen-complete XYZ is required")
        receptor, ligand = read_xyz(receptor_xyz), read_xyz(ligand_xyz)
        combined = XYZStructure(receptor.elements + ligand.elements, receptor.coordinates + ligand.coordinates)
        states = ((combined, charge_receptor + charge_ligand, uhf_complex),
                  (receptor, charge_receptor, uhf_receptor), (ligand, charge_ligand, uhf_ligand))
        for structure, charge, uhf in states:
            validate_electronic_state(structure, charge, uhf)
        if method == "gfnff" and any(uhf for _, _, uhf in states):
            raise ValueError("GFN-FF has no electronic spin model; nonzero uhf unsupported")
        with TemporaryDirectory(prefix="vinalab-interaction-") as directory:
            paths = tuple(Path(directory) / f"{name}.xyz" for name in ("complex", "receptor", "ligand"))
            for path, (structure, _, _) in zip(paths, states):
                write_xyz(path, structure)
            validate_fragments(read_xyz(paths[0]), receptor, ligand)
            energies = tuple(self.score_single_point(path, charge=charge, uhf=uhf, method=method,
                cpu_threads=cpu_threads, timeout_seconds=timeout_seconds)
                for path, (_, charge, uhf) in zip(paths, states))
        energy = energies[0].hartree - energies[1].hartree - energies[2].hartree
        protocol = (f"xTB {method.upper()} + ALPB water; frozen XYZ single points; "
                    f"Ecomplex-Ereceptor-Eligand; charges={tuple(s[1] for s in states)}; "
                    f"uhf={tuple(s[2] for s in states)}; user-confirmed hydrogen complete")
        return XtbInteractionResult(*energies, energy, energy * HARTREE_TO_KCAL_PER_MOL, protocol)

    @staticmethod
    def parse_total_energy(output: str) -> float:
        matches = re.findall(r"total energy\s+([+-]?\d+(?:\.\d*)?(?:[EeDd][+-]?\d+)?)\s+Eh", output, re.IGNORECASE)
        if not matches:
            raise ValueError("xTB output does not contain a total energy in Hartree")
        energy = float(matches[-1].replace("D", "E").replace("d", "e"))
        if not math.isfinite(energy):
            raise ValueError("Nonfinite xTB energy")
        return energy
