from __future__ import annotations

import importlib

import pytest


def _search_box_type():
    try:
        module = importlib.import_module("vinalab_core.docking.search_box")
    except ModuleNotFoundError:
        return None
    return getattr(module, "SearchBox", None)


def test_search_box_is_available_as_the_single_geometry_model() -> None:
    assert _search_box_type() is not None


def test_search_box_derives_minimum_and_maximum_from_center_and_size() -> None:
    search_box_type = _search_box_type()
    assert search_box_type is not None

    search_box = search_box_type(
        center=(10.0, 20.0, 30.0),
        size=(8.0, 6.0, 4.0),
        coordinate_frame="prepared-receptor-v1",
        margin=4.0,
        source="user",
    )

    assert search_box.minimum == (6.0, 17.0, 28.0)
    assert search_box.maximum == (14.0, 23.0, 32.0)


def test_search_box_rejects_non_positive_dimensions() -> None:
    search_box_type = _search_box_type()
    assert search_box_type is not None

    with pytest.raises(ValueError, match="size"):
        search_box_type(
            center=(0.0, 0.0, 0.0),
            size=(10.0, 0.0, 10.0),
            coordinate_frame="prepared-receptor-v1",
            margin=4.0,
            source="user",
        )


def test_search_box_fits_reference_coordinates_by_bounding_box_with_margin() -> None:
    search_box_type = _search_box_type()
    assert search_box_type is not None

    search_box = search_box_type.fit_to_coordinates(
        coordinates=[(2.0, 10.0, -1.0), (8.0, 14.0, 3.0), (5.0, 11.0, 2.0)],
        coordinate_frame="prepared-receptor-v1",
        margin=4.0,
        source="reference_ligand",
    )

    assert search_box.center == (5.0, 12.0, 1.0)
    assert search_box.size == (14.0, 12.0, 12.0)
    assert search_box.minimum == (-2.0, 6.0, -5.0)
    assert search_box.maximum == (12.0, 18.0, 7.0)


def test_search_box_reports_coordinates_outside_the_current_box() -> None:
    search_box_type = _search_box_type()
    assert search_box_type is not None
    search_box = search_box_type(
        center=(0.0, 0.0, 0.0),
        size=(10.0, 10.0, 10.0),
        coordinate_frame="prepared-receptor-v1",
        margin=0.0,
        source="user",
    )

    result = search_box.validate_coordinates([("B12", (5.1, 0.0, 0.0))])

    assert not result.ok
    assert result.violations[0].atom_label == "B12"
    assert result.violations[0].axis == "x"
    assert result.violations[0].maximum == 5.0


def test_search_box_center_change_preserves_size_and_changes_bounds() -> None:
    search_box_type = _search_box_type()
    assert search_box_type is not None
    initial = search_box_type(
        center=(0.0, 0.0, 0.0),
        size=(10.0, 10.0, 10.0),
        coordinate_frame="prepared-receptor-v1",
        margin=4.0,
        source="reference_ligand",
    )

    moved = initial.with_center((20.0, 30.0, 40.0), source="user")

    assert moved.center == (20.0, 30.0, 40.0)
    assert moved.size == initial.size
    assert moved.minimum == (15.0, 25.0, 35.0)
    assert moved.source == "user"
