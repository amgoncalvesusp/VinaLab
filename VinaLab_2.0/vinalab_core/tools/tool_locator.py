"""Deterministic native-tool discovery without hard-coded system paths."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


class ToolLocator:
    """Finds bundled tools first, then a configured conda environment, then PATH."""

    def __init__(self, project_root: str | Path, conda_prefix: str | Path | None = None) -> None:
        self.project_root = Path(project_root)
        self.conda_prefix = Path(conda_prefix) if conda_prefix else None

    def find(self, name: str) -> Path | None:
        for candidate in self._bundled_candidates(name):
            if candidate.is_file():
                return candidate
        for candidate in self._conda_candidates(name):
            if candidate.is_file():
                return candidate
        path_match = shutil.which(name)
        if path_match:
            return Path(path_match)
        if os.name == "nt":
            executable_match = shutil.which(f"{name}.exe")
            if executable_match:
                return Path(executable_match)
        return None

    def _bundled_candidates(self, name: str) -> tuple[Path, ...]:
        suffixes = (".exe", "") if os.name == "nt" else ("", ".exe")
        tool_directory = self.project_root / "tools" / name
        exact = tuple(tool_directory / f"{name}{suffix}" for suffix in suffixes)
        nested_bin = tuple(tool_directory / "bin" / f"{name}{suffix}" for suffix in suffixes)
        versioned = tuple(sorted(tool_directory.glob(f"{name}_*")))
        return exact + nested_bin + versioned

    def _conda_candidates(self, name: str) -> tuple[Path, ...]:
        if self.conda_prefix is None:
            return ()
        suffixes = (".exe", "") if os.name == "nt" else ("", ".exe")
        directories = (self.conda_prefix / "Scripts", self.conda_prefix / "bin")
        return tuple(directory / f"{name}{suffix}" for directory in directories for suffix in suffixes)
