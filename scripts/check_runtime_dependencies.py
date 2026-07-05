# -*- coding: utf-8 -*-
"""Verify runtime dependencies required by packaged builds are importable."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.native_tools import find_obabel_executable, find_vina_executable


REQUIRED_IMPORTS = [
    "PySide6.QtWidgets",
    "PySide6.QtWebEngineWidgets",
    "meeko",
    "scipy",
    "gemmi",
    "rdkit",
    "openbabel",
    "prody",
    "Bio",
    "MDAnalysis",
    "plotly",
    "pandas",
    "matplotlib",
    "openpyxl",
    "reportlab",
    "numpy",
    "py3Dmol",
]


def main() -> int:
    failures: list[str] = []
    for import_name in REQUIRED_IMPORTS:
        try:
            importlib.import_module(import_name)
        except Exception as exc:  # noqa: BLE001 - report every import failure
            failures.append(f"{import_name}: {exc}")

    obabel = find_obabel_executable()
    if obabel is None:
        failures.append("obabel.exe/obabel was not found")
    vina = find_vina_executable()
    if vina is None:
        failures.append("vina_1.2.7_win.exe/vina was not found")

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1
    print(f"Runtime dependency check passed. Open Babel CLI: {obabel}; AutoDock Vina CLI: {vina}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
