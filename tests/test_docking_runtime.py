"""Runtime regressions: fresh settings, honest progress and retained diagnostics."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import io
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from PySide6.QtWidgets import QApplication
from core.docking_engine import DockingWorker
from tabs.docking_tab import DockingTab
from tabs.setup_tab import SetupTab

APP = QApplication.instance() or QApplication([])


def worker_for(tmp_path, parameters=None, ligands=None):
    return DockingWorker(tmp_path / "receptor.pdbqt", None, None,
                         ligands or [tmp_path / "ligand.pdbqt"], tmp_path,
                         parameters or {"scoring_functions": ["vina"]})


def tab_for(tmp_path):
    setup = SetupTab()
    for name in ("receptor", "ligand"):
        (tmp_path / f"{name}.pdbqt").write_text("ROOT\nENDROOT\nTORSDOF 0\n")
    setup.set_receptor_file(str(tmp_path / "receptor.pdbqt"))
    setup.set_ligand_file(str(tmp_path / "ligand.pdbqt"))
    with patch.object(DockingTab, "_refresh_dependency_status"), \
         patch("tabs.docking_tab.ScoringFunctionSelector._save_keys"):
        tab = DockingTab(setup, Mock(), Mock())
    tab.scoring_selector.prefs_path = tmp_path / "prefs.json"
    tab.output_edit.setText(str(tmp_path))
    return tab


def test_worker_snapshots_nested_parameters(tmp_path):
    params = {"scoring_functions": ["vina"]}
    worker = worker_for(tmp_path, params)
    params["scoring_functions"].append("vinardo")
    assert worker._selected_scoring_functions() == ["vina"]


def test_fully_rigid_ignores_previous_rigid_fragment(tmp_path):
    tab = SetupTab()
    tab.rigid_receptor_edit.setText(str(tmp_path / "fragment.pdbqt"))
    tab.fully_rigid_checkbox.setChecked(True)
    assert tab.rigid_receptor_path() is None
    assert tab.flexible_receptor_path() is None


def test_load_config_resets_reference_and_random_seed(tmp_path):
    tab = tab_for(tmp_path)
    tab.reference_ligand_edit.setText("old.pdbqt")
    tab.fix_seed.setChecked(True)
    tab._apply_config_values({"reference_ligand": "", "seed": "0"})
    assert tab.current_parameters()["reference_ligand"] == ""
    assert not tab.fix_seed.isChecked()


def test_next_run_uses_changed_settings_without_restart(tmp_path):
    tab = tab_for(tmp_path)
    with patch.object(DockingWorker, "start"):
        tab.launch_docking()
        first = tab.worker
        tab.exhaustiveness.setValue(17)
        tab.center_x.setValue(8.5)
        tab.scoring_selector.set_selected_keys(["vinardo"])
        tab.launch_docking()
        assert tab.worker.parameters["exhaustiveness"] == 17
        assert tab.worker.parameters["center_x"] == 8.5
        assert tab.worker.parameters["scoring_functions"] == ["vinardo"]
        assert first.parameters["exhaustiveness"] == 8
        assert tab.progress_bar.maximum() == 0
    tab._worker_finished()


def test_setup_rejects_sanitized_name_collisions(tmp_path):
    tab = SetupTab()
    paths = [tmp_path / name for name in ("a b.pdbqt", "a_b.pdbqt")]
    for path in paths:
        path.write_text("ROOT\nENDROOT\nTORSDOF 0\n")
    tab.set_receptor_file(str(paths[0]))
    tab.set_ligand_files([str(path) for path in paths])
    assert not tab.validate_inputs()


def test_worker_rejects_collisions_before_preparation(tmp_path):
    worker = worker_for(tmp_path, ligands=[tmp_path / "a b.pdbqt", tmp_path / "a_b.pdbqt"])
    errors = []
    worker.error_signal.connect(errors.append)
    with patch("core.docking_engine.Vina", object()), \
         patch.object(worker, "_prepare_pdbqt_inputs") as prepare:
        worker.run()
    prepare.assert_not_called()
    assert errors


def test_failed_job_has_persistent_traceback_and_failed_status(tmp_path):
    worker = worker_for(tmp_path)
    errors = []
    worker.error_signal.connect(errors.append)
    with patch("core.docking_engine.Vina", object()), \
         patch.object(worker, "_prepare_pdbqt_inputs"), \
         patch.object(worker, "_validate_ligand_inside_grid", return_value=None), \
         patch.object(worker, "_run_ligand_with_scoring", side_effect=RuntimeError("native failure")):
        worker.run()
    assert worker.run_status == "failed"
    assert worker.failed_jobs == 1
    assert errors
    log = worker.log_path.read_text(encoding="utf-8")
    assert "native failure" in log
    assert "Traceback" in log
    assert "scoring_functions" in log


def test_cancel_before_job_does_not_claim_completion(tmp_path):
    worker = worker_for(tmp_path)
    with patch("core.docking_engine.Vina", object()), \
         patch.object(worker, "_prepare_pdbqt_inputs"), \
         patch.object(worker, "isInterruptionRequested", return_value=True), \
         patch.object(worker, "_run_ligand_with_scoring") as dock:
        worker.run()
    dock.assert_not_called()
    assert worker.run_status == "cancelled"
    assert worker.completed_jobs == 0


def test_error_is_visible_after_dialog_closes(tmp_path):
    tab = tab_for(tmp_path)
    with patch("tabs.docking_tab.QMessageBox.critical"):
        tab._show_error("native failure")
    tab.results_consumer.append_log.assert_called_with("ERROR: native failure")


def test_failed_run_never_shows_success_progress(tmp_path):
    tab = tab_for(tmp_path)
    tab.worker = SimpleNamespace(run_status="failed", completed_jobs=1, total_jobs=1,
                                 failed_jobs=1)
    tab._worker_finished()
    assert tab.run_button.isEnabled()
    assert tab.progress_bar.value() == 0
    assert "1" in tab.progress_status.text()


def test_charge_repair_never_modifies_source_inputs(tmp_path):
    worker = worker_for(tmp_path)
    original = "ATOM      1  C   LIG A   1       0.000   0.000   0.000  0.00  0.00     0.000 C\n"
    inputs = [worker.receptor_path, *worker.ligand_paths]
    for path in inputs:
        path.write_text(original)
    def repair(path, _role):
        path.write_text("repaired copy\n")
        return True
    with patch("core.docking_engine.validate_pdbqt_charges", return_value=False), \
         patch("core.docking_engine.repair_pdbqt_charges", side_effect=repair), \
         patch("core.docking_engine.validate_ligand_pdbqt"):
        worker._prepare_pdbqt_inputs()
    assert all(path.read_text() == original for path in inputs)
    assert worker.receptor_path.read_text() == "repaired copy\n"
    assert worker.ligand_paths[0].read_text() == "repaired copy\n"


def test_cli_streams_diagnostics_before_exit(tmp_path):
    worker = worker_for(tmp_path, {"scoring_function": "vina", "cpu": 1, "seed": 0,
        "center_x": 0, "center_y": 0, "center_z": 0, "size_x": 10,
        "size_y": 10, "size_z": 10, "exhaustiveness": 1, "num_modes": 1,
        "energy_range": 3, "min_rmsd": 1})
    messages = []
    worker.log_signal.connect(messages.append)
    process = MagicMock(stdout=io.StringIO("native diagnostic\n"))
    process.__enter__.return_value = process
    def wait():
        assert "native diagnostic" in messages
        return 1
    process.wait.side_effect = wait
    with patch("core.docking_engine.subprocess.Popen", return_value=process), \
         patch("core.docking_engine.native_tool_env", return_value={}):
        import pytest
        with pytest.raises(RuntimeError, match="código 1"):
            worker._dock_single_ligand_cli(worker.ligand_paths[0], tmp_path / "vina")


def test_report_snapshot_changes_only_on_launch(tmp_path):
    tab = tab_for(tmp_path)
    snapshots = []
    tab.run_parameters.connect(snapshots.append)
    with patch.object(DockingWorker, "start"):
        tab.launch_docking()
        tab.exhaustiveness.setValue(18)
        assert len(snapshots) == 1
        assert snapshots[0]["exhaustiveness"] == 8
        tab.launch_docking()
        assert snapshots[-1]["exhaustiveness"] == 18
    tab._worker_finished()


def test_partial_batch_failure_reports_counts_and_keeps_valid_rows(tmp_path):
    worker = worker_for(tmp_path, {"scoring_functions": ["vina", "vinardo"]})
    batches = []
    worker.result_signal.connect(batches.append)
    with patch("core.docking_engine.Vina", object()), \
         patch.object(worker, "_prepare_pdbqt_inputs"), \
         patch.object(worker, "_validate_ligand_inside_grid", return_value="outside grid"), \
         patch.object(worker, "_run_ligand_with_scoring", side_effect=[[{"mode": 1}], RuntimeError("bad scorer")]):
        worker.run()
    assert batches == [[{"mode": 1}]]
    assert (worker.completed_jobs, worker.total_jobs, worker.failed_jobs) == (2, 2, 1)
    assert worker.run_status == "failed"


def test_successful_batch_marks_completion(tmp_path):
    worker = worker_for(tmp_path)
    with patch("core.docking_engine.Vina", object()), \
         patch.object(worker, "_prepare_pdbqt_inputs"), \
         patch.object(worker, "_validate_ligand_inside_grid", return_value=None), \
         patch.object(worker, "_run_ligand_with_scoring", return_value=[{"mode": 1}]):
        worker.run()
    assert worker.run_status == "completed"
    assert worker.completed_jobs == worker.total_jobs == 1
    assert worker.failed_jobs == 0


def test_reference_rmsd_excludes_flexible_receptor_atoms(tmp_path):
    worker = worker_for(tmp_path, {"reference_ligand": "reference.pdbqt"})
    atom = "ATOM      1  C   LIG A   1       0.000   0.000   0.000  0.00  0.00     0.000 C\n"
    worker._reference_ligand_text = atom
    output = tmp_path / "out.pdbqt"
    output.write_text("MODEL 1\n" + atom + "BEGIN_RES ARG A 9\n" + atom.replace("LIG", "ARG") + "END_RES ARG A 9\nENDMDL\n")
    rows = [{"output_file": str(output), "mode": 1}]
    worker._annotate_reference_rmsd(rows)
    assert rows[0]["reference_validation"] == "Pass"


def test_flexible_receptor_sanitization_preserves_residue_torsion_tree(tmp_path):
    from core.file_utils import sanitize_pdbqt_for_vina
    source = tmp_path / "flex.pdbqt"
    flexible = (
        "BEGIN_RES LYS A 2\n"
        "ROOT\n"
        "ATOM      1  CA  LYS A   2      -0.278   0.169  -0.686  1.00  0.00    +0.171 C\n"
        "ENDROOT\n"
        "BRANCH   1   2\n"
        "ATOM      2  CB  LYS A   2      -0.264   1.679  -0.954  1.00  0.00    +0.035 C\n"
        "ENDBRANCH   1   2\n"
        "END_RES LYS A 2\n"
    )
    source.write_text("HEADER imported protein\n" + flexible)
    result = sanitize_pdbqt_for_vina(source, tmp_path, "flex_receptor")
    assert result.path.read_text() == flexible
    assert result.removed_counts == {"HEADER": 1}
    assert source.read_text() == "HEADER imported protein\n" + flexible
    clean = sanitize_pdbqt_for_vina(result.path, tmp_path, "flex_receptor")
    assert not clean.changed


def test_rigid_receptor_still_strips_torsion_tree(tmp_path):
    from core.file_utils import sanitize_pdbqt_for_vina
    source = tmp_path / "rigid.pdbqt"
    atom = "ATOM      1  CA  LYS A   2      -0.278   0.169  -0.686  1.00  0.00    +0.171 C\n"
    source.write_text("ROOT\n" + atom + "ENDROOT\n")
    result = sanitize_pdbqt_for_vina(source, tmp_path, "rigid_receptor")
    assert result.path.read_text() == atom
    assert result.removed_counts == {"ROOT": 1, "ENDROOT": 1}
