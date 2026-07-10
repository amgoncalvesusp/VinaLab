"""Paths for development and frozen VinaLab desktop distributions."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def resource_root() -> Path:
    """Return the read-only application directory that contains bundled engines."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[1]


def default_project_root() -> Path:
    """Return the writable default project location for the current application mode."""
    if not getattr(sys, "frozen", False):
        return resource_root()
    local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return local_app_data / "VinaLab 2.0"
