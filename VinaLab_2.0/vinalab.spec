# -*- mode: python ; coding: utf-8 -*-
"""Native-platform VinaLab build; Linux engines are resolved from PATH."""

from pathlib import Path
import os
import sys
from importlib.metadata import distribution


project_root = Path(SPECPATH)
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "packaging"))
from build_support import check_dependencies, isolated_build_environment, tool_files

os.environ.update(isolated_build_environment(os.environ))
from PyInstaller.utils.hooks import collect_all, copy_metadata

check_dependencies()
datas = [(str(path), str(path.parent.relative_to(project_root)))
         for path in tool_files(project_root, sys.platform)]
asset_directories = [project_root / "vinalab_ui" / relative
                     for relative in ("assets", "widgets/assets")]
if not any(path.is_dir() for path in asset_directories):
    raise RuntimeError("Missing offline viewer assets: vinalab_ui/assets")
datas += [(str(path), str(path.relative_to(project_root)))
          for path in asset_directories if path.is_dir()]
binaries = []
hiddenimports = ["PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineCore", "PySide6.QtWebChannel"]
for package in ("rdkit", "meeko", "gemmi", "openbabel", "scipy", "numpy"):
    package_data, package_binaries, package_imports = collect_all(package)
    datas += [(source, target) for source, target in package_data
              if not {"tests", "test"}.intersection(Path(source).parts)]
    binaries += package_binaries
    hiddenimports += [name for name in package_imports if not {"tests", "test"}.intersection(name.split("."))]
openbabel_distribution = distribution("openbabel-wheel")
for relative in openbabel_distribution.files or ():
    parts = Path(relative).parts
    if not parts or parts[0] not in {"openbabel", "openbabel_wheel.libs"}:
        continue
    source = Path(openbabel_distribution.locate_file(relative))
    if source.suffix.lower() in {".dll", ".obf", ".exe"}:
        if sys.platform == "win32":
            binaries.append((str(source), str(Path(relative).parent)))
    elif parts[0] == "openbabel_wheel.libs":
        binaries.append((str(source), str(Path(relative).parent)))
for distribution in ("rdkit", "meeko", "gemmi", "openbabel-wheel", "scipy", "numpy", "vinalab"):
    datas += copy_metadata(distribution)

a = Analysis(
    [str(project_root / "packaging" / "frozen_entry.py")],
    pathex=[str(project_root), str(project_root / "packaging")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(project_root / "packaging" / "runtime_openbabel.py")],
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
