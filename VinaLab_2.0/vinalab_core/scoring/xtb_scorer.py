"""xTB GFN2/ALPB rescoring plugin for exotic-element complexes."""

from __future__ import annotations

from pathlib import Path
import re
from dataclasses import dataclass
from tempfile import TemporaryDirectory
from typing import Protocol

from vinalab_core.docking.vina_runner import VinaProcessResult, VinaRunner
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


class XtbScorer:
    """Builds deterministic solvated GFN2-xTB single-point invocations."""

    key = "xtb_gfn2"
    label = "xTB GFN2 + ALPB water"

    def __init__(self, project_root: str | Path, *, runner: XtbRunner | None = None) -> None:
        self.locator = ToolLocator(project_root)
        self.runner = runner or VinaRunner()

    def is_available(self) -> tuple[bool, str]:
        if self.locator.find("xtb") is None:
            return False, "xTB binary is not configured"
        return True, ""

    def build_single_point_command(self, structure: str | Path, *, charge: int) -> list[str]:
        executable = self.locator.find("xtb")
        if executable is None:
            raise RuntimeError("xTB binary is not configured")
        return [
            str(executable),
            str(structure),
            "--gfn", "2",
            "--alpb", "water",
            "--chrg", str(charge),
        ]

    def score_single_point(
        self,
        structure: str | Path,
        *,
        charge: int,
        cpu_threads: int,
        timeout_seconds: float = 3600,
    ) -> XtbEnergyResult:
        structure_path = Path(structure).resolve()
        with TemporaryDirectory(prefix="vinalab-xtb-") as temporary_directory:
            process = self.runner.execute(
                self.build_single_point_command(structure_path, charge=charge),
                cpu_threads=cpu_threads,
                timeout_seconds=timeout_seconds,
                working_directory=temporary_directory,
            )
        if not process.ok:
            raise RuntimeError(process.stderr.strip() or "xTB exited without a total energy")
        hartree = self.parse_total_energy(process.stdout)
        return XtbEnergyResult(hartree=hartree, kcal_per_mol=hartree * HARTREE_TO_KCAL_PER_MOL)

    @staticmethod
    def parse_total_energy(output: str) -> float:
        match = re.search(r"total energy\s+(-?\d+(?:\.\d+)?)\s+Eh", output)
        if match is None:
            raise ValueError("xTB output does not contain a total energy in Hartree")
        return float(match.group(1))
