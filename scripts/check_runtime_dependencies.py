# -*- coding: utf-8 -*-
"""Verify runtime dependencies required by packaged builds are importable."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.native_tools import (
    find_obabel_executable,
    find_vina_executable,
    native_tool_env,
)


REQUIRED_IMPORTS = [
    "PySide6.QtWidgets",
    "PySide6.QtWebEngineWidgets",
    "meeko",
    "meeko.cli.mk_prepare_receptor",
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
    else:
        obabel_env = native_tool_env(obabel)
        babel_libdir_value = obabel_env.get("BABEL_LIBDIR", "")
        babel_datadir_value = obabel_env.get("BABEL_DATADIR", "")
        babel_libdir = Path(babel_libdir_value) if babel_libdir_value else None
        babel_datadir = Path(babel_datadir_value) if babel_datadir_value else None
        if (
            babel_libdir is None
            or not babel_libdir.exists()
            or not any(babel_libdir.glob("*.obf"))
        ):
            failures.append("Open Babel .obf plugins were not found via BABEL_LIBDIR")
        if babel_datadir is None or not babel_datadir.exists():
            failures.append("Open Babel data directory was not found via BABEL_DATADIR")
        if sys.platform.startswith("win") and _openbabel_wheel_libs() is None:
            failures.append("openbabel_wheel.libs was not found")
    vina = find_vina_executable()
    if vina is None:
        failures.append("vina_1.2.7_win.exe/vina was not found")

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1
    print(f"Runtime dependency check passed. Open Babel CLI: {obabel}; AutoDock Vina CLI: {vina}")
    return 0


def _openbabel_wheel_libs() -> Path | None:
    spec = importlib.util.find_spec("openbabel")
    if spec is None or not spec.origin:
        return None
    libs = Path(spec.origin).resolve().parents[1] / "openbabel_wheel.libs"
    return libs if libs.exists() else None


if __name__ == "__main__":
    raise SystemExit(main())
