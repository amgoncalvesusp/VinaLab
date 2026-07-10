"""Integrity checks for the redistributable standalone xTB runtime bundle."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class XtbBundleStatus:
    ready: bool
    executable: Path | None
    errors: tuple[str, ...] = ()


class XtbBundleValidator:
    """Checks executable and LGPL notice before a standalone xTB runtime is enabled."""

    def __init__(self, project_root: str | Path) -> None:
        self.bundle = Path(project_root) / "tools" / "xtb"

    def validate(self) -> XtbBundleStatus:
        executable_name = "xtb.exe" if os.name == "nt" else "xtb"
        executable_candidates = (
            self.bundle / executable_name,
            self.bundle / "bin" / executable_name,
        )
        executable = next((candidate for candidate in executable_candidates if candidate.is_file()), None)
        license_file = self.bundle / "LICENSES" / "COPYING"
        errors: list[str] = []
        if executable is None:
            errors.append(f"Missing standalone xTB executable: {executable_name}")
        if not license_file.is_file():
            errors.append("Missing xTB LGPL license notice: LICENSES/COPYING")
        return XtbBundleStatus(not errors, executable, tuple(errors))
