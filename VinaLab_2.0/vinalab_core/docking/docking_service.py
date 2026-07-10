"""End-to-end orchestration for a reproducible AutoDock Vina run."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from vinalab_core.docking.search_box import SearchBox
from vinalab_core.docking.vina_engine import VinaCommandBuilder
from vinalab_core.docking.vina_results import VinaPoseResult, VinaResultsParser
from vinalab_core.docking.vina_runner import VinaProcessResult, VinaRunner


class VinaExecutor(Protocol):
    def execute(
        self, command: Sequence[str], *, cpu_threads: int, timeout_seconds: float
    ) -> VinaProcessResult: ...


@dataclass(frozen=True, slots=True)
class DockingRunResult:
    process: VinaProcessResult
    poses: tuple[VinaPoseResult, ...]

    @property
    def ok(self) -> bool:
        return self.process.ok


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
    ) -> DockingRunResult:
        command = self.builder.build(
            receptor=receptor,
            ligand=ligand,
            output=output,
            search_box=search_box,
            cpu_threads=cpu_threads,
            exhaustiveness=exhaustiveness,
            seed=seed,
        )
        process = self.runner.execute(
            command, cpu_threads=cpu_threads, timeout_seconds=timeout_seconds
        )
        poses = self.parser.parse(process.stdout) if process.ok else ()
        return DockingRunResult(process=process, poses=poses)
