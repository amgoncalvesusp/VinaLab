# -*- coding: utf-8 -*-
"""Unit tests for PDBQT charge parsing and molecular format detection."""

from pathlib import Path
import tempfile
import unittest

from core.converter import FileConverter
from core.file_utils import _pdbqt_charge_value, validate_pdbqt_charges


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


if __name__ == "__main__":
    unittest.main()
