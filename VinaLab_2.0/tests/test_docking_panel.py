from __future__ import annotations

import importlib
import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton
from vinalab_core.docking.search_box import SearchBox
from vinalab_core.prepare.element_router import ElementRouter


def _panel_type():
    try:
        module = importlib.import_module("vinalab_ui.widgets.docking_panel")
    except ModuleNotFoundError:
        return None
    return getattr(module, "DockingPanel", None)


def test_docking_panel_is_available_for_vina_execution() -> None:
    assert _panel_type() is not None


def test_docking_panel_only_enables_run_when_vina_and_both_pdbqt_inputs_exist(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    panel_type = _panel_type()
    assert panel_type is not None
    panel = panel_type(
        SearchBox(
            center=(0.0, 0.0, 0.0),
            size=(20.0, 20.0, 20.0),
            coordinate_frame="receptor:test",
            margin=4.0,
            source="user",
        ),
        vina_available=True,
    )
    run_button = panel.findChild(QPushButton, "runDocking")
    assert run_button is not None
    assert not run_button.isEnabled()

    receptor = tmp_path / "receptor.pdbqt"
    ligand = tmp_path / "ligand.pdbqt"
    receptor.write_text("RECEPTOR", encoding="utf-8")
    ligand.write_text("LIGAND", encoding="utf-8")
    panel.set_inputs(receptor, ligand)

    assert run_button.isEnabled()
    assert panel.validation_message == "Ready to run Vina"


def test_docking_panel_uses_a_replaced_search_box_before_execution() -> None:
    QApplication.instance() or QApplication([])
    panel_type = _panel_type()
    assert panel_type is not None
    panel = panel_type(
        SearchBox(
            center=(0.0, 0.0, 0.0),
            size=(20.0, 20.0, 20.0),
            coordinate_frame="receptor:test",
            margin=4.0,
            source="user",
        ),
        vina_available=True,
    )
    replacement = SearchBox(
        center=(10.0, 20.0, 30.0),
        size=(24.0, 22.0, 20.0),
        coordinate_frame="receptor:test",
        margin=4.0,
        source="user",
    )

    panel.set_search_box(replacement)

    assert panel.search_box == replacement


def test_docking_panel_emits_the_visible_run_configuration(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    panel_type = _panel_type()
    assert panel_type is not None
    receptor = tmp_path / "receptor.pdbqt"
    ligand = tmp_path / "ligand.pdbqt"
    receptor.write_text("RECEPTOR", encoding="utf-8")
    ligand.write_text("LIGAND", encoding="utf-8")
    panel = panel_type(
        SearchBox(
            center=(1.0, 2.0, 3.0),
            size=(20.0, 20.0, 20.0),
            coordinate_frame="receptor:test",
            margin=4.0,
            source="user",
        ),
        vina_available=True,
    )
    panel.set_inputs(receptor, ligand)
    requests = []
    panel.run_requested.connect(requests.append)

    panel.run_button.click()

    assert requests[0].receptor == receptor
    assert requests[0].ligand == ligand
    assert requests[0].search_box == panel.search_box
    assert requests[0].cpu_threads >= 1


def test_docking_panel_browse_button_sets_receptor_path(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    panel_type = _panel_type()
    assert panel_type is not None
    receptor = tmp_path / "receptor.pdbqt"
    receptor.write_text("RECEPTOR", encoding="utf-8")
    panel = panel_type(
        SearchBox(
            center=(0.0, 0.0, 0.0),
            size=(20.0, 20.0, 20.0),
            coordinate_frame="receptor:test",
            margin=4.0,
            source="user",
        ),
        vina_available=True,
    )
    browse_button = panel.findChild(QPushButton, "browseReceptor")
    receptor_input = panel.findChild(QLineEdit, "receptorPath")
    assert browse_button is not None
    assert receptor_input is not None

    with patch("vinalab_ui.widgets.docking_panel.QFileDialog.getOpenFileName", return_value=(str(receptor), "")):
        browse_button.click()

    assert receptor_input.text() == str(receptor)


def test_docking_panel_browse_button_sets_ligand_path(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    panel_type = _panel_type()
    assert panel_type is not None
    ligand = tmp_path / "ligand.pdbqt"
    ligand.write_text("LIGAND", encoding="utf-8")
    panel = panel_type(
        SearchBox(
            center=(0.0, 0.0, 0.0),
            size=(20.0, 20.0, 20.0),
            coordinate_frame="receptor:test",
            margin=4.0,
            source="user",
        ),
        vina_available=True,
    )
    browse_button = panel.findChild(QPushButton, "browseLigand")
    ligand_input = panel.findChild(QLineEdit, "ligandPath")
    assert browse_button is not None
    assert ligand_input is not None

    with patch("vinalab_ui.widgets.docking_panel.QFileDialog.getOpenFileName", return_value=(str(ligand), "")):
        browse_button.click()

    assert ligand_input.text() == str(ligand)


def test_docking_panel_blocks_vina_when_the_ligand_requires_exotic_scoring(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    panel_type = _panel_type()
    assert panel_type is not None
    receptor = tmp_path / "receptor.pdbqt"
    ligand = tmp_path / "boron_ligand.pdbqt"
    receptor.write_text("RECEPTOR", encoding="utf-8")
    ligand.write_text(
        "ATOM      1  B1  LIG     1       0.000   0.000   0.000  0.00  0.00     0.000 B\n",
        encoding="utf-8",
    )
    panel = panel_type(
        SearchBox(
            center=(0.0, 0.0, 0.0),
            size=(20.0, 20.0, 20.0),
            coordinate_frame="receptor:test",
            margin=4.0,
            source="user",
        ),
        vina_available=True,
    )
    panel.set_inputs(receptor, ligand)
    route = ElementRouter().inspect_pdbqt_text(ligand.read_text(encoding="utf-8"))

    panel.set_element_route(route)

    assert not panel.run_button.isEnabled()
    assert "Boron" in panel.validation_message
