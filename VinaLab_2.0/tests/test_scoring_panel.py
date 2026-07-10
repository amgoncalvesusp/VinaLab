from __future__ import annotations

import importlib
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QTableWidget
from vinalab_core.scoring.registry import ScoringRegistry


def _panel_type():
    try:
        module = importlib.import_module("vinalab_ui.widgets.scoring_panel")
    except ModuleNotFoundError:
        return None
    return getattr(module, "ScoringPanel", None)


def test_scoring_panel_is_available_for_transparent_scorer_selection() -> None:
    assert _panel_type() is not None


def test_scoring_panel_shows_boron_recommendation_and_xtb_availability(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    panel_type = _panel_type()
    assert panel_type is not None
    plan = ScoringRegistry(tmp_path).plan_for_elements(frozenset({"B", "O"}))
    panel = panel_type()

    panel.show_plan(plan)
    recommendation = panel.findChild(QLabel, "scoringRecommendation")
    table = panel.findChild(QTableWidget, "scoringTable")

    assert recommendation is not None
    assert "xTB" in recommendation.text()
    assert table is not None
    assert table.rowCount() == len(plan.options)
