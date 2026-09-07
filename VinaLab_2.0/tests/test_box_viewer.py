from __future__ import annotations

import hashlib
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from vinalab_core.docking.search_box import SearchBox
from vinalab_ui.widgets.box_viewer import validate_coordinates
from vinalab_ui.widgets.search_box_editor import SearchBoxEditor


@pytest.fixture
def editor():
    app = QApplication.instance() or QApplication([])
    widget = SearchBoxEditor(SearchBox((0, 0, 0), (20, 20, 20), "receptor", 4, "user"))
    yield widget
    widget.close()
    assert app is not None


def test_canonical_box_updates_inputs_and_preview_without_emitting(editor):
    changes = []
    editor.search_box_changed.connect(changes.append)
    box = SearchBox((10, 20, 30), (8, 9, 10), "other", 2, "imported")
    editor.set_search_box(box)
    assert editor._center_inputs[0].value() == 10
    assert editor.viewer.scene_data["box"]["center"] == [10, 20, 30]
    assert editor.margin_input.value() == 2
    assert changes == []


def test_reference_fits_with_margin_and_emits_valid_path(editor, tmp_path):
    path = tmp_path / "reference.pdb"
    path.write_text("reference", encoding="utf-8")
    loaded, changed = [], []
    editor.reference_selected.connect(loaded.append)
    editor.search_box_changed.connect(changed.append)
    editor.set_reference(path, coordinates=[(1, 2, 3), (5, 6, 7)])
    editor.margin_input.setValue(2)
    editor.fit_reference()
    assert loaded == [path.resolve()]
    assert editor.search_box.center == (3, 4, 5)
    assert editor.search_box.size == (8, 8, 8)
    assert editor.search_box.coordinate_frame == "receptor"
    assert editor.search_box.source == "reference_ligand"
    assert changed[-1] == editor.search_box


def test_invalid_reference_does_not_replace_previous_state(editor, tmp_path):
    path = tmp_path / "reference.pdb"
    path.touch()
    editor.set_reference(path, coordinates=[(1, 2, 3)])
    before = editor.search_box
    events = []
    editor.reference_selected.connect(events.append)
    with pytest.raises(ValueError):
        editor.set_reference(path, coordinates=[(float("nan"), 0, 0)])
    assert editor.search_box == before
    assert events == []


def test_structure_and_reference_can_share_injected_reader(tmp_path):
    app = QApplication.instance() or QApplication([])
    path = tmp_path / "molecule.sdf"
    path.touch()
    editor = SearchBoxEditor(
        SearchBox((0, 0, 0), (20, 20, 20), "receptor", 4, "user"),
        coordinate_reader=lambda p: [(1, 2, 3), (4, 5, 6)],
    )
    editor.set_structure(path)
    assert editor.viewer.scene_data["receptor"] == [[1, 2, 3], [4, 5, 6]]
    assert editor.search_box.coordinate_frame == "receptor"
    editor.close()
    assert app is not None


@pytest.mark.parametrize("points", [[], [(1, 2)], [(1, 2, float("inf"))]])
def test_coordinate_validation_rejects_invalid_arrays(points):
    with pytest.raises(ValueError):
        validate_coordinates(points)


def test_viewer_assets_are_local_and_pinned():
    assets = Path(__file__).parents[1] / "vinalab_ui" / "widgets" / "assets" / "box_viewer"
    assert (assets / "three.module.js").is_file()
    assert (assets / "OrbitControls.js").is_file()
    assert "643680ed5fc73ba27e32a6529d59cae8c8b3825c" in (assets / "NOTICE.md").read_text()
    assert "https:" not in (assets / "index.html").read_text()
    hashes = {
        "three.module.js": "76dea8151bc9352aef3528b4262e249b2604f62543828328db978d060d61a495",
        "OrbitControls.js": "5a44a9e86a2a0fb11933eed69bc2cd33c76a496854c1aed6ed776efa87d7b064",
        "LICENSE": "852e0e8699169bf9f6fdc6bda3e682d078dcbc738b5d33e74df594721bff271d",
    }
    for name, expected in hashes.items():
        assert hashlib.sha256((assets / name).read_bytes()).hexdigest() == expected


def test_hidden_editor_never_constructs_webengine(editor):
    assert editor.viewer._web is None
    assert editor.viewer._profile is None
    editor.viewer.reset_view()
    assert editor.viewer._web is None


def test_default_reader_and_failed_load_preserve_state(editor, tmp_path):
    source = tmp_path / "reference.pdb"
    source.write_text("ATOM      1  C   LIG A   1       1.000   2.000   3.000\n")
    editor.set_reference(source)
    assert editor.search_box.center == (1, 2, 3)
    with pytest.raises(ValueError, match="does not exist"):
        editor.set_structure(tmp_path / "missing.pdb")
    assert editor.structure_path is None
    assert editor.viewer.scene_data["receptor"] == []


def test_invalid_fit_keeps_canonical_box(editor, tmp_path):
    editor.fit_reference()
    path = tmp_path / "reference.pdb"
    path.touch()
    editor.set_reference(path, coordinates=[(1, 2, 3)])
    before = editor.search_box
    editor.margin_input.setValue(0)
    editor.fit_reference()
    assert editor.search_box == before
    assert editor.validation_message


def test_browse_handles_invalid_reference_without_signal(editor, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: ("missing.pdb", ""))
    signals = []
    editor.reference_selected.connect(signals.append)
    editor._browse_reference()
    assert "does not exist" in editor.validation_message
    assert signals == []


def test_viewer_payload_is_isolated_and_rejects_invalid_updates(editor):
    from vinalab_ui.widgets.box_viewer import box_payload
    copy = editor.viewer.scene_data
    copy["box"]["center"][0] = 888
    assert editor.viewer.scene_data["box"]["center"][0] == 0
    with pytest.raises(ValueError, match="Unknown"):
        editor.viewer.set_coordinates("unknown", [(0, 0, 0)])
    with pytest.raises(ValueError):
        validate_coordinates([None])
    with pytest.raises(ValueError):
        box_payload(SearchBox((float("inf"), 0, 0), (1, 1, 1), "frame", 0, "user"))


def test_clear_reference_discards_cached_fit_without_changing_box(editor, tmp_path):
    path = tmp_path / "molecule.pdb"
    path.touch()
    editor.set_structure(path, coordinates=[(8, 9, 10)])
    editor.set_reference(path, coordinates=[(1, 2, 3)])
    box = editor.search_box
    changes, references = [], []
    editor.search_box_changed.connect(changes.append)
    editor.reference_selected.connect(references.append)
    editor.clear_reference()
    editor.clear_reference()
    editor.fit_reference()
    assert editor.reference_path is None
    assert editor._reference_coordinates is None
    assert not editor.fit_button.isEnabled()
    assert editor.viewer.scene_data["reference"] == []
    assert editor.viewer.scene_data["receptor"] == [[8, 9, 10]]
    assert editor.structure_path == path.resolve()
    assert editor.search_box == box
    assert changes == references == []
    assert editor.viewer._web is None


def test_clear_structure_preserves_reference_and_box(editor, tmp_path):
    path = tmp_path / "molecule.pdb"
    path.touch()
    editor.set_structure(path, coordinates=[(8, 9, 10)])
    editor.set_reference(path, coordinates=[(1, 2, 3)])
    box = editor.search_box
    editor.clear_structure()
    editor.clear_structure()
    assert editor.structure_path is None
    assert editor.viewer.scene_data["receptor"] == []
    assert editor.viewer.scene_data["reference"] == [[1, 2, 3]]
    assert editor.reference_path == path.resolve()
    assert editor.fit_button.isEnabled()
    assert editor.search_box == box


@pytest.mark.parametrize("kind", ["reference", "receptor"])
def test_viewer_empty_layer_requires_explicit_clear(editor, monkeypatch, kind):
    viewer = editor.viewer
    viewer.set_coordinates(kind, [(1, 2, 3)])
    before = viewer.scene_data
    with pytest.raises(ValueError):
        viewer.set_coordinates(kind, [])
    assert viewer.scene_data == before
    published = []
    monkeypatch.setattr(viewer, "_publish", lambda: published.append(viewer.scene_data))
    viewer.clear_coordinates(kind)
    assert published[-1][kind] == []
    assert published[-1]["box"] == before["box"]


@pytest.mark.parametrize("kind", ["box", "unknown", ""])
def test_viewer_rejects_unknown_clear_layer(editor, monkeypatch, kind):
    before = editor.viewer.scene_data
    published = []
    monkeypatch.setattr(editor.viewer, "_publish", lambda: published.append(True))
    with pytest.raises(ValueError, match="Unknown structure layer"):
        editor.viewer.clear_coordinates(kind)
    assert editor.viewer.scene_data == before
    assert published == []
