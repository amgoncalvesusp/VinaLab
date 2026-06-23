# -*- mode: python ; coding: utf-8 -*-

import glob
import os
import sys

from PyInstaller.utils.hooks import collect_all

# RDKit ships compiled extension submodules (e.g. rdkit.Geometry.rdGeometry) whose
# dependent DLLs must travel with them; Meeko imports those at module load
# (``from rdkit.Geometry import Point3D``). collect_submodules alone bundled the
# .pyd files but not their binary dependencies, so ``import meeko`` still failed
# in the frozen bundle (FALHA meeko). collect_all() gathers datas + binaries +
# hiddenimports together, which is the reliable way to ship RDKit/Meeko frozen.
binaries = []
hiddenimports = [
    "scipy",
    "gemmi",
    "openbabel",
    "openbabel.pybel",
    "meeko.cli.mk_prepare_receptor",
    "wheel",
    "PySide6.QtWidgets",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineCore",
    "matplotlib.backends.backend_qt5agg",
    "reportlab.graphics",
]

datas = [
    ("main.py", "."),
    ("mainwindow.py", "."),
    ("core", "core"),
    ("tabs", "tabs"),
    ("ui", "ui"),
    ("config", "config"),
    ("tools", "tools"),
]

# meeko 0.7 imports prody at top level, prody imports Biopython, and Biopython's
# substitution_matrices loads a data directory at import time. Without it,
# ``import meeko`` raises FileNotFoundError for Bio/Align/substitution_matrices/data,
# which made the frozen environment check report FALHA for meeko. Collect the full
# dependency chain (code + data + binaries) so the import succeeds frozen.
# MDAnalysis (interaction analysis) and plotly (interactive charts) also ship
# compiled extensions / data files that need full collection to import frozen.
# PySide6 is collected in full (collect_all) instead of relying only on the
# built-in hook + a handful of hiddenimports. The "missing DLL for PySide6"
# failure on other computers came from Qt6 DLLs/plugins/WebEngine pieces that
# the partial collection did not carry into the bundle. collect_all pulls every
# Qt6 DLL, the platform/imageformats plugins, the QtWebEngine process and its
# resources, so the frozen app no longer depends on a system Qt install.
# openbabel (openbabel-wheel) ships obabel's compiled extension plus its format
# plugins (*.obf) and data/lib directories. The receptor/MOL2 conversion path
# uses the openbabel Python API (pybel) in-process, so the whole package — code,
# binaries and data — must travel or "OpenBabel não está disponível" appears in
# the frozen app. The package self-configures BABEL_LIBDIR/BABEL_DATADIR on import
# relative to its bundled location, so no runtime env wiring is needed.
for _package in (
    "PySide6",
    "rdkit",
    "meeko",
    "prody",
    "Bio",
    "MDAnalysis",
    "plotly",
    "openbabel",
):
    _datas, _binaries, _hidden = collect_all(_package)
    datas += _datas
    binaries += _binaries
    hiddenimports += _hidden


# openbabel-wheel keeps its private shared libraries in a sibling
# "openbabel_wheel.libs" directory (the delvewheel layout) that collect_all does
# not reach. openbabel/__init__.py adds that directory to the DLL search path at
# import time via a path relative to the package, so the DLLs must be bundled at
# the same relative location for the compiled extension to load in the frozen app.
import importlib.util as _importlib_util

_openbabel_spec = _importlib_util.find_spec("openbabel")
if _openbabel_spec is not None and _openbabel_spec.origin:
    _openbabel_libs = os.path.join(
        os.path.dirname(os.path.dirname(_openbabel_spec.origin)),
        "openbabel_wheel.libs",
    )
    if os.path.isdir(_openbabel_libs):
        for _dll in glob.glob(os.path.join(_openbabel_libs, "*.dll")):
            binaries.append((_dll, "openbabel_wheel.libs"))


# Bundle the Microsoft Visual C++ runtime. Qt6/PySide6 are built with MSVC and
# fail to start with "DLL load failed while importing QtCore/QtGui" on machines
# that do not have the VC++ Redistributable installed. Shipping these DLLs beside
# the app removes that external system dependency, which is the root cause of the
# install failures reported on clean computers.
def _collect_msvc_runtime():
    if not sys.platform.startswith("win"):
        return []
    names = (
        "msvcp140.dll",
        "msvcp140_1.dll",
        "msvcp140_2.dll",
        "vcruntime140.dll",
        "vcruntime140_1.dll",
        "concrt140.dll",
    )
    search_dirs = []
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    search_dirs.append(os.path.join(system_root, "System32"))
    redist_dir = os.environ.get("VCToolsRedistDir", "")
    if redist_dir:
        search_dirs.extend(
            os.path.dirname(path)
            for path in glob.glob(
                os.path.join(redist_dir, "**", "x64", "**", "*.dll"), recursive=True
            )
        )
    found = []
    seen = set()
    for name in names:
        for directory in search_dirs:
            candidate = os.path.join(directory, name)
            if os.path.isfile(candidate) and name not in seen:
                found.append((candidate, "."))
                seen.add(name)
                break
    return found


binaries += _collect_msvc_runtime()

# The optional ML rescoring stack (torch/dgl/...) is NOT part of the core app:
# it runs from the extracted scoring archive via a separate interpreter. Bundling
# it here pulls in >1 GB and triggers a broken torch PyInstaller hook
# (ImportError: cannot import name 'conda_support') that disrupts collection of
# the core dependencies. Exclude it so the frozen core builds cleanly.
excludes = [
    "torch",
    "torchvision",
    "torchaudio",
    "torchdata",
    "dgl",
    "dgllife",
    "torch_scatter",
    "tensorboard",
    "tensorflow",
]


# Entry point must be main.py, not launcher.py. launcher.py is the SOURCE-mode
# bootstrap (creates .venv, pip-installs, then spawns ``python main.py`` as a
# subprocess). In a frozen build there is no .venv interpreter and main.py is not
# a standalone runnable script, so that subprocess launch never starts the GUI —
# the environment screen would pass but the app would never open. main.py already
# has the correct frozen branch (sys.frozen -> skip bootstrap, run Qt in-process),
# and using it as the entry makes PyInstaller analyze and bundle the full import
# chain (mainwindow, tabs, ui, core) as real modules.
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='VinaLab',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX is disabled: compressing Qt6/PySide6 (and Python) DLLs frequently
    # corrupts them, producing "DLL load failed" on machines other than the one
    # that built the bundle. Disabling it trades a slightly larger exe for a
    # bundle that loads reliably everywhere.
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['ui\\icon.ico'],
)
