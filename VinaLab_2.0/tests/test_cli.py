from __future__ import annotations

import importlib
import os
from pathlib import Path


def _cli_main():
    try:
        module = importlib.import_module("vinalab_cli.main")
    except ModuleNotFoundError:
        return None
    return getattr(module, "main", None)


def test_cli_main_is_available_for_headless_workflows() -> None:
    assert _cli_main() is not None


def test_cli_diagnostics_reports_the_bundled_vina_binary(tmp_path: Path, capsys) -> None:
    cli_main = _cli_main()
    assert cli_main is not None
    binary = tmp_path / "tools" / "vina" / ("vina.exe" if os.name == "nt" else "vina")
    binary.parent.mkdir(parents=True)
    binary.write_text("placeholder", encoding="utf-8")
    binary.chmod(0o755)

    exit_code = cli_main(["diagnostics", "--project-root", str(tmp_path)])

    assert exit_code == 0
    assert str(binary) in capsys.readouterr().out


def test_cli_diagnostics_defaults_to_installed_resources_outside_project(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from vinalab_core import runtime_paths

    package = tmp_path / "installed" / "vinalab_core"
    binary = package / "_bundled" / "tools" / "vina" / ("vina.exe" if os.name == "nt" else "vina")
    binary.parent.mkdir(parents=True)
    binary.write_text("placeholder", encoding="utf-8")
    binary.chmod(0o755)
    outside = tmp_path / "unrelated"
    outside.mkdir()
    monkeypatch.chdir(outside)
    monkeypatch.setattr(runtime_paths, "__file__", str(package / "runtime_paths.py"))
    monkeypatch.setattr("shutil.which", lambda _: None)

    assert _cli_main()(["diagnostics"]) == 0
    assert str(binary) in capsys.readouterr().out


def test_cli_explicit_project_root_overrides_installed_resources(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from vinalab_core import runtime_paths

    package = tmp_path / "installed" / "vinalab_core"
    bundled = package / "_bundled" / "tools" / "vina" / ("vina.exe" if os.name == "nt" else "vina")
    bundled.parent.mkdir(parents=True)
    bundled.write_text("placeholder", encoding="utf-8")
    bundled.chmod(0o755)
    override = tmp_path / "explicit"
    override.mkdir()
    monkeypatch.setattr(runtime_paths, "__file__", str(package / "runtime_paths.py"))
    monkeypatch.setattr("shutil.which", lambda _: None)

    assert _cli_main()(["diagnostics", "--project-root", str(override)]) == 1
    assert "Vina: not found" in capsys.readouterr().out
