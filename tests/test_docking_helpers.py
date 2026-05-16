"""Unit tests for docking helper utilities."""

from pathlib import Path
import sys
import tempfile
import types
import unittest

qtcore = types.ModuleType("PySide6.QtCore")


class _DummyQThread:
    pass


class _DummySignal:
    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs


qtcore.QThread = _DummyQThread
qtcore.Signal = _DummySignal
sys.modules.setdefault("PySide6", types.ModuleType("PySide6"))
sys.modules["PySide6.QtCore"] = qtcore

from core.docking_engine import discover_external_scoring_functions, extract_pose_model
from core.file_utils import pdbqt_receptor_atoms, validate_ligand_pdbqt


class DockingHelperTests(unittest.TestCase):
    """Cover helper behavior that does not require heavy docking dependencies."""

    def test_discover_external_scoring_functions_lists_zip_bundles(self) -> None:
        """Scoring discovery should expose the expected pontuacao bundles."""
        labels = {item["label"] for item in discover_external_scoring_functions()}
        self.assertIn("DeltaVinaRF20", labels)
        self.assertIn("DeltaVinaXGB-Light", labels)
        self.assertIn("RTMScore", labels)

    def test_extract_pose_model_returns_requested_block(self) -> None:
        """Only the requested MODEL block should be returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "poses.pdbqt"
            output_file.write_text(
                "\n".join(
                    [
                        "MODEL 1",
                        "REMARK VINA RESULT: -7.1 0.0 0.0",
                        "ENDMDL",
                        "MODEL 2",
                        "REMARK VINA RESULT: -6.5 0.0 0.0",
                        "ENDMDL",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            pose_block = extract_pose_model(output_file, 2)
        self.assertIn("MODEL 2", pose_block)
        self.assertNotIn("MODEL 1", pose_block)

    def test_extract_pose_model_can_strip_model_wrappers_and_null_bytes(self) -> None:
        """Single-pose exports should not carry multi-model wrappers or NUL padding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "poses.pdbqt"
            output_file.write_text(
                "\n".join(
                    [
                        "MODEL 1",
                        "REMARK VINA RESULT: -7.1 0.0 0.0",
                        "ATOM      1  C   UNL     1       1.000   1.000   1.000  1.00  0.00     0.000 C",
                        "\x00\x00",
                        "ENDMDL",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            pose_block = extract_pose_model(output_file, 1, include_model=False)
        self.assertNotIn("MODEL", pose_block)
        self.assertNotIn("ENDMDL", pose_block)
        self.assertNotIn("\x00", pose_block)
        self.assertIn("ATOM", pose_block)

    def test_pdbqt_receptor_atoms_includes_one_letter_residue_code(self) -> None:
        """Receptor atoms should expose residue identity and coordinates for the center picker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_file = Path(tmpdir) / "receptor.pdbqt"
            receptor_file.write_text(
                "ATOM      1  CA  ALA A  42      11.000  12.000  13.000  0.00  0.00      C\n",
                encoding="utf-8",
            )
            atoms = pdbqt_receptor_atoms(receptor_file)
        self.assertEqual(atoms[0]["one_letter"], "A")
        self.assertEqual(atoms[0]["residue_number"], "42")
        self.assertEqual(atoms[0]["atom_name"], "CA")
        self.assertEqual((atoms[0]["x"], atoms[0]["y"], atoms[0]["z"]), (11.0, 12.0, 13.0))

    def test_validate_ligand_pdbqt_rejects_multi_model_input(self) -> None:
        """A Vina output with multiple MODEL blocks must not be reused as one ligand input."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ligand_file = Path(tmpdir) / "multi_pose_ligand.pdbqt"
            ligand_file.write_text(
                "\n".join(
                    [
                        "MODEL 1",
                        "ATOM      1  C   UNL     1       1.000   1.000   1.000  1.00  0.00     0.000 C",
                        "ENDMDL",
                        "MODEL 2",
                        "ATOM      1  C   UNL     1       2.000   2.000   2.000  1.00  0.00     0.000 C",
                        "ENDMDL",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                validate_ligand_pdbqt(ligand_file)

    def test_validate_ligand_pdbqt_rejects_disconnected_components(self) -> None:
        """Disconnected ligand fragments should be blocked before Vina can dock them separately."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ligand_file = Path(tmpdir) / "fragmented_ligand.pdbqt"
            ligand_file.write_text(
                "\n".join(
                    [
                        "ROOT",
                        "ATOM      1  C   UNL     1       1.000   1.000   1.000  1.00  0.00     0.000 C",
                        "ATOM      2  C   UNL     1      20.000  20.000  20.000  1.00  0.00     0.000 C",
                        "ENDROOT",
                        "TORSDOF 0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                validate_ligand_pdbqt(ligand_file)


if __name__ == "__main__":
    unittest.main()
