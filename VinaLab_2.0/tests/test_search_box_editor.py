from __future__ import annotations

import importlib
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDoubleSpinBox
from vinalab_core.docking.search_box import SearchBox


def _editor_type():
    try:
        module = importlib.import_module("vinalab_ui.widgets.search_box_editor")
    except ModuleNotFoundError:
        return None
    return getattr(module, "SearchBoxEditor", None)


def test_search_box_editor_is_available_for_visual_and_execution_geometry() -> None:
    assert _editor_type() is not None


def test_search_box_editor_replaces_center_in_the_canonical_search_box() -> None:
    application = QApplication.instance() or QApplication([])
    editor_type = _editor_type()
    assert editor_type is not None
    editor = editor_type(
        SearchBox(
            center=(1.0, 2.0, 3.0),
            size=(20.0, 20.0, 20.0),
            coordinate_frame="prepared-receptor-v1",
            margin=4.0,
            source="reference_ligand",
        )
    )
    updates = []
    editor.search_box_changed.connect(updates.append)

    center_x = editor.findChild(QDoubleSpinBox, "centerX")
    assert center_x is not None
    center_x.setValue(11.0)

    assert application is not None
    assert editor.search_box.center == (11.0, 2.0, 3.0)
    assert updates[-1] == editor.search_box


def test_search_box_editor_rejects_a_non_positive_size_before_emitting() -> None:
    QApplication.instance() or QApplication([])
    editor_type = _editor_type()
    assert editor_type is not None
    editor = editor_type(
        SearchBox(
            center=(1.0, 2.0, 3.0),
            size=(20.0, 20.0, 20.0),
            coordinate_frame="prepared-receptor-v1",
            margin=4.0,
            source="reference_ligand",
        )
    )

    size_x = editor.findChild(QDoubleSpinBox, "sizeX")
    assert size_x is not None
    size_x.setValue(0.0)

    assert editor.search_box.size[0] > 0
    assert "Size values must be positive" in editor.validation_message
