"""End-to-end orchestration for a reproducible AutoDock Vina run."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Protocol

from vinalab_core.docking.search_box import SearchBox
from vinalab_core.docking.vina_engine import VinaCommandBuilder
from vinalab_core.docking.vina_results import VinaPoseResult, VinaResultsParser
from vinalab_core.docking.vina_runner import VinaProcessResult, VinaRunner
from vinalab_core.prepare.element_router import VINA_ATOM_TYPES
from vinalab_core.prepare.pdbqt_validator import PdbqtValidator, parse_atom_record


class VinaExecutor(Protocol):
    def execute(
        self, command: Sequence[str], *, cpu_threads: int, timeout_seconds: float
    ) -> VinaProcessResult: ...


@dataclass(frozen=True, slots=True)
class DockingRunResult:
    process: VinaProcessResult
    poses: tuple[VinaPoseResult, ...]
    errors: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.process.ok and bool(self.poses) and not self.errors


class DockingService:
    """Builds one Vina command, executes it safely, then returns typed poses."""

    def __init__(self, executable: str | Path, *, runner: VinaExecutor | None = None) -> None:
        self.builder = VinaCommandBuilder(executable)
        self.runner = runner or VinaRunner()
        self.parser = VinaResultsParser()

    def run(
        self,
        *,
        receptor: str | Path,
        ligand: str | Path,
        output: str | Path,
        search_box: SearchBox,
        cpu_threads: int,
        exhaustiveness: int,
        seed: int,
        timeout_seconds: float = 3600,
        scoring: str = "vina",
        num_modes: int = 9,
        energy_range: float = 3.0,
    ) -> DockingRunResult:
        if not isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")
        validator = PdbqtValidator()
        for role, path in (("receptor", receptor), ("ligand", ligand)):
            text = Path(path).read_text(encoding="utf-8")
            report = validator.validate_text(text, role=role)
            if not report.ok:
                raise ValueError(f"Invalid {role} PDBQT: {'; '.join(report.errors)}")
            for line in text.splitlines():
                if line[:6].strip() in {"ATOM", "HETATM"}:
                    atom_type = parse_atom_record(line)[2]
                    if atom_type not in VINA_ATOM_TYPES:
                        raise ValueError(f"Unsupported {scoring} atom type: {atom_type}")
        output = Path(output)
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Output already exists; choose a new run path: {output}")
        command = self.builder.build(
            receptor=receptor,
            ligand=ligand,
            output=output,
            search_box=search_box,
            cpu_threads=cpu_threads,
            exhaustiveness=exhaustiveness,
            seed=seed,
            scoring=scoring,
            num_modes=num_modes,
            energy_range=energy_range,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        process = self.runner.execute(
            command, cpu_threads=cpu_threads, timeout_seconds=timeout_seconds
        )
        poses = self.parser.parse(process.stdout) if process.ok else ()
        errors: list[str] = []
        if process.ok:
            if not poses:
                errors.append("Vina stdout contains no valid pose results")
            try:
                output_text = output.read_text(encoding="utf-8")
                models = _output_models(output_text)
                for model in models:
                    report = validator.validate_text(model, role="ligand")
                    errors.extend(report.errors)
                if len(models) != len(poses) or not models:
                    errors.append("Output model count does not match parsed stdout poses")
            except (OSError, UnicodeError, ValueError) as exc:
                errors.append(f"Invalid or missing Vina output: {exc}")
        return DockingRunResult(process=process, poses=poses, errors=tuple(errors))


def _output_models(text: str) -> tuple[str, ...]:
    models: list[str] = []
    current: list[str] | None = None
    for line in text.splitlines():
        tag = line.split()[0] if line.strip() else ""
        if tag == "MODEL":
            if current is not None or line.split() != ["MODEL", str(len(models) + 1)]:
                raise ValueError("Invalid MODEL sequence")
            current = []
        elif tag == "ENDMDL":
            if current is None:
                raise ValueError("Unmatched ENDMDL")
            models.append("\n".join(current))
            current = None
        elif current is not None:
            current.append(line)
        elif tag and tag != "REMARK":
            raise ValueError("Pose records outside MODEL block")
    if current is not None:
        raise ValueError("Unclosed MODEL block")
    return tuple(models)
