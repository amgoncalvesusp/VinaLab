from __future__ import annotations

import importlib
import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton
import pytest


def _selector_type():
    try:
        module = importlib.import_module("vinalab_ui.widgets.receptor_selector")
    except ModuleNotFoundError:
        return None
    return getattr(module, "ReceptorSelector", None)


def test_receptor_selector_is_available_for_receptor_pdbqt_input() -> None:
    assert _selector_type() is not None


def test_receptor_selector_browse_emits_the_existing_pdbqt_path(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    selector_type = _selector_type()
    assert selector_type is not None
    receptor = tmp_path / "receptor.pdbqt"
    receptor.write_text(
        "ATOM      1  C1  REC     1       1.000   2.000   3.000  0.00  0.00     0.100 C\n",
        encoding="utf-8",
    )
    selector = selector_type()
    selected = []
    selector.receptor_selected.connect(selected.append)
    browse = selector.findChild(QPushButton, "browseReceptorSelector")
    path_input = selector.findChild(QLineEdit, "receptorSelectorPath")
    assert browse is not None
    assert path_input is not None

    with patch("vinalab_ui.widgets.receptor_selector.QFileDialog.getOpenFileName", return_value=(str(receptor), "")):
        browse.click()

    assert path_input.text() == str(receptor)
    assert selected == [receptor]


def test_receptor_selector_rejects_invalid_pdbqt_before_emitting(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    selector_type = _selector_type()
    assert selector_type is not None
    receptor = tmp_path / "invalid_receptor.pdbqt"
    receptor.write_text("REMARK no atoms\n", encoding="utf-8")
    selector = selector_type()
    selected = []
    selector.receptor_selected.connect(selected.append)

    with pytest.raises(ValueError, match="ATOM"):
        selector.select_path(receptor)

    assert selected == []
