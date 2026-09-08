"""Conversion identity and molecular rendering regressions."""

from unittest.mock import patch
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

APP = QApplication.instance() or QApplication([])

from core.converter import ConversionResult, FileConverter
from tabs.results_view import _box_preview_js, pdbqt_text_to_view_pdb, build_pose_view_html
from ui.converter_widget import ConversionWorker


def test_meeko_failure_is_not_silently_replaced(tmp_path):
    source, target = tmp_path / "in.pdb", tmp_path / "out.pdbqt"
    failure = ConversionResult(False, target, "missing residue A:12", "Meeko failed")
    with patch.object(FileConverter, "_convert_receptor_via_meeko", return_value=failure), \
         patch.object(FileConverter, "_convert_via_openbabel") as fallback:
        result = FileConverter.convert_pdb_to_pdbqt_receptor(source, target)
    assert not result.success
    assert "A:12" in result.log
    fallback.assert_not_called()


def test_openbabel_requires_explicit_selection(tmp_path):
    source, target = tmp_path / "in.pdb", tmp_path / "out.pdbqt"
    source.write_text("ATOM\n")
    worker = ConversionWorker([source], target, "receptor", "openbabel")
    with patch.object(FileConverter, "_convert_via_openbabel") as convert:
        worker._convert_one(source, target)
    assert convert.call_args.args[:3] == (source, target, True)


def test_receptor_hetero_amino_acids_can_render_cartoon():
    text = "HETATM    1  CA  ALA A   1       0.000   0.000   0.000  1.00  0.00     0.000 C\n"
    assert pdbqt_text_to_view_pdb(text, include_conect=False).startswith("ATOM  ")
    assert pdbqt_text_to_view_pdb(text, include_conect=True).startswith("HETATM")


def test_box_has_twelve_edges_without_surface_occlusion():
    script = _box_preview_js(dict(center_x=1, center_y=2, center_z=3, size_x=10, size_y=12, size_z=14))
    assert script.count("viewer.addCylinder") == 12
    assert "wireframe" not in script
    assert "radius: 0.10" in script


def test_pose_styles_only_nearby_residues(tmp_path):
    pdb = tmp_path / "molecule.pdb"
    pdb.write_text("END\n")
    page = build_pose_view_html(dict(ligand_name="test", mode=1), pdb, pdb)
    assert "nearbyResidues.has" in page
    assert "addSurface" not in page
    assert "within:" not in page


def test_preparation_direct_pdbqt_uses_meeko_worker(tmp_path):
    from PySide6.QtWidgets import QApplication
    from tabs.prepare_protein_tab import PrepareProteinTab
    app = QApplication.instance() or QApplication([])
    tab = PrepareProteinTab()
    tab.input_path = tmp_path / "in.pdb"
    tab.input_path.write_text("ATOM      1  CA  ALA A   1       0.000   0.000   0.000\nEND\n")
    tab.output_edit.setText(str(tmp_path / "prepared.pdb"))
    tab.pdbqt_checkbox.setChecked(True)
    assert tab.output_edit.text().endswith(".pdbqt")
    received = []
    tab.receptor_prepared.connect(received.append)
    with patch("tabs.prepare_protein_tab.ConversionWorker") as worker:
        tab._run_preparation()
        worker.return_value.start.assert_called_once()
        assert worker.call_args.args[2] == "receptor"
        target = worker.call_args.args[1]
        tab._pdbqt_finished([ConversionResult(True, target, "Meeko", "")])
    assert received == [str(tmp_path / "prepared.pdbqt")]


def test_analysis_headers_do_not_shrink_to_fit_notebooks():
    from PySide6.QtWidgets import QApplication, QHeaderView
    from tabs.results_tab import ResultsTab
    app = QApplication.instance() or QApplication([])
    with patch("tabs.results_tab.QWebEngineView", None):
        tab = ResultsTab()
    for table in (tab.interaction_table, tab.consensus_table, tab.cluster_table):
        if table.columnCount() == 0:
            table.setColumnCount(1)
        assert table.horizontalHeader().sectionResizeMode(0) == QHeaderView.ResizeToContents
