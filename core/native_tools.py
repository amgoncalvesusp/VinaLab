# -*- coding: utf-8 -*-
"""Discovery and launch helpers for bundled native command-line tools."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import os
from pathlib import Path
import shutil
import subprocess
import sys

NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0


def find_native_executable(
    names: Sequence[str], tool_subdir: str | None = None
) -> Path | None:
    """Return a native executable from the app, PyInstaller bundle, or PATH."""
    for candidate in iter_native_executable_candidates(names, tool_subdir):
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def find_obabel_executable() -> Path | None:
    """Return the Open Babel CLI bundled with the app or available on PATH."""
    names = ("obabel.exe", "obabel") if sys.platform.startswith("win") else ("obabel",)
    return find_native_executable(names, "openbabel")


def find_gnina_executable() -> Path | None:
    """Return GNINA only when the executable can start with its local DLLs."""
    names = ("gnina.exe", "gnina") if sys.platform.startswith("win") else ("gnina",)
    for candidate in iter_native_executable_candidates(names, "gnina"):
        if candidate.exists() and candidate.is_file() and native_tool_starts(candidate):
            return candidate
    return None


def native_tool_starts(
    tool_path: Path, args: Sequence[str] = ("--help",), timeout: int = 10
) -> bool:
    """Return True when a native executable can start without missing-DLL errors."""
    try:
        result = subprocess.run(
            [str(tool_path), *args],
            cwd=tool_path.resolve().parent,
            env=native_tool_env(tool_path),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            creationflags=NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def native_tool_env(
    tool_path: Path, base_env: Mapping[str, str] | None = None
) -> dict[str, str]:
    """Return an environment that lets bundled native tools find local DLLs/plugins."""
    env = dict(os.environ if base_env is None else base_env)
    tool_dir = tool_path.resolve().parent
    extra_paths = [str(tool_dir)]
    bundle_dir = Path(getattr(sys, "_MEIPASS", ""))
    if bundle_dir.exists():
        extra_paths.append(str(bundle_dir))
        openbabel_dir = bundle_dir / "openbabel"
        if openbabel_dir.exists():
            extra_paths.append(str(openbabel_dir))
    existing_path = env.get("PATH", "")
    if existing_path:
        extra_paths.append(existing_path)
    env["PATH"] = os.pathsep.join(extra_paths)
    if any(tool_dir.glob("*.obf")):
        env.setdefault("BABEL_LIBDIR", str(tool_dir))
    return env


def iter_native_executable_candidates(
    names: Sequence[str], tool_subdir: str | None
) -> list[Path]:
    """Return app/bundle candidates followed by PATH candidates."""
    candidates = _candidate_paths(names, tool_subdir)
    for name in names:
        path_value = shutil.which(name)
        if path_value:
            candidates.append(Path(path_value))
    return candidates


def _candidate_paths(names: Sequence[str], tool_subdir: str | None) -> list[Path]:
    project_root = Path(__file__).resolve().parents[1]
    bundle_dir = Path(getattr(sys, "_MEIPASS", project_root))
    executable_dir = Path(sys.executable).resolve().parent
    roots = [
        executable_dir,
        bundle_dir,
        bundle_dir / "Scripts",
        Path.cwd(),
        project_root,
    ]
    candidates: list[Path] = []
    for root in roots:
        for name in names:
            candidates.append(root / name)
        if tool_subdir:
            for name in names:
                candidates.append(root / "tools" / tool_subdir / name)
                candidates.append(root / tool_subdir / name)
    return candidates
