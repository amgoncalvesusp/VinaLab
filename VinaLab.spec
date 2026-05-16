# -*- mode: python ; coding: utf-8 -*-

import sys

from PyInstaller.utils.hooks import collect_all, copy_metadata


datas = [
    ("ui", "ui"),
    ("config", "config"),
    ("tools", "tools"),
    ("pontuacao", "pontuacao"),
    ("VERSION", "."),
    ("README.md", "."),
]
binaries = []
hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtWebEngineWidgets",
    "matplotlib.backends.backend_qtagg",
    "reportlab.graphics",
]


def collect_package(package_name):
    try:
        package_datas, package_binaries, package_hiddenimports = collect_all(package_name)
    except Exception:
        return
    datas.extend(package_datas)
    binaries.extend(package_binaries)
    hiddenimports.extend(package_hiddenimports)


def collect_dist_metadata(distribution_name):
    try:
        datas.extend(copy_metadata(distribution_name))
    except Exception:
        return


for package in (
    "vina",
    "meeko",
    "scipy",
    "gemmi",
    "rdkit",
    "openbabel",
    "pandas",
    "matplotlib",
    "openpyxl",
    "reportlab",
    "numpy",
    "py3Dmol",
):
    collect_package(package)

for distribution in (
    "PySide6",
    "PySide6-Addons",
    "PySide6-Essentials",
    "PySide6-WebEngine",
    "vina",
    "meeko",
    "scipy",
    "gemmi",
    "rdkit",
    "openbabel-wheel",
    "pandas",
    "matplotlib",
    "openpyxl",
    "reportlab",
    "numpy",
    "py3Dmol",
):
    collect_dist_metadata(distribution)


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "torch",
        "torchdata",
        "dgl",
        "dgllife",
        "MDAnalysis",
        "prody",
        "torch_scatter",
        "xgboost",
        "sklearn",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe_options = {}
if sys.platform.startswith("win"):
    exe_options["icon"] = "ui/icon.ico"

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="VinaLab",
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
    **exe_options,
)
