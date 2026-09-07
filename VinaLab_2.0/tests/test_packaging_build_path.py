import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def helper():
    spec = importlib.util.spec_from_file_location("build_support", ROOT / "packaging/build_support.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_windows_build_environment_excludes_foreign_dll_paths():
    original = {"PATH": r"C:\Codex\poppler\bin;C:\Codex\libheif\bin;C:\miniconda\Library\bin;;.",
                "SystemRoot": r"C:\Windows", "KEEP": "unchanged"}
    result = helper().isolated_build_environment(
        original, platform="win32", executable=r"C:\project\.venv-build\Scripts\python.exe",
        base_prefix=r"C:\Python311",
    )
    assert result["PATH"].split(";") == [
        r"C:\project\.venv-build\Scripts", r"C:\Python311", r"C:\Python311\Scripts",
        r"C:\Windows\System32", r"C:\Windows",
    ]
    assert result["KEEP"] == "unchanged"
    assert "poppler" in original["PATH"]
    assert result is not original


def test_linux_path_is_preserved():
    original = {"PATH": "/usr/local/bin:/usr/bin", "KEEP": "yes"}
    assert helper().isolated_build_environment(original, platform="linux") == original


@pytest.mark.parametrize("root", ["", ".", "Windows"])
def test_windows_rejects_missing_or_relative_system_root(root):
    with pytest.raises(ValueError, match="absolute"):
        helper().isolated_build_environment(
            {"SystemRoot": root}, platform="win32", executable=r"C:\Python311\python.exe",
            base_prefix=r"C:\Python311",
        )


def test_spec_isolates_path_before_dependency_collection():
    source = (ROOT / "vinalab.spec").read_text()
    isolation = source.index("isolated_build_environment(os.environ)")
    assert isolation < source.index("from PyInstaller.utils.hooks import")
    assert isolation < source.index("check_dependencies()")
    assert isolation < source.index("a = Analysis(")


def test_installer_normalizes_workspace_paths_before_file_collection():
    source = (ROOT / "packaging/windows/VinaLab_2.0.iss").read_text()
    assert "ProjectRoot ExtractFileDir(ExtractFileDir(RemoveBackslashUnlessRoot(SourcePath)))" in source
    assert 'Source: "{#ProjectRoot}\\dist\\VinaLab_2.0\\*"' in source
    assert "..\\..\\" not in source
