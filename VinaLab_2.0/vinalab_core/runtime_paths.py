"""Paths for development and frozen VinaLab desktop distributions."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def resource_root() -> Path:
    """Return the read-only application directory that contains bundled engines."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    bundled = Path(__file__).resolve().parent / "_bundled"
    if bundled.is_dir():
        return bundled
    return Path(__file__).resolve().parents[1]


def default_project_root() -> Path:
    """Return the writable default project location for the current application mode."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        configured = Path(os.environ.get("XDG_DATA_HOME", ""))
        base = configured if configured.is_absolute() else Path.home() / ".local" / "share"
    return base / "VinaLab 2.0"
