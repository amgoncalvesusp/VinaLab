from __future__ import annotations

import importlib
import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton, QLabel
import pytest


def _inspector_type():
    try:
        module = importlib.import_module("vinalab_ui.widgets.ligand_inspector")
    except ModuleNotFoundError:
        return None
    return getattr(module, "LigandInspector", None)


def test_ligand_inspector_is_available_for_element_aware_preparation() -> None:
    assert _inspector_type() is not None


def test_ligand_inspector_warns_that_boron_requires_exotic_rescoring(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    inspector_type = _inspector_type()
    assert inspector_type is not None
    ligand = tmp_path / "boron_ligand.pdbqt"
    ligand.write_text(
        "ATOM      1  B1  LIG     1       0.000   0.000   0.000  0.00  0.00     0.000 B\n",
        encoding="utf-8",
    )
    inspector = inspector_type()

    inspector.inspect_path(ligand)
    status = inspector.findChild(QLabel, "ligandRouteStatus")

    assert status is not None
    assert "Boron" in status.text()
    assert "xTB" in status.text()


def test_ligand_inspector_emits_the_selected_ligand_path(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    inspector_type = _inspector_type()
    assert inspector_type is not None
    ligand = tmp_path / "ligand.pdbqt"
    ligand.write_text(
        "ATOM      1  C1  LIG     1       0.000   0.000   0.000  0.00  0.00     0.000 C\n",
        encoding="utf-8",
    )
    inspector = inspector_type()
    selected = []
    inspector.ligand_selected.connect(selected.append)

    inspector.inspect_path(ligand)

    assert selected == [ligand]


def test_ligand_inspector_reports_when_the_recommended_xtb_route_is_not_configured(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    inspector_type = _inspector_type()
    assert inspector_type is not None
    ligand = tmp_path / "boron_ligand.pdbqt"
    ligand.write_text(
        "ATOM      1  B1  LIG     1       0.000   0.000   0.000  0.00  0.00     0.000 B\n",
        encoding="utf-8",
    )
    inspector = inspector_type(project_root=tmp_path)

    inspector.inspect_path(ligand)

    assert "not configured" in inspector.status.text().lower()


def test_ligand_inspector_browse_selects_and_inspects_a_pdbqt_file(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    inspector_type = _inspector_type()
    assert inspector_type is not None
    ligand = tmp_path / "ligand.pdbqt"
    ligand.write_text(
        "ATOM      1  C1  LIG     1       0.000   0.000   0.000  0.00  0.00     0.000 C\n",
        encoding="utf-8",
    )
    inspector = inspector_type(project_root=tmp_path)
    browse = inspector.findChild(QPushButton, "browseLigandInspector")
    path_input = inspector.findChild(QLineEdit, "ligandInspectorPath")
    assert browse is not None
    assert path_input is not None

    with patch("vinalab_ui.widgets.ligand_inspector.QFileDialog.getOpenFileName", return_value=(str(ligand), "")):
        browse.click()

    assert path_input.text() == str(ligand)
    assert "Standard Vina" in inspector.status.text()


def test_ligand_inspector_rejects_invalid_pdbqt_before_routing(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    inspector_type = _inspector_type()
    assert inspector_type is not None
    ligand = tmp_path / "invalid_ligand.pdbqt"
    ligand.write_text("REMARK no atoms\n", encoding="utf-8")
    inspector = inspector_type(project_root=tmp_path)

    with pytest.raises(ValueError, match="ATOM"):
        inspector.inspect_path(ligand)
