from __future__ import annotations

import importlib
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTableWidget
from vinalab_core.docking.vina_results import VinaPoseResult


def _panel_type():
    try:
        module = importlib.import_module("vinalab_ui.widgets.results_panel")
    except ModuleNotFoundError:
        return None
    return getattr(module, "ResultsPanel", None)


def test_results_panel_is_available_for_docking_poses() -> None:
    assert _panel_type() is not None


def test_results_panel_displays_mode_affinity_and_rmsd_values() -> None:
    QApplication.instance() or QApplication([])
    panel_type = _panel_type()
    assert panel_type is not None
    panel = panel_type()

    panel.show_poses([VinaPoseResult(1, -8.4, 0.0, 0.0)])
    table = panel.findChild(QTableWidget, "resultsTable")

    assert table is not None
    assert table.rowCount() == 1
    assert table.item(0, 0).text() == "1"
    assert table.item(0, 1).text() == "-8.400"
