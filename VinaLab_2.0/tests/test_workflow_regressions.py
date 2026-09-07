import os
from time import monotonic, sleep

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QLabel

from vinalab_core.docking.docking_service import DockingRunResult
from vinalab_core.docking.vina_runner import VinaProcessResult
from vinalab_ui.mainwindow import MainWindow


def inputs(tmp_path):
    atom = 'ATOM      1  C1  LIG     1       0.000   0.000   0.000  0.00  0.00     0.000 C\n'
    receptor = tmp_path / 'receptor.pdbqt'
    ligand = tmp_path / 'ligand.pdbqt'
    receptor.write_text(atom)
    ligand.write_text('ROOT\n' + atom + 'ENDROOT\nTORSDOF 0\n')
    return receptor, ligand


class FailureService:
    def __init__(self):
        self.outputs = []

    def run(self, **kwargs):
        self.outputs.append(kwargs['output'])
        return DockingRunResult(VinaProcessResult((), 1, '', 'deliberate failure'), ())


def wait_idle(window):
    deadline = monotonic() + 3
    while window.active_worker is not None and monotonic() < deadline:
        QApplication.instance().processEvents()
        sleep(0.01)
    assert window.active_worker is None


def test_direct_boron_and_replacement_are_revalidated(tmp_path):
    QApplication.instance() or QApplication([])
    receptor, ligand = inputs(tmp_path)
    boron = tmp_path / 'boron.pdbqt'
    boron.write_text(ligand.read_text().replace('0.000 C', '0.000 B'))
    window = MainWindow(project_root=tmp_path, docking_service=FailureService())
    window.docking_panel.set_inputs(receptor, boron)
    assert not window.docking_panel.run_button.isEnabled()
    window.ligand_inspector.inspect_path(boron)
    window.docking_panel.ligand_input.setText(str(ligand))
    assert window.docking_panel.run_button.isEnabled()
    window.close()


def test_run_directories_and_failure_status_survive_worker_finish(tmp_path):
    QApplication.instance() or QApplication([])
    service = FailureService()
    window = MainWindow(project_root=tmp_path, docking_service=service)
    window.docking_panel.set_inputs(*inputs(tmp_path))
    for _ in range(2):
        window.docking_panel.run_button.click()
        wait_idle(window)
        assert 'deliberate failure' in window.docking_panel.status.text()
    assert len(set(service.outputs)) == 2
    assert all(path.parent.joinpath('ligand.pdbqt').exists() for path in service.outputs)
    assert len(window.project_store.list_runs()) == 2
    assert all(run.status == 'failed' for run in window.project_store.list_runs())
    window.close()


def test_project_and_validation_are_functional_and_project_can_reopen(tmp_path):
    QApplication.instance() or QApplication([])
    window = MainWindow(project_root=tmp_path, docking_service=FailureService())
    assert not isinstance(window.project_panel, QLabel)
    assert not isinstance(window.validation_panel, QLabel)
    other = tmp_path / 'other project'
    window.open_project(other)
    assert window.project_store.path == other / 'vinalab.sqlite'
    assert window.project_panel.table.rowCount() == 0
    window.close()


def test_close_is_rejected_while_worker_active(tmp_path):
    QApplication.instance() or QApplication([])
    class SlowService(FailureService):
        def run(self, **kwargs):
            sleep(0.15)
            return super().run(**kwargs)
    window = MainWindow(project_root=tmp_path, docking_service=SlowService())
    window.docking_panel.set_inputs(*inputs(tmp_path))
    window.docking_panel.run_button.click()
    assert not window.close()
    wait_idle(window)
    assert window.close()


def test_project_switch_clears_reference_geometry_and_frame(tmp_path):
    QApplication.instance() or QApplication([])
    receptor, _ = inputs(tmp_path)
    window = MainWindow(project_root=tmp_path / 'a', docking_service=FailureService())
    window.search_box_editor.set_reference(receptor, coordinates=[(10., 20., 30.)])
    assert window.search_box_editor.fit_button.isEnabled()
    window.open_project(tmp_path / 'b')
    assert not window.search_box_editor.fit_button.isEnabled()
    assert window.search_box_editor.reference_path is None
    assert window.search_box_editor.viewer.scene_data['reference'] == []
    assert window.search_box.coordinate_frame == 'unconfigured-receptor'
    window.close()


def test_scoring_settings_invalidate_previous_result(tmp_path):
    QApplication.instance() or QApplication([])
    window = MainWindow(project_root=tmp_path)
    panel = window.scoring_panel
    panel.result_label.setText('old energy')
    panel.charge_ligand.setValue(1)
    assert not panel.result_label.text()
    panel.result_label.setText('old energy')
    panel.method_input.setCurrentIndex(1)
    assert not panel.result_label.text()
    window.close()


def test_malformed_analysis_does_not_break_project_or_display_false_success(tmp_path):
    import json
    QApplication.instance() or QApplication([])
    analysis = tmp_path / 'analyses' / 'bad'
    analysis.mkdir(parents=True)
    manifest = analysis / 'validation.json'
    manifest.write_text(json.dumps({'created_at': 123, 'frame_confirmed': 'false',
        'results': [{'mode': 1, 'comparable': True, 'rmsd': float('nan'), 'reason': ''}]}))
    window = MainWindow(project_root=tmp_path)
    window._load_analysis(manifest)
    assert window.validation_panel.table.rowCount() == 0
    assert not window.validation_panel.frame_confirmed.isChecked()
    assert not window.validation_panel.export_button.isEnabled()
    assert 'Cannot load analysis' in window.project_panel.status.text()
    window.close()
