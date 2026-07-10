from __future__ import annotations

import importlib
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication


def _create_application():
    try:
        module = importlib.import_module("vinalab_ui.main")
    except ModuleNotFoundError:
        return None
    return getattr(module, "create_application", None)


def test_desktop_application_factory_is_available() -> None:
    assert _create_application() is not None


def test_desktop_application_factory_creates_the_vinalab_window() -> None:
    factory = _create_application()
    assert factory is not None

    application, window = factory([])

    assert isinstance(application, QApplication)
    assert window.windowTitle() == "VinaLab 2.0"
