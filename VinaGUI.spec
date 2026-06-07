# -*- mode: python ; coding: utf-8 -*-

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
for _package in ("rdkit", "meeko", "prody", "Bio"):
    _datas, _binaries, _hidden = collect_all(_package)
    datas += _datas
    binaries += _binaries
    hiddenimports += _hidden

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


a = Analysis(
    ['launcher.py'],
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
    upx=True,
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
