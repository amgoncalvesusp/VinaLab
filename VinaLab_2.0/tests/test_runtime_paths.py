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


def test_development_runtime_uses_the_source_root_for_resources_and_project_data() -> None:
    module = _paths_module()
    assert module is not None

    source_root = Path(__file__).resolve().parents[1]

    assert module.resource_root() == source_root
    assert module.default_project_root() == source_root
