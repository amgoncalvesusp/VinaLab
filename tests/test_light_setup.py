"""Small-screen and multi-ligand workflow regressions."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QVBoxLayout, QWidget
from core.scrolling import ScrollManager, WheelGuard
from tabs.setup_tab import SetupTab

APP = QApplication.instance() or QApplication([])


def test_select_multiple_ligands_and_switch_to_folder(tmp_path):
    files = [tmp_path / name for name in ("one.pdbqt", "two.pdbqt")]
    for path in files:
        path.write_text("ROOT\nENDROOT\nTORSDOF 0\n")
    tab = SetupTab()
    tab.set_ligand_files([str(path) for path in files])
    assert tab.ligand_paths() == files
    assert "2" in tab.batch_count_label.text()
    folder = tmp_path / "batch"
    folder.mkdir()
    batch = folder / "three.pdbqt"
    batch.write_text("ROOT\nENDROOT\nTORSDOF 0\n")
    tab.set_ligand_folder(str(folder))
    assert tab.ligand_paths() == [batch]
    tab.set_ligand_file(str(files[0]))
    assert tab.ligand_paths() == [files[0]]


def test_combo_popup_has_room_for_both_molecule_types():
    guard = WheelGuard(APP)
    APP.installEventFilter(guard)
    combo = QComboBox()
    combo.addItems(["Ligante", "Receptor (proteína)"])
    combo.resize(180, 40)
    combo.show()
    combo.showPopup()
    APP.processEvents()
    assert combo.view().sizeHintForRow(0) >= 24
    assert combo.view().viewport().height() >= 2 * combo.view().sizeHintForRow(0)
    combo.hidePopup()
    combo.close()
    APP.removeEventFilter(guard)


def test_scroll_area_preserves_control_height():
    content = QWidget()
    layout = QVBoxLayout(content)
    for index in range(20):
        label = QLabel(str(index))
        label.setMinimumHeight(32)
        layout.addWidget(label)
    area = ScrollManager.wrap(content)
    area.resize(320, 240)
    area.show()
    APP.processEvents()
    assert area.verticalScrollBar().maximum() > 0
    area.verticalScrollBar().setValue(area.verticalScrollBar().maximum())
    assert content.height() >= 640
    area.close()
