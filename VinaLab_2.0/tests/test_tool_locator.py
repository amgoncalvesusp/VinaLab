from __future__ import annotations

import importlib
from pathlib import Path


def _locator_type():
    try:
        module = importlib.import_module("vinalab_core.tools.tool_locator")
    except ModuleNotFoundError:
        return None
    return getattr(module, "ToolLocator", None)


def test_tool_locator_is_available_to_find_native_tools() -> None:
    assert _locator_type() is not None


def test_tool_locator_prefers_the_project_bundle_before_path_lookup(tmp_path: Path) -> None:
    locator_type = _locator_type()
    assert locator_type is not None
    bundled_vina = tmp_path / "tools" / "vina" / "vina.exe"
    bundled_vina.parent.mkdir(parents=True)
    bundled_vina.write_text("placeholder", encoding="utf-8")

    found = locator_type(tmp_path).find("vina")

    assert found == bundled_vina


def test_tool_locator_accepts_the_versioned_vina_binary_from_the_1x_bundle(tmp_path: Path) -> None:
    locator_type = _locator_type()
    assert locator_type is not None
    bundled_vina = tmp_path / "tools" / "vina" / "vina_1.2.7_win.exe"
    bundled_vina.parent.mkdir(parents=True)
    bundled_vina.write_text("placeholder", encoding="utf-8")

    assert locator_type(tmp_path).find("vina") == bundled_vina


def test_tool_locator_finds_xtb_in_its_official_bin_layout(tmp_path: Path) -> None:
    locator_type = _locator_type()
    assert locator_type is not None
    bundled_xtb = tmp_path / "tools" / "xtb" / "bin" / "xtb.exe"
    bundled_xtb.parent.mkdir(parents=True)
    bundled_xtb.write_text("placeholder", encoding="utf-8")

    assert locator_type(tmp_path).find("xtb") == bundled_xtb
