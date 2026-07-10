from __future__ import annotations

import importlib
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
    binary = tmp_path / "tools" / "vina" / "vina.exe"
    binary.parent.mkdir(parents=True)
    binary.write_text("placeholder", encoding="utf-8")

    exit_code = cli_main(["diagnostics", "--project-root", str(tmp_path)])

    assert exit_code == 0
    assert str(binary) in capsys.readouterr().out
