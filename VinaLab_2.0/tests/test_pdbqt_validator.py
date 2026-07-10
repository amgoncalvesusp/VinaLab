from __future__ import annotations

import importlib


def _validator_type():
    try:
        module = importlib.import_module("vinalab_core.prepare.pdbqt_validator")
    except ModuleNotFoundError:
        return None
    return getattr(module, "PdbqtValidator", None)


def test_pdbqt_validator_is_available_for_docking_inputs() -> None:
    assert _validator_type() is not None


def test_pdbqt_validator_accepts_atom_records_with_coordinates_and_atom_type() -> None:
    validator_type = _validator_type()
    assert validator_type is not None
    pdbqt = "ATOM      1  C1  LIG     1       1.000   2.000   3.000  0.00  0.00     0.100 C\n"

    report = validator_type().validate_text(pdbqt)

    assert report.ok
    assert report.atom_count == 1
    assert report.errors == ()


def test_pdbqt_validator_explains_when_no_atom_records_exist() -> None:
    validator_type = _validator_type()
    assert validator_type is not None

    report = validator_type().validate_text("REMARK no atoms\n")

    assert not report.ok
    assert "ATOM" in report.errors[0]
