from __future__ import annotations

import importlib
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel


def _panel_type():
    try:
        module = importlib.import_module("vinalab_ui.widgets.diagnostics_panel")
    except ModuleNotFoundError:
        return None
    return getattr(module, "DiagnosticsPanel", None)


def test_diagnostics_panel_is_available_to_check_native_tools() -> None:
    assert _panel_type() is not None


def test_diagnostics_panel_reports_a_bundled_vina_binary(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    panel_type = _panel_type()
    assert panel_type is not None
    binary = tmp_path / "tools" / "vina" / "vina.exe"
    binary.parent.mkdir(parents=True)
    binary.write_text("placeholder", encoding="utf-8")

    panel = panel_type(tmp_path)
    status = panel.findChild(QLabel, "vinaStatus")

    assert status is not None
    assert "Available" in status.text()
    assert str(binary) in status.text()


def test_diagnostics_panel_reports_a_ready_standalone_xtb_bundle(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    panel_type = _panel_type()
    assert panel_type is not None
    bundle = tmp_path / "tools" / "xtb"
    (bundle / "bin").mkdir(parents=True)
    (bundle / "LICENSES").mkdir()
    executable = bundle / "bin" / "xtb.exe"
    executable.write_text("placeholder", encoding="utf-8")
    (bundle / "LICENSES" / "COPYING").write_text("LGPL-3.0", encoding="utf-8")

    panel = panel_type(tmp_path)
    status = panel.findChild(QLabel, "xtbStatus")

    assert status is not None
    assert "Available" in status.text()
    assert str(executable) in status.text()


def test_diagnostics_panel_explains_the_current_cpu_only_engine_capability(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    panel_type = _panel_type()
    assert panel_type is not None

    panel = panel_type(tmp_path)
    status = panel.findChild(QLabel, "gpuStatus")

    assert status is not None
    assert "CPU" in status.text()
    assert "GPU" in status.text()
