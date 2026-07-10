"""Subprocess execution boundary for AutoDock Vina."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class VinaProcessResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class VinaRunner:
    """Runs trusted engine argument lists without using a shell."""

    def execute(
        self,
        command: Sequence[str],
        *,
        cpu_threads: int,
        timeout_seconds: float,
        environment: Mapping[str, str] | None = None,
        working_directory: str | Path | None = None,
    ) -> VinaProcessResult:
        if not command:
            raise ValueError("command must not be empty")
        if cpu_threads < 1:
            raise ValueError("cpu_threads must be at least one")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        process_environment = os.environ.copy()
        process_environment.update(
            {
                "OMP_NUM_THREADS": str(cpu_threads),
                "OPENBLAS_NUM_THREADS": str(cpu_threads),
                "MKL_NUM_THREADS": str(cpu_threads),
            }
        )
        if environment:
            process_environment.update(environment)
        startupinfo = None
        creationflags = 0
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = subprocess.CREATE_NO_WINDOW
        completed = subprocess.run(
            list(command),
            shell=False,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            env=process_environment,
            cwd=working_directory,
            timeout=timeout_seconds,
            startupinfo=startupinfo,
            creationflags=creationflags,
        )
        return VinaProcessResult(
            command=tuple(command),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
