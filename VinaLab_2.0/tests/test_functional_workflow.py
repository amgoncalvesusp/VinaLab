"""End-to-end native workflows, with real chemistry and Vina where installed."""

import csv
import os
import shutil
from pathlib import Path
from time import monotonic, sleep

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication
from rdkit import Chem
from rdkit.Chem import AllChem

from vinalab_core.tools.tool_locator import ToolLocator
from vinalab_ui.mainwindow import MainWindow
from vinalab_ui.widgets.form_helpers import export_table


def wait(window, seconds=30):
    deadline = monotonic() + seconds
    while window.active_worker is not None and monotonic() < deadline:
        QApplication.instance().processEvents()
        sleep(.01)
    assert window.active_worker is None, "worker did not finish"


def source_sdf(path):
    mol = Chem.AddHs(Chem.MolFromSmiles("CCO"))
    assert AllChem.EmbedMolecule(mol, randomSeed=42) == 0
    with Chem.SDWriter(str(path)) as writer:
        writer.write(mol)
    return path


@pytest.mark.parametrize("scoring", ["Vina", "Vinardo"])
def test_prepare_dock_validate_and_reopen_portable_project(tmp_path, scoring):
    if ToolLocator(Path(__file__).resolve().parents[1]).find("vina") is None:
        pytest.skip("native Vina is unavailable")
    QApplication.instance() or QApplication([])
    root = tmp_path / "project"
    window = MainWindow(project_root=root)
    ligand_source = source_sdf(tmp_path / "reference.sdf")
    prepared = tmp_path / "ligand.pdbqt"
    window._convert(ligand_source, prepared, "ligand")
    wait(window)
    assert prepared.is_file(), window.ligand_inspector.conversion.status.text()
    assert window.docking_panel.ligand_input.text() == str(prepared)
    receptor = tmp_path / "receptor.pdbqt"
    receptor.write_text("ATOM      1  C1  REC     1       4.000   0.000   0.000  0.00  0.00     0.000 C\n")
    window.receptor_selector.select_path(receptor)
    window.search_box_editor.set_reference(ligand_source)
    window.docking_panel.scoring_input.setCurrentText(scoring)
    window.docking_panel.cpu_input.setValue(1)
    window.docking_panel.seed_input.setValue(42)
    window.docking_panel.exhaustiveness_input.setValue(1)
    window.docking_panel.modes_input.setValue(2)
    window.docking_panel.run_button.click()
    wait(window)
    assert "Completed:" in window.docking_panel.status.text(), window.docking_panel.status.text()
    run = window.project_store.list_runs()[0]
    assert run.scoring == scoring.lower()
    assert run.status == "completed"
    assert run.stdout
    assert window.results_panel.output_path.is_file()
    assert window.results_panel.table.rowCount() > 0
    window.validation_panel.frame_confirmed.setChecked(True)
    window.validation_panel.run_button.click()
    wait(window)
    assert window.validation_panel.table.rowCount() > 0, window.validation_panel.status.text()
    assert window.validation_panel.table.item(0, 2).text() == "Yes"
    assert list(root.glob("analyses/*/validation.json"))
    window.close()

    moved = tmp_path / "moved project"
    shutil.copytree(root, moved)
    reopened = MainWindow(project_root=moved)
    reopened._load_run_safely(run.id)
    assert reopened.results_panel.output_path.is_relative_to(moved)
    assert reopened.results_panel.table.rowCount() > 0
    assert reopened.docking_panel.scoring_input.currentText() == scoring
    assert reopened.validation_panel.table.rowCount() > 0
    assert reopened.project_panel.analysis_table.rowCount() == 1
    assert len(reopened.project_store.get_run(run.id).metadata['analyses']) == 1
    reopened.close()


def test_analysis_failure_and_csv_export(tmp_path):
    QApplication.instance() or QApplication([])
    window = MainWindow(project_root=tmp_path)
    def fail():
        raise ValueError("specific input error")
    window._start_task(fail, lambda _: None, window.validation_panel.status)
    wait(window)
    assert "specific input error" in window.validation_panel.status.text()
    assert window.validation_panel.isEnabled()
    window.validation_panel.show_rows([(1, 0.0, "Yes", "=HYPERLINK()")])
    path = tmp_path / "out.csv"
    export_table(window.validation_panel.table, path)
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    assert rows[1][3] == "'=HYPERLINK()"
    window.validation_panel.reference_input.setText("new reference")
    assert not window.validation_panel.export_button.isEnabled()
    assert window.validation_panel.table.rowCount() == 0
    window.close()


@pytest.mark.parametrize("method_index", [0, 1])
def test_real_xtb_interaction_gui_records_protocol_and_components(tmp_path, method_index):
    if ToolLocator(Path(__file__).resolve().parents[1]).find("xtb") is None:
        pytest.skip("native xTB is unavailable")
    QApplication.instance() or QApplication([])
    window = MainWindow(project_root=tmp_path / "project")
    receptor, ligand = tmp_path / "receptor.xyz", tmp_path / "ligand.xyz"
    receptor.write_text("3\nwater\nO 0 0 0\nH .9572 0 0\nH -.239 .927 0\n")
    ligand.write_text("3\nwater\nO 0 0 3\nH .9572 0 3\nH -.239 .927 3\n")
    panel = window.scoring_panel
    panel.receptor_input.setText(str(receptor))
    panel.ligand_input.setText(str(ligand))
    panel.method_input.setCurrentIndex(method_index)
    panel.prepared_confirmed.setChecked(True)
    panel.run_button.click()
    wait(window, seconds=90)
    assert "Frozen interaction energy:" in panel.result_label.text(), panel.status.text()
    import json
    results = list((tmp_path / "project").glob("analyses/*/rescoring.json"))
    assert len(results) == 1
    result = json.loads(results[0].read_text())
    assert result["interaction_hartree"] == pytest.approx(
        result["complex_energy"]["hartree"] - result["receptor_energy"]["hartree"] - result["ligand_energy"]["hartree"])
    assert "not binding" in result["interpretation"]
    assert results[0].parent.joinpath("request.json").exists()
    assert window.project_panel.analysis_table.rowCount() == 1
    panel.result_label.clear()
    window._load_analysis(results[0])
    assert "Frozen interaction energy:" in panel.result_label.text()
    window.close()
