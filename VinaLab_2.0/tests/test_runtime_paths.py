from __future__ import annotations

import importlib
from pathlib import Path


def _paths_module():
    try:
        return importlib.import_module("vinalab_core.runtime_paths")
    except ModuleNotFoundError:
        return None


def test_runtime_paths_are_available_for_a_packaged_desktop_application() -> None:
    assert _paths_module() is not None


def test_development_resources_and_user_project_data_are_separate(monkeypatch, tmp_path) -> None:
    import sys

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    module = _paths_module()
    assert module is not None

    source_root = Path(__file__).resolve().parents[1]

    assert module.resource_root() == source_root
    assert module.default_project_root() == tmp_path / "VinaLab 2.0"
