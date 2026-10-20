"""Real Qt journeys through conversion, native docking, results and diagnostics."""

import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from core.converter import FileConverter
from core.environment_manager import EnvironmentManager
from core.native_tools import find_vina_executable
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox, QScrollArea
from tabs.docking_tab import DockingTab
from tabs.results_tab import ResultsTab
from tabs.setup_tab import SetupTab

APP = QApplication.instance() or QApplication([])


@pytest.fixture
def real_docking_ui(tmp_path, monkeypatch):
    """Use real widgets and native runtime while isolating user preferences."""
    if find_vina_executable() is None:
        pytest.skip("Bundled Vina CLI unavailable on this platform")
    Chem = pytest.importorskip("rdkit.Chem")
    AllChem = pytest.importorskip("rdkit.Chem.AllChem")
    dependencies = FileConverter.check_dependencies()
    if not (dependencies["meeko"] and dependencies["mk_prepare_receptor"]):
        pytest.skip("Meeko conversion runtime unavailable")
    monkeypatch.setattr(EnvironmentManager, "_user_data_dir", lambda self: tmp_path / "prefs")
    monkeypatch.setattr("core.docking_engine.Vina", None)
    # Embedded browser rendering is covered separately; keep Qt tables/logs real.
    monkeypatch.setattr("tabs.results_tab.QWebEngineView", None)
    dialogs = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: dialogs.append(args[-1]))
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: dialogs.append(args[-1]))
    for name, mol in (("receptor", Chem.MolFromSequence("AG")),
                      ("ligand", Chem.MolFromSmiles("CCO"))):
        molecule = Chem.AddHs(mol)
        assert AllChem.EmbedMolecule(molecule, randomSeed=42) == 0
        if name == "receptor":
            source = tmp_path / "receptor.pdb"
            Chem.MolToPDBFile(Chem.RemoveHs(molecule), str(source))
        else:
            source = tmp_path / "ligand.sdf"
            with Chem.SDWriter(str(source)) as writer:
                writer.write(molecule)
        converted = FileConverter.auto_convert(source, name)
        assert converted.success, converted.errors
    setup = SetupTab()
    setup.set_receptor_file(str(tmp_path / "receptor.pdbqt"))
    setup.set_ligand_file(str(tmp_path / "ligand.pdbqt"))
    results = ResultsTab()
    tab = DockingTab(setup, results, None)
    tab.retranslate_ui("en")
    tab.cpu.setValue(1)
    tab.exhaustiveness.setValue(1)
    tab.fix_seed.setChecked(True)
    for widget in (tab.center_x, tab.center_y, tab.center_z):
        widget.setValue(0)
    for widget in (tab.size_x, tab.size_y, tab.size_z):
        widget.setValue(14)
    tab.resize(1000, 900)
    results.resize(1200, 900)
    tab.show()
    results.show()
    yield tab, results, dialogs
    if tab.worker and tab.worker.isRunning():
        tab.worker.requestInterruption()
        assert tab.worker.wait(120000), "Native worker did not terminate"
    tab.close()
    results.close()
    setup.close()
    APP.processEvents()


def wait_for_run(tab):
    """Process GUI signals until native worker completion, with a bounded wait."""
    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    tab.worker.finished.connect(loop.quit)
    timer.start(90000)
    if tab.worker.isRunning():
        loop.exec()
    assert timer.isActive(), "Native docking timed out"
    timer.stop()
    assert tab.worker.wait(1000)
    APP.processEvents()


def capture_widget(widget, name):
    artifact_dir = os.environ.get("VINALAB_E2E_ARTIFACTS")
    if artifact_dir:
        directory = Path(artifact_dir)
        directory.mkdir(parents=True, exist_ok=True)
        if isinstance(widget, DockingTab):
            widget.findChild(QScrollArea, "tab_scroll_area").ensureWidgetVisible(widget.progress_status)
            APP.processEvents()
        assert widget.grab().save(str(directory / f"{name}.png"))


def test_real_docking_reuses_gui_with_current_settings(real_docking_ui, tmp_path):
    tab, results, dialogs = real_docking_ui
    snapshots = []
    tab.run_parameters.connect(snapshots.append)
    previous_worker = None
    for index, (scorer, seed, modes) in enumerate((("vina", 41, 1), ("vinardo", 97, 2))):
        output = tmp_path / f"run_{index}"
        tab.output_edit.setText(str(output))
        tab.seed.setValue(seed)
        tab.num_modes.setValue(modes)
        tab.scoring_selector.set_selected_keys([scorer])
        tab.run_button.click()
        assert tab.worker is not previous_worker
        assert not tab.run_button.isEnabled()
        assert tab.cancel_button.isEnabled()
        assert tab.progress_bar.maximum() == 0
        wait_for_run(tab)
        assert not dialogs, dialogs
        assert tab.worker.run_status == "completed", results.log_console.toPlainText()
        assert tab.worker.completed_jobs == tab.worker.total_jobs == 1
        assert tab.run_button.isEnabled()
        assert not tab.cancel_button.isEnabled()
        assert tab.progress_bar.value() == 100
        assert "Completed" in tab.progress_status.text()
        assert 1 <= len(results.results) <= modes
        assert results.table.rowCount() == len(results.results)
        assert {row["scoring_key"] for row in results.results} == {scorer}
        assert snapshots[-1]["seed"] == seed
        assert snapshots[-1]["num_modes"] == modes
        log = tab.worker.log_path.read_text(encoding="utf-8")
        assert f"--seed {seed}" in log
        assert f"--num_modes {modes}" in log
        assert f"--scoring {scorer}" in log
        assert "AutoDock Vina" in results.log_console.toPlainText()
        for row in results.results:
            assert "REMARK VINA RESULT:" in Path(row["output_file"]).read_text()
        capture_widget(tab, f"{scorer}_completed")
        capture_widget(results, f"{scorer}_results")
        previous_worker = tab.worker
    assert snapshots[0]["seed"] == 41
    assert snapshots[0]["scoring_functions"] == ["vina"]


def test_real_worker_error_stays_visible_and_saved(real_docking_ui, tmp_path):
    tab, results, dialogs = real_docking_ui
    tab.output_edit.setText(str(tmp_path / "failed_run"))
    tab.reference_ligand_edit.setText(str(tmp_path / "missing_reference.pdbqt"))
    tab.run_button.click()
    wait_for_run(tab)
    assert tab.worker.run_status == "failed"
    assert dialogs and "missing_reference.pdbqt" in dialogs[-1]
    assert not results.results
    assert "ERROR:" in results.log_console.toPlainText()
    assert "missing_reference.pdbqt" in results.log_console.toPlainText()
    assert "Traceback" in tab.worker.log_path.read_text(encoding="utf-8")
    assert tab.progress_bar.value() == 0
    assert "Failed" in tab.progress_status.text()
    assert tab.run_button.isEnabled()
    capture_widget(results, "error_log")


def test_real_flexible_docking_exports_only_once_at_docked_coordinates(real_docking_ui, tmp_path):
    """Meeko torsion trees must survive staging and remain separated at export."""
    import numpy as np
    from core.docking_engine import extract_pose_model
    from openbabel import openbabel as ob
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from tabs.results_dialogs import ExportWorker

    tab, results, dialogs = real_docking_ui
    peptide = Chem.AddHs(Chem.MolFromSequence("AKA"))
    assert AllChem.EmbedMolecule(peptide, randomSeed=42) == 0
    AllChem.MMFFOptimizeMolecule(peptide)
    pdb = tmp_path / "flexible.pdb"
    Chem.MolToPDBFile(Chem.RemoveHs(peptide), str(pdb))
    command = [sys.executable, "-m", "meeko.cli.mk_prepare_receptor", "--read_pdb", str(pdb),
               "-o", str(tmp_path / "flexible"), "-p", "--flexres", "A:2"]
    preparation = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert preparation.returncode == 0, preparation.stdout + preparation.stderr
    converted = FileConverter.convert_pdb_to_pdbqt_receptor(pdb, pdb.with_suffix(".pdbqt"))
    assert converted.success, converted.errors
    tab.setup_provider.set_receptor_file(str(converted.output_path))
    tab.setup_provider.fully_rigid_checkbox.setChecked(False)
    tab.setup_provider.rigid_receptor_edit.setText(str(tmp_path / "flexible_rigid.pdbqt"))
    tab.setup_provider.flex_receptor_edit.setText(str(tmp_path / "flexible_flex.pdbqt"))
    tab.output_edit.setText(str(tmp_path / "docking"))
    tab.seed.setValue(113)
    tab.num_modes.setValue(1)
    tab.scoring_selector.set_selected_keys(["vina"])
    tab.run_button.click()
    wait_for_run(tab)
    assert not dialogs, dialogs
    assert tab.worker.run_status == "completed", results.log_console.toPlainText()
    row = {**results.results[0], "_export_name": "flexible_pose"}
    pose = extract_pose_model(Path(row["output_file"]), row["mode"], include_model=False)
    ligand_lines, flexible_lines = [], []
    in_residue = False
    for line in pose.splitlines():
        if line.startswith("BEGIN_RES"):
            in_residue = True
        elif line.startswith("END_RES"):
            in_residue = False
        elif line.startswith(("ATOM  ", "HETATM")):
            (flexible_lines if in_residue else ligand_lines).append(line)
    assert flexible_lines and ligand_lines

    def atoms_by_identity(text):
        return {(line[12:16].strip(), line[17:20], line[21:27]): line
                for line in text.splitlines() if line.startswith(("ATOM  ", "HETATM"))}

    def atom_values(line):
        element = {"OA": "O", "NA": "N", "HD": "H", "A": "C"}.get(line.split()[-1], line.split()[-1])
        return element, *(float(line[start:start + 8]) for start in (30, 38, 46))

    rigid = atoms_by_identity((tmp_path / "flexible_rigid.pdbqt").read_text())
    flex = atoms_by_identity("\n".join(flexible_lines))
    expected_receptor = {**rigid, **flex}
    original = atoms_by_identity(converted.output_path.read_text())
    assert expected_receptor.keys() == original.keys()
    assert any(np.linalg.norm(np.array(atom_values(line)[1:]) - atom_values(original[key])[1:]) > 0.1
               for key, line in flex.items()), "Actual flexible sidechain must move"
    expected_ligand = sorted(atom_values(line) for line in ligand_lines)
    expected_complex = sorted(atom_values(line) for line in [*expected_receptor.values(), *ligand_lines])
    for format_name in ("pdbqt", "pdb", "mol2"):
        output = tmp_path / format_name
        exporter = ExportWorker([row], output, format_name, True, "en")
        completed = []
        exporter.completed.connect(lambda *args, target=completed: target.append(args))
        exporter.run()
        assert completed == [(1, "", False)]
        complex_format = "mol2" if format_name == "mol2" else "pdb"
        for filename, expected in ((f"flexible_pose_complex.{complex_format}", expected_complex),
                                   (f"flexible_pose.{format_name}", expected_ligand)):
            path = output / filename
            reader = ob.OBConversion()
            assert reader.SetInFormat(path.suffix[1:])
            molecule = ob.OBMol()
            assert reader.ReadString(molecule, path.read_text())
            actual = sorted((ob.GetSymbol(atom.GetAtomicNum()), atom.GetX(), atom.GetY(), atom.GetZ())
                            for atom in ob.OBMolAtomIter(molecule))
            assert len(actual) == len(expected)
            assert [atom[0] for atom in actual] == [atom[0] for atom in expected]
            np.testing.assert_allclose([atom[1:] for atom in actual], [atom[1:] for atom in expected],
                                       atol=0.00051, rtol=0)
