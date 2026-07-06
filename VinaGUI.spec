# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import glob
import os
import shutil
import subprocess
import sys

from PyInstaller.utils.hooks import collect_all

# RDKit ships compiled extension submodules (e.g. rdkit.Geometry.rdGeometry) whose
# dependent DLLs must travel with them; Meeko imports those at module load
# (``from rdkit.Geometry import Point3D``). collect_all() gathers datas +
# binaries + hiddenimports together, which is the reliable way to ship
# RDKit/Meeko frozen.
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
    ("tools/vina", "tools/vina"),
    ("pontuacao", "pontuacao"),
    ("VERSION", "."),
    ("README.md", "."),
]


def find_build_obabel():
    names = ("obabel.exe", "obabel") if sys.platform.startswith("win") else ("obabel",)
    scripts_dir = Path(sys.executable).resolve().parent
    for name in names:
        candidate = scripts_dir / name
        if candidate.exists():
            return str(candidate)
    for name in names:
        path_value = shutil.which(name)
        if path_value:
            return path_value
    return None


def find_build_vina():
    names = (
        ("vina_1.2.7_win.exe", "vina.exe", "vina")
        if sys.platform.startswith("win")
        else ("vina",)
    )
    for name in names:
        candidate = Path("tools") / "vina" / name
        if candidate.exists():
            return str(candidate)
    for name in names:
        path_value = shutil.which(name)
        if path_value:
            return path_value
    return None


def bundled_windows_gnina_exists():
    name = "gnina.exe"
    gnina = Path("tools") / "gnina" / name
    return gnina.exists() and gnina.is_file()


def collect_windows_gnina_torch_dlls():
    """Bundle libtorch DLLs for GNINA when a compatible CUDA torch is available."""
    if not sys.platform.startswith("win") or not bundled_windows_gnina_exists():
        return []
    required = ("c10.dll", "torch_cpu.dll", "torch_cuda.dll")
    search_roots = []
    libtorch_bin = os.environ.get("LIBTORCH_BIN")
    if libtorch_bin:
        search_roots.append(Path(libtorch_bin))
    try:
        import torch

        search_roots.append(Path(torch.__file__).resolve().parent / "lib")
    except Exception:
        pass
    found = []
    missing = []
    for dll_name in required:
        dll_path = next(
            (root / dll_name for root in search_roots if (root / dll_name).is_file()),
            None,
        )
        if dll_path is None:
            missing.append(dll_name)
        else:
            found.append((str(dll_path), "tools/gnina"))
    if missing:
        print(
            "GNINA Windows libtorch DLLs not fully bundled; missing: "
            + ", ".join(missing)
        )
        return []
    return found


# meeko 0.7 imports prody at top level, prody imports Biopython, and Biopython's
# substitution_matrices loads a data directory at import time. Without it,
# ``import meeko`` raises FileNotFoundError for Bio/Align/substitution_matrices/data,
# which made the frozen environment check report FALHA for meeko.
#
# PySide6 is collected in full instead of relying only on the built-in hook + a
# handful of hiddenimports. The missing-DLL failures on clean computers came from
# Qt6 DLLs/plugins/WebEngine pieces that the partial collection did not carry.
#
# openbabel-wheel ships compiled extensions plus format plugins (*.obf) and data.
# The receptor/MOL2 conversion path uses the openbabel Python API in-process, so
# the whole package must travel with the executable.
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

_obabel = find_build_obabel()
if sys.platform.startswith("win") and _obabel is None:
    raise SystemExit("obabel.exe was not found; install openbabel-wheel before building.")
if _obabel is not None:
    binaries.append((_obabel, "."))

_vina_cli = find_build_vina()
if sys.platform.startswith("linux") and _vina_cli is None:
    raise SystemExit(
        "vina was not found; install the Vina Python package or AutoDock Vina CLI before building."
    )
if _vina_cli is not None and not Path(_vina_cli).resolve().is_relative_to(
    (Path("tools") / "vina").resolve()
):
    binaries.append((_vina_cli, "tools/vina"))

if sys.platform.startswith("win") and bundled_windows_gnina_exists():
    datas.append(("tools/gnina", "tools/gnina"))
    binaries += collect_windows_gnina_torch_dlls()
else:
    print("Skipping PyInstaller GNINA bundle for this platform/build.")

# openbabel-wheel keeps its private shared libraries in a sibling
# "openbabel_wheel.libs" directory (the delvewheel layout) that collect_all does
# not reach. Bundle it at the same relative location expected by openbabel.
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


def _collect_msvc_runtime():
    """Bundle the Microsoft Visual C++ runtime needed by Qt6/PySide6."""
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


def _drop_unused_qt_plugins():
    """Remove optional Qt plugins whose external DLLs are not used by VinaLab."""
    blocked_names = {"qsqlmimer.dll", "qtwebviewquickplugin.dll"}

    def keep(entry):
        source = entry[0]
        normalized = str(source).replace("/", "\\").lower()
        name = os.path.basename(normalized)
        return name not in blocked_names and "\\qml\\qtwebview\\" not in normalized

    binaries[:] = [entry for entry in binaries if keep(entry)]
    datas[:] = [entry for entry in datas if keep(entry)]


binaries += _collect_msvc_runtime()
_drop_unused_qt_plugins()

excludes = [
    "torch",
    "torchvision",
    "torchaudio",
    "torchdata",
    "dgl",
    "dgllife",
    "torch_scatter",
    "xgboost",
    "sklearn",
    "tensorboard",
    "tensorflow",
]


a = Analysis(
    ["main.py"],
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
    name="VinaLab",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=["ui/icon.ico"],
)
