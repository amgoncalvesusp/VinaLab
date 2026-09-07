import importlib.util
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def helper():
    spec = importlib.util.spec_from_file_location("build_support", ROOT / "packaging/build_support.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_explicit_discovery_and_dependencies():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    discovery = config["tool"]["setuptools"]["packages"]["find"]
    assert set(discovery["include"]) == {"vinalab_core*", "vinalab_ui*", "vinalab_cli*"}
    assert {"packaging*", "tools*", "tests*"} <= set(discovery["exclude"])
    assert config["project"]["requires-python"] == ">=3.11"
    assert config["project"]["version"] == "2.0.1"
    deps = {dep.split(">=")[0] for dep in config["project"]["dependencies"]}
    assert {"PySide6", "rdkit", "meeko", "gemmi", "openbabel-wheel", "scipy", "numpy"} <= deps


def test_linux_resources_exclude_windows_binaries():
    resources = helper().tool_files(ROOT, "linux")
    assert resources
    assert all(path.suffix.lower() not in {".exe", ".dll"} for path in resources)
    assert any(path.name == "param_gfn2-xtb.txt" for path in resources)


def test_windows_resources_include_engines():
    names = {path.name for path in helper().tool_files(ROOT, "win32")}
    assert {"vina_1.2.7_win.exe", "xtb.exe", "libiomp5md.dll"} <= names


def test_missing_molecular_dependency_fails_build():
    def absent(name):
        if name == "meeko":
            raise ImportError("missing")
    with pytest.raises(RuntimeError, match="meeko"):
        helper().check_dependencies(absent)


def test_dependency_check_imports_every_required_module():
    checked = []
    helper().check_dependencies(checked.append)
    assert {"rdkit.Chem", "meeko", "gemmi", "openbabel.openbabel", "scipy", "numpy", "PySide6.QtWidgets", "PySide6.QtWebEngineWidgets"} <= set(checked)


def test_v2_workflow_is_manual_artifacts_only():
    workflow = (ROOT.parent / ".github/workflows/v2-build.yml").read_text()
    assert "workflow_dispatch:" in workflow
    assert "push:" not in workflow
    assert "contents: read" in workflow
    assert "working-directory: VinaLab_2.0" in workflow
    assert "python-version: '3.11'" in workflow
    assert "VINALAB_TEST_VINA={engine}" in workflow
    assert 'shutil.which("vina")' in workflow
    assert "action-gh-release" not in workflow
    old = (ROOT.parent / ".github/workflows/release.yml").read_text()
    assert '"!v2*"' in old


def test_frozen_spec_checks_dependencies_and_collects_webengine():
    spec = (ROOT / "vinalab.spec").read_text()
    assert spec.index("check_dependencies()") < spec.index("a = Analysis(")
    assert '"PySide6.QtWebEngineWidgets"' in spec
    assert '"frozen_entry.py"' in spec
    assert "copy_metadata(distribution)" in spec


def test_windowless_frozen_smoke_failure_returns_nonzero(monkeypatch):
    import sys

    monkeypatch.syspath_prepend(str(ROOT / "packaging"))
    spec = importlib.util.spec_from_file_location("frozen_entry", ROOT / "packaging/frozen_entry.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def missing():
        raise RuntimeError("Required build dependencies unavailable: meeko")

    monkeypatch.setattr(module, "check_dependencies", missing)
    monkeypatch.setattr(sys, "argv", ["VinaLab.exe", "--check-dependencies"])
    monkeypatch.setattr(sys, "stderr", None)
    assert module.main() == 1
