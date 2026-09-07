"""Shared resource selection and mandatory frozen-build dependency checks."""

import sys
from importlib import import_module
from pathlib import Path, PureWindowsPath


def isolated_build_environment(environment, *, platform=None, executable=None, base_prefix=None):
    """Exclude workstation DLL providers from Windows dependency resolution."""
    if (platform or sys.platform) != "win32":
        return dict(environment)
    windows = PureWindowsPath(environment.get("SystemRoot", environment.get("WINDIR", "")))
    python = PureWindowsPath(executable or sys.executable)
    base = PureWindowsPath(base_prefix or sys.base_prefix)
    if not all(path.is_absolute() for path in (windows, python, base)):
        raise ValueError("Windows build requires absolute interpreter and SystemRoot paths")
    directories = (python.parent, base, base / "Scripts", windows / "System32", windows)
    path = ";".join(str(directory) for directory in dict.fromkeys(directories))
    return {**environment, "PATH": path}


def check_dependencies(importer=import_module):
    from vinalab_core.runtime_check import check_dependencies as check_runtime_dependencies

    check_runtime_dependencies(importer)


def tool_files(root: Path, platform: str):
    return tuple(
        path for path in sorted((root / "tools").rglob("*"))
        if path.is_file()
        and (platform == "win32" or path.suffix.lower() not in {".exe", ".dll"})
    )


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    check_dependencies()
    print(f"Mandatory runtime dependencies available for {sys.platform}.")
