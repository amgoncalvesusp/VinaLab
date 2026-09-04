# -*- coding: utf-8 -*-
"""Unit tests for PDBQT charge parsing and molecular format detection."""

from pathlib import Path
import types
import tempfile
import unittest
from unittest import mock

from core.converter import ConversionResult, FileConverter
from tabs.results_view import build_complex_pdb
from core.file_utils import (
    _pdbqt_charge_value,
    hetatm_residue_counts,
    hetatm_residue_lines,
    validate_pdbqt_charges,
)


class ChargeParsingTests(unittest.TestCase):
    """Cover whitespace + fixed-width partial-charge extraction."""

    def test_reads_whitespace_charge_token(self) -> None:
        line = "ATOM      1  N   LIG A   1      11.000  12.000  13.000  1.00  0.00    -0.347 N"
        self.assertAlmostEqual(_pdbqt_charge_value(line), -0.347, places=3)

    def test_missing_charge_returns_none(self) -> None:
        # Header-only record with no numeric charge in either the whitespace
        # token or the fixed-width charge column.
        line = "ATOM      1  CA  ALA A   1"
        self.assertIsNone(_pdbqt_charge_value(line))

    def test_validate_accepts_charged_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ok.pdbqt"
            path.write_text(
                "ATOM      1  N   LIG A   1      11.000  12.000  13.000  1.00  0.00    -0.347 N\n"
                "ATOM      2  C   LIG A   1      12.000  12.000  13.000  1.00  0.00     0.112 C\n",
                encoding="utf-8",
            )
            self.assertTrue(validate_pdbqt_charges(path))

    def test_validate_rejects_uncharged_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.pdbqt"
            path.write_text(
                "ATOM      1  CA  ALA A   1\n",
                encoding="utf-8",
            )
            self.assertFalse(validate_pdbqt_charges(path))


class FormatDetectionTests(unittest.TestCase):
    """Cover pdb / pdbqt / mol2 detection from file contents."""

    def _detect(self, text: str, suffix: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / f"mol{suffix}"
            path.write_text(text, encoding="utf-8")
            return FileConverter._detect_format(path)

    def test_plain_pdb_is_not_misread_as_pdbqt(self) -> None:
        pdb = (
            "ATOM      1  N   ALA A   1      11.104   6.134   7.123  1.00 19.00           N\n"
            "ATOM      2  CA  ALA A   1      12.560   6.321   7.220  1.00 18.00           C\n"
        )
        self.assertEqual(self._detect(pdb, ".pdb"), "pdb")

    def test_pdbqt_with_autodock_type_detected(self) -> None:
        pdbqt = (
            "ROOT\n"
            "ATOM      1  N   LIG A   1      11.000  12.000  13.000  1.00  0.00    -0.347 HD\n"
            "ENDROOT\nTORSDOF 0\n"
        )
        self.assertEqual(self._detect(pdbqt, ".pdbqt"), "pdbqt")

    def test_mol2_detected(self) -> None:
        mol2 = "@<TRIPOS>MOLECULE\nlig\n 1 0\n@<TRIPOS>ATOM\n 1 C 0.0 0.0 0.0 C.3\n"
        self.assertEqual(self._detect(mol2, ".mol2"), "mol2")


class ConversionFallbackTests(unittest.TestCase):
    """Cover conversion behavior that can be tested without real Open Babel."""

    def test_ligand_preparation_keeps_largest_fragment(self) -> None:
        """Salts/counterions should not produce disconnected ligand PDBQT files."""
        try:
            from rdkit import Chem
        except ImportError:
            self.skipTest("RDKit not installed")

        mol = Chem.MolFromSmiles("CCO.[Na+]")
        prepared, note = FileConverter._prepare_ligand_molecule(mol)
        heavy_atomic_numbers = [
            atom.GetAtomicNum() for atom in prepared.GetAtoms() if atom.GetAtomicNum() > 1
        ]

        self.assertNotIn(11, heavy_atomic_numbers)
        self.assertIn("maior fragmento", note)

    def test_openbabel_cli_fallback_writes_ligand_pdbqt(self) -> None:
        """When the Python API fails, conversion should retry through obabel CLI."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "ligand.sdf"
            output_path = tmp_path / "ligand.pdbqt"
            obabel = tmp_path / "obabel.exe"
            input_path.write_text("fake sdf", encoding="utf-8")
            obabel.write_text("", encoding="utf-8")
            commands = []

            def fake_run(command, **_kwargs):
                commands.append(command)
                output = Path(command[command.index("-O") + 1])
                output.write_text(
                    "ROOT\n"
                    "ATOM      1  C   LIG     1       0.000   0.000   0.000  1.00  0.00     0.000 C\n"
                    "ENDROOT\nTORSDOF 0\n",
                    encoding="utf-8",
                )
                return types.SimpleNamespace(returncode=0, stdout="", stderr="")

            with (
                mock.patch(
                    "core.converter.FileConverter._convert_via_openbabel_py_api",
                    return_value=ConversionResult(
                        False, output_path, "", "Open Babel API failed"
                    ),
                ),
                mock.patch("core.converter.find_obabel_executable", return_value=obabel),
                mock.patch("core.converter.subprocess.run", side_effect=fake_run),
            ):
                result = FileConverter._convert_via_openbabel(
                    input_path,
                    output_path,
                    receptor=False,
                    previous_error="primary failed",
                )

        self.assertTrue(result.success)
        self.assertIn("--partialcharge", commands[0])
        self.assertIn("gasteiger", commands[0])
        # Peptide MOL2 files need pH-aware protonation (obabel -p 7.4), not bare -h.
        self.assertIn("-p", commands[0])
        self.assertIn("7.4", commands[0])
        self.assertNotIn("-h", commands[0])

    def test_openbabel_cli_fallback_uses_receptor_flag(self) -> None:
        """Receptor fallback should pass Open Babel's rigid receptor flag."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "receptor.pdb"
            output_path = tmp_path / "receptor.pdbqt"
            obabel = tmp_path / "obabel"
            input_path.write_text("fake pdb", encoding="utf-8")
            obabel.write_text("", encoding="utf-8")
            commands = []

            def fake_run(command, **_kwargs):
                commands.append(command)
                output = Path(command[command.index("-O") + 1])
                output.write_text(
                    "ATOM      1  C   REC     1       0.000   0.000   0.000  1.00  0.00     0.000 C\n",
                    encoding="utf-8",
                )
                return types.SimpleNamespace(returncode=0, stdout="", stderr="")

            with (
                mock.patch(
                    "core.converter.FileConverter._convert_via_openbabel_py_api",
                    return_value=ConversionResult(
                        False, output_path, "", "Open Babel API failed"
                    ),
                ),
                mock.patch("core.converter.find_obabel_executable", return_value=obabel),
                mock.patch("core.converter.subprocess.run", side_effect=fake_run),
            ):
                result = FileConverter._convert_via_openbabel(
                    input_path,
                    output_path,
                    receptor=True,
                    previous_error="primary failed",
                )

        self.assertTrue(result.success)
        self.assertIn("-xr", commands[0])


class HetatmExtractionTests(unittest.TestCase):
    """Cover co-crystal ligand discovery and per-residue extraction from a PDB."""

    PDB_TEXT = chr(10).join(
        [
            "HETATM    1  C1  TWB A 301      10.000  10.000  10.000  1.00  0.00           C",
        "HETATM    2  C2  TWB A 301      11.000  10.000  10.000  1.00  0.00           C",
        "HETATM    3  C1  TWB A 302      20.000  20.000  20.000  1.00  0.00           C",
        "HETATM    4  C1  GOL A 303      30.000  30.000  30.000  1.00  0.00           C",
        "HETATM    5  O   HOH A 401      40.000  40.000  40.000  1.00  0.00           O",
        "ATOM      6  CA  ALA A   1       1.000   1.000   1.000  1.00  0.00           C",
        ]
    )

    def test_counts_ligands_per_residue_and_skips_water(self) -> None:
        counts = hetatm_residue_counts(self.PDB_TEXT)
        self.assertEqual(
            counts,
            {("TWB", "A", "301"): 2, ("TWB", "A", "302"): 1, ("GOL", "A", "303"): 1},
        )

    def test_extracts_only_the_selected_residue_copy(self) -> None:
        lines = hetatm_residue_lines(self.PDB_TEXT, ("TWB", "A", "301"))
        self.assertEqual(len(lines), 2)
        self.assertTrue(all("TWB A 301" in line for line in lines))


class MultiMoleculeNoteTests(unittest.TestCase):
    """A MOL2/SDF library must not be silently truncated to its first molecule."""

    def test_warns_when_mol2_holds_several_molecules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "library.mol2"
            path.write_text(
                "@<TRIPOS>MOLECULE" + chr(10) + "a" + chr(10) + "@<TRIPOS>MOLECULE" + chr(10) + "b" + chr(10),
                encoding="utf-8",
            )
            note = FileConverter._multi_molecule_note(path, "mol2")
        self.assertIn("2", note)

    def test_single_molecule_has_no_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "one.mol2"
            path.write_text("@<TRIPOS>MOLECULE" + chr(10) + "a" + chr(10), encoding="utf-8")
            self.assertEqual(FileConverter._multi_molecule_note(path, "mol2"), "")


class ComplexExportTests(unittest.TestCase):
    """The receptor-pose complex must renumber serials and isolate the ligand."""

    RECEPTOR = (
        "ATOM      1  CA  ALA A   1      10.000  10.000  10.000  1.00  0.00     0.000 C\n"
        "ATOM      2  CB  ALA A   1      11.000  10.000  10.000  1.00  0.00     0.000 C\n"
    )
    POSE = (
        "MODEL 1\nROOT\n"
        "ATOM      1  C1  UNL A   1      20.000  20.000  20.000  1.00  0.00     0.000 C\n"
        "ATOM      2  C2  UNL A   1      21.500  20.000  20.000  1.00  0.00     0.000 C\n"
        "ENDROOT\nENDMDL\n"
    )

    def test_merges_receptor_and_pose_with_unique_serials(self) -> None:
        text = build_complex_pdb(self.RECEPTOR, self.POSE)
        atom_lines = [
            line
            for line in text.splitlines()
            if line.startswith(("ATOM", "HETATM"))
        ]
        serials = [int(line[6:11]) for line in atom_lines]
        self.assertEqual(serials, [1, 2, 3, 4])
        self.assertEqual(len(set(serials)), len(serials))

    def test_pose_is_hetatm_in_its_own_chain(self) -> None:
        text = build_complex_pdb(self.RECEPTOR, self.POSE)
        pose_lines = [line for line in text.splitlines() if line.startswith("HETATM")]
        self.assertEqual(len(pose_lines), 2)
        self.assertTrue(all(line[21] == "Z" for line in pose_lines))
        self.assertIn("TER", text.splitlines())

    def test_conect_records_point_at_renumbered_pose_atoms(self) -> None:
        text = build_complex_pdb(self.RECEPTOR, self.POSE)
        conect = [line for line in text.splitlines() if line.startswith("CONECT")]
        self.assertTrue(conect)
        for line in conect:
            for serial in (int(line[6:11]), int(line[11:16])):
                self.assertGreaterEqual(serial, 3)

    def test_rejects_a_receptor_without_atoms(self) -> None:
        with self.assertRaises(ValueError):
            build_complex_pdb("REMARK no atoms here", self.POSE)


if __name__ == "__main__":
    unittest.main()
