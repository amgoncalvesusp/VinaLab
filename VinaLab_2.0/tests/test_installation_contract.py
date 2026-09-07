"""Real wheel/editable installations exercised outside the project working directory."""

import os
import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path

import pytest

from vinalab_core import runtime_paths

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("platform,env,expected", [
    ("win32", "LOCALAPPDATA", "VinaLab 2.0"),
    ("linux", "XDG_DATA_HOME", "VinaLab 2.0"),
])
def test_project_data_is_user_owned(monkeypatch, tmp_path, platform, env, expected):
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setenv(env, str(tmp_path))
    assert runtime_paths.default_project_root() == tmp_path / expected


def test_linux_relative_xdg_is_ignored(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", "relative")
    assert runtime_paths.default_project_root() == Path.home() / ".local/share/VinaLab 2.0"


def test_frozen_resources_and_user_data_are_separate(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert runtime_paths.resource_root() == tmp_path
    assert runtime_paths.default_project_root() != tmp_path


def run(*args, cwd):
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=180, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_wheel_and_editable_install_from_unrelated_cwd(tmp_path):
    wheel_dir = tmp_path / "wheels"
    run(sys.executable, "-m", "pip", "wheel", str(ROOT), "--no-deps",
        "-w", str(wheel_dir), cwd=tmp_path)
    wheel = next(wheel_dir.glob("*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        names = [name.split(".data/purelib/", 1)[-1] for name in archive.namelist()]
        assert not any(name.startswith(("packaging/", "tests/", "tools/")) for name in names)
        assert any("vinalab_core/_bundled/tools/xtb/share/xtb/param_gfn2" in n for n in names)
        for asset in (ROOT / "vinalab_ui").rglob("assets/**/*"):
            if asset.is_file() and asset.name not in {".gitattributes", ".gitignore"}:
                assert asset.relative_to(ROOT).as_posix() in names
        if sys.platform != "win32":
            assert not any(n.lower().endswith((".exe", ".dll")) for n in names)
    target = tmp_path / "installed"
    run(sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(target),
        str(wheel), cwd=tmp_path)
    probe = (
        "from vinalab_core.runtime_paths import resource_root, default_project_root; "
        "import vinalab_cli, vinalab_ui; "
        "assert (resource_root() / 'tools/xtb/share/xtb/param_gfn2-xtb.txt').is_file(); "
        "assert default_project_root() != resource_root()"
    )
    run(sys.executable, "-I", "-c", f"import sys; sys.path.insert(0, {str(target)!r}); " + probe,
        cwd=tmp_path)
    env = tmp_path / "editable"
    venv.EnvBuilder(with_pip=True, system_site_packages=True).create(env)
    python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    run(str(python), "-m", "pip", "install", "--no-deps",
        "-e", str(ROOT), cwd=tmp_path)
    run(str(python), "-I", "-c", probe, cwd=tmp_path)
    run(str(python), "-m", "pip", "install", "build", cwd=tmp_path)
    run(str(python), "-m", "build", "--sdist", str(ROOT), "--outdir", str(wheel_dir),
        cwd=tmp_path)
    sdist = next(wheel_dir.glob("*.tar.gz"))
    with tarfile.open(sdist) as archive:
        names = archive.getnames()
        assert any(n.endswith("/packaging/vinalab_build.py") for n in names)
        assert any(n.endswith("/tools/xtb/bin/xtb.exe") for n in names)
    run(str(python), "-m", "pip", "wheel", str(sdist), "--no-deps", "-w",
        str(tmp_path / "roundtrip"), cwd=tmp_path)


def test_frozen_entry_dependency_check_without_gui(tmp_path):
    run(sys.executable, str(ROOT / "packaging/frozen_entry.py"), "--check-dependencies",
        cwd=tmp_path)
