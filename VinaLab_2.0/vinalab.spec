# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for the self-contained Windows VinaLab 2.0 build."""

from pathlib import Path


project_root = Path(SPECPATH)

a = Analysis(
    [str(project_root / "vinalab_ui" / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[(str(project_root / "tools"), "tools")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VinaLab_2.0",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="VinaLab_2.0",
)
