"""Automatic preparation retries preserve data and report the engine used."""

import os
from unittest.mock import patch

import pytest
from core.conversion_io import validate_prepared_pdbqt
from core.converter import ConversionResult, FileConverter
from PySide6.QtWidgets import QApplication
from test_conversion_formats import ligand_file
from ui.converter_widget import ConversionWorker, ConverterWidget

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
APP = QApplication.instance() or QApplication([])


@pytest.mark.parametrize("fmt", ["pdb", "mol2", "sdf"])
def test_default_worker_retries_real_openbabel_and_reports_reason(tmp_path, fmt):
    source, molecule = ligand_file(tmp_path, fmt, smiles="CC(=O)NCCO")
    original = source.read_bytes()
    target = tmp_path / "output.pdbqt"
    worker = ConversionWorker([source], target, "ligand")
    results, logs = [], []
    worker.finished_signal.connect(results.extend)
    worker.log_signal.connect(logs.append)
    with patch("meeko.MoleculePreparation.prepare", side_effect=ValueError("unsupported setup")):
        worker.run()
    assert results[0].success, results[0].errors
    validate_prepared_pdbqt(target, "ligand")
    assert "Open Babel" in results[0].log
    assert "unsupported setup" in results[0].log
    assert any("unsupported setup" in line for line in logs)
    assert source.read_bytes() == original
    atoms = FileConverter._pdbqt_atoms(target)
    for atom in molecule.GetAtoms():
        if atom.GetAtomicNum() != 1:
            xyz = tuple(molecule.GetConformer().GetAtomPosition(atom.GetIdx()))
            assert min(FileConverter._distance(xyz, out["xyz"]) for out in atoms) < 0.002


def test_auto_convert_retries_but_explicit_meeko_does_not(tmp_path):
    source, _ = ligand_file(tmp_path, "sdf")
    with patch("meeko.MoleculePreparation.prepare", side_effect=ValueError("unsupported setup")):
        automatic = FileConverter.auto_convert(source, "ligand")
        explicit = ConversionWorker([source], tmp_path / "explicit.pdbqt", "ligand", "meeko")._convert_one(
            source, tmp_path / "explicit.pdbqt")
    assert automatic.success, automatic.errors
    assert not explicit.success
    assert "unsupported setup" in explicit.errors
    assert not (tmp_path / "explicit.pdbqt").exists()


def test_both_engines_fail_preserving_existing_output_and_causes(tmp_path):
    source, _ = ligand_file(tmp_path, "sdf")
    target = source.with_suffix(".pdbqt")
    target.write_text("previous output")
    with patch("meeko.MoleculePreparation.prepare", side_effect=ValueError("meeko cause")), \
         patch.object(FileConverter, "_convert_ligand_via_obabel", return_value=ConversionResult(
             False, target, "", "babel cause")):
        result = FileConverter.auto_convert(source, "ligand")
    assert not result.success
    assert "meeko cause" in result.log + result.errors
    assert "babel cause" in result.log + result.errors
    assert target.read_text() == "previous output"


def test_default_widget_is_automatic_with_explicit_engines():
    widget = ConverterWidget()
    assert widget.backend_combo.currentData() == "auto"
    assert {widget.backend_combo.itemData(i) for i in range(widget.backend_combo.count())} == {
        "auto", "meeko", "openbabel"}
    widget.backend_combo.setCurrentIndex(widget.backend_combo.findData("meeko"))
    widget.retranslate_ui("en")
    assert widget.backend_combo.currentData() == "meeko"
    widget.close()


def test_openbabel_cli_log_retains_primary_failure(tmp_path):
    source, _ = ligand_file(tmp_path, "sdf")
    target = tmp_path / "out.pdbqt"
    with patch.object(FileConverter, "_convert_via_openbabel_py_api", return_value=ConversionResult(
            False, target, "", "API unavailable")):
        result = FileConverter._convert_ligand_via_obabel(source, target)
    assert result.success, result.errors
    assert "API unavailable" in result.log


@pytest.mark.parametrize("backend", ["auto", "meeko", "openbabel"])
def test_engine_dispatch_preserves_input_when_output_is_same_file(tmp_path, backend):
    source, _ = ligand_file(tmp_path, "sdf")
    original = source.read_bytes()
    result = FileConverter.convert_ligand(source, source, "sdf", backend)
    assert not result.success
    assert source.read_bytes() == original


@pytest.mark.parametrize("backend,fmt", [(None, "sdf"), ("typo", "sdf"), ("auto", "xyz")])
def test_invalid_engine_or_format_is_rejected(tmp_path, backend, fmt):
    source, _ = ligand_file(tmp_path, "sdf")
    target = tmp_path / "output.pdbqt"
    result = FileConverter.convert_ligand(source, target, fmt, backend)
    assert not result.success
    assert not target.exists()


def test_atomic_validation_failure_preserves_engine_diagnostic(tmp_path):
    from core.conversion_io import atomic_conversion

    source = tmp_path / "source.pdb"
    source.write_text("original")
    target = tmp_path / "output.pdbqt"
    target.write_text("previous")

    @atomic_conversion("ligand")
    def invalid_engine(input_path, output_path):
        output_path.write_text("ROOT\nENDROOT\nTORSDOF 0\n")
        return ConversionResult(True, output_path, "Open Babel after Meeko failure", "engine warning")

    result = invalid_engine(source, target)
    assert not result.success
    assert "Open Babel after Meeko failure" in result.log
    assert "engine warning" in result.errors
    assert target.read_text() == "previous"


def test_invalid_openbabel_output_does_not_replace_previous_file(tmp_path):
    source, _ = ligand_file(tmp_path, "sdf")
    target = tmp_path / "output.pdbqt"
    target.write_text("previous")

    def invalid_api(input_path, output_path, receptor, previous_error):
        output_path.write_text("ROOT\nENDROOT\nTORSDOF 0\n")
        return ConversionResult(True, output_path, "Open Babel output", "")

    with patch("meeko.MoleculePreparation.prepare", side_effect=ValueError("unsupported setup")), \
         patch.object(FileConverter, "_convert_via_openbabel_py_api", side_effect=invalid_api):
        result = FileConverter.convert_ligand(source, target, "sdf")
    assert not result.success
    assert "unsupported setup" in result.log
    assert target.read_text() == "previous"


def test_successful_meeko_never_calls_fallback(tmp_path):
    source, _ = ligand_file(tmp_path, "sdf")
    with patch.object(FileConverter, "_convert_ligand_via_obabel") as fallback:
        result = FileConverter.convert_ligand(source, source.with_suffix(".pdbqt"), "sdf")
    assert result.success, result.errors
    fallback.assert_not_called()


def test_dispatch_explicit_openbabel_never_calls_meeko(tmp_path):
    source, _ = ligand_file(tmp_path, "sdf")
    with patch.object(FileConverter, "_convert_ligand_rdkit_meeko") as meeko:
        result = FileConverter.convert_ligand(source, source.with_suffix(".pdbqt"), "sdf", "openbabel")
    assert result.success, result.errors
    meeko.assert_not_called()


def test_automatic_fallback_normalizes_shifted_pdb_elements(tmp_path):
    source, _ = ligand_file(tmp_path, "pdb", smiles="CCCl")
    original = "\n".join(line[:54] + "  -0.00" + line[60:] if line.startswith("HETATM") else line
                         for line in source.read_text().splitlines())
    source.write_text(original)
    with patch("meeko.MoleculePreparation.prepare", side_effect=ValueError("unsupported setup")):
        result = FileConverter.auto_convert(source, "ligand")
    assert result.success, result.errors
    types = [line[77:].strip() for line in result.output_path.read_text().splitlines()
             if line.startswith(("ATOM  ", "HETATM"))]
    assert "Cl" in types
    assert source.read_text() == original


@pytest.mark.parametrize("use_cli", [False, True])
def test_fallback_uses_detected_content_for_unknown_suffix(tmp_path, use_cli):
    source, _ = ligand_file(tmp_path, "sdf")
    renamed = source.with_suffix(".data")
    source.rename(renamed)
    with patch("meeko.MoleculePreparation.prepare", side_effect=ValueError("unsupported setup")):
        if use_cli:
            with patch.object(FileConverter, "_convert_via_openbabel_py_api", return_value=ConversionResult(
                    False, tmp_path / "unused", "", "API unavailable")):
                result = FileConverter.auto_convert(renamed, "ligand")
        else:
            result = FileConverter.auto_convert(renamed, "ligand")
    assert result.success, result.errors
    validate_prepared_pdbqt(result.output_path, "ligand")
