"""Regression checks for export isolation and reference handoff."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from tabs.results_dialogs import ExportComplexDialog, ExportWorker
from tabs.prepare_protein_tab import PrepareProteinTab
from tabs.results_view import build_box_preview_html

APP = QApplication.instance() or QApplication([])


def test_export_dialog_runs_worker_and_finishes(tmp_path):
    from PySide6.QtCore import QEventLoop, QTimer
    source = tmp_path / "input.pdbqt"
    source.write_text("REMARK pose\n")
    row = dict(ligand_name="lig", mode=1, affinity=-1, scoring_key="vina",
               output_file=str(source))
    dialog = ExportComplexDialog([row], lang="en")
    dialog.all_radio.setChecked(True)
    dialog.complex_checkbox.setChecked(False)
    dialog.folder_edit.setText(str(tmp_path))
    loop = QEventLoop()
    dialog.accepted.connect(loop.quit)
    QTimer.singleShot(10000, loop.quit)
    with patch("tabs.results_dialogs.QMessageBox.information"), \
         patch("tabs.results_dialogs.QMessageBox.critical") as failed:
        dialog._export()
        loop.exec()
    dialog.worker.wait(10000)
    assert not dialog.worker.isRunning()
    failed.assert_not_called()
    assert dialog.result() == 1
    assert (tmp_path / "lig_vina_pose1.pdbqt").read_text() == "REMARK pose\n"


def test_exports_preserve_scorers_and_existing_files(tmp_path):
    rows = []
    for scorer in ("vina", "vinardo"):
        source = tmp_path / (scorer + ".pdbqt")
        source.write_text("REMARK " + scorer + "\n")
        rows.append(dict(ligand_name="lig", mode=1, affinity=-1,
                         scoring_key=scorer, output_file=str(source)))
    dialog = ExportComplexDialog(rows, lang="en")
    dialog.all_radio.setChecked(True)
    dialog.complex_checkbox.setChecked(False)
    dialog.folder_edit.setText(str(tmp_path))
    plans = dialog._planned_rows()
    worker = ExportWorker(plans, tmp_path, "pdbqt", False, "en")
    worker.run()
    assert (tmp_path / "lig_vina_pose1.pdbqt").read_text() == "REMARK vina\n"
    assert (tmp_path / "lig_vinardo_pose1.pdbqt").read_text() == "REMARK vinardo\n"
    assert all(row["_export_name"].endswith("_2") for row in dialog._planned_rows())
    assert "vina" in dialog.preview_label.text()


def test_export_cancellation_does_not_publish_current_pose(tmp_path):
    worker = ExportWorker([{"_export_name": "test"}], tmp_path, "pdbqt", False, "en")
    with patch.object(worker, "isInterruptionRequested", side_effect=[False, True, True]), \
         patch.object(worker, "_export_row") as export:
        worker.run()
    export.assert_called_once()
    assert list(tmp_path.iterdir()) == []


def test_reference_button_emits_extracted_path(tmp_path):
    tab = PrepareProteinTab()
    received = []
    tab.reference_selected.connect(received.append)
    tab.extracted_ligand = tmp_path / "ligand.pdb"
    tab.reference_button.setEnabled(True)
    tab.reference_button.click()
    assert received == [str(tab.extracted_ligand)]
    tab.retranslate_ui("en")
    assert tab.reference_button.text() == "Use as reference"


def test_box_view_uses_bundled_library():
    page = build_box_preview_html(None, None, "en")
    assert "https://cdn" not in page
    library = Path(__file__).resolve().parents[1] / "ui" / "3Dmol-min.js"
    assert library.is_file()
    assert library.as_uri() in page
    assert "Box not defined" in page
    assert "No receptor" in page
