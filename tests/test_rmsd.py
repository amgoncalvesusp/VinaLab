# -*- coding: utf-8 -*-
"""Unit tests for symmetry- and order-aware RMSD utilities."""

import math
import unittest

from core.rmsd import (
    pdbqt_heavy_coordinates,
    pose_pair_rmsd,
    symmetry_corrected_rmsd,
)


def _atom(serial: int, name: str, x: float, y: float, z: float, element: str) -> str:
    """Build a fixed-width PDBQT ATOM line with coordinates at columns 31-54."""
    prefix = f"ATOM  {serial:>5} {name:<4}".ljust(30)
    return f"{prefix}{x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00     0.000 {element}"


def _pdbqt(*atoms: str) -> str:
    """Wrap atom lines in a minimal single-model PDBQT body."""
    return "ROOT\n" + "\n".join(atoms) + "\nENDROOT\nTORSDOF 0\n"


class SymmetryCorrectedRmsdTests(unittest.TestCase):
    """Cover the assignment-based RMSD that tolerates reordering and symmetry."""

    def test_identical_structures_have_zero_rmsd(self) -> None:
        text = _pdbqt(
            _atom(1, "C", 0.0, 0.0, 0.0, "C"),
            _atom(2, "O", 1.5, 0.0, 0.0, "O"),
        )
        result = symmetry_corrected_rmsd(text, text)
        self.assertTrue(result.comparable)
        self.assertAlmostEqual(result.value, 0.0, places=6)

    def test_atom_reordering_does_not_inflate_rmsd(self) -> None:
        """Same molecule, atoms listed in a different order, must give ~0 Å."""
        probe = _pdbqt(
            _atom(1, "C", 0.0, 0.0, 0.0, "C"),
            _atom(2, "O", 1.5, 0.0, 0.0, "O"),
        )
        reference = _pdbqt(
            _atom(1, "O", 1.5, 0.0, 0.0, "O"),
            _atom(2, "C", 0.0, 0.0, 0.0, "C"),
        )
        result = symmetry_corrected_rmsd(probe, reference)
        self.assertTrue(result.comparable)
        self.assertAlmostEqual(result.value, 0.0, places=6)

    def test_symmetry_equivalent_swap_is_corrected(self) -> None:
        """Two equivalent carbons swapped between files should match optimally (0 Å)."""
        probe = _pdbqt(
            _atom(1, "C", 0.0, 0.0, 0.0, "C"),
            _atom(2, "C", 2.0, 0.0, 0.0, "C"),
        )
        reference = _pdbqt(
            _atom(1, "C", 2.0, 0.0, 0.0, "C"),
            _atom(2, "C", 0.0, 0.0, 0.0, "C"),
        )
        result = symmetry_corrected_rmsd(probe, reference)
        self.assertTrue(result.comparable)
        self.assertAlmostEqual(result.value, 0.0, places=6)

    def test_displaced_pose_reports_positive_rmsd(self) -> None:
        probe = _pdbqt(_atom(1, "C", 0.0, 0.0, 0.0, "C"))
        reference = _pdbqt(_atom(1, "C", 3.0, 0.0, 0.0, "C"))
        result = symmetry_corrected_rmsd(probe, reference)
        self.assertTrue(result.comparable)
        self.assertAlmostEqual(result.value, 3.0, places=6)

    def test_different_element_composition_is_not_comparable(self) -> None:
        probe = _pdbqt(
            _atom(1, "C", 0.0, 0.0, 0.0, "C"),
            _atom(2, "O", 1.5, 0.0, 0.0, "O"),
        )
        reference = _pdbqt(
            _atom(1, "C", 0.0, 0.0, 0.0, "C"),
            _atom(2, "N", 1.5, 0.0, 0.0, "N"),
        )
        result = symmetry_corrected_rmsd(probe, reference)
        self.assertFalse(result.comparable)
        self.assertTrue(result.reason)
        self.assertTrue(math.isnan(result.value))

    def test_empty_structure_is_not_comparable(self) -> None:
        result = symmetry_corrected_rmsd(
            "ROOT\nENDROOT\n", _pdbqt(_atom(1, "C", 0, 0, 0, "C"))
        )
        self.assertFalse(result.comparable)

    def test_hydrogens_are_ignored(self) -> None:
        probe = _pdbqt(
            _atom(1, "C", 0.0, 0.0, 0.0, "C"),
            _atom(2, "H", 0.5, 0.5, 0.5, "HD"),
        )
        reference = _pdbqt(_atom(1, "C", 0.0, 0.0, 0.0, "C"))
        result = symmetry_corrected_rmsd(probe, reference)
        self.assertTrue(result.comparable)
        self.assertAlmostEqual(result.value, 0.0, places=6)


class PosePairRmsdTests(unittest.TestCase):
    """Cover the direct order-dependent RMSD used for same-ligand clustering."""

    def test_known_displacement(self) -> None:
        left = pdbqt_heavy_coordinates(_pdbqt(_atom(1, "C", 0.0, 0.0, 0.0, "C")))
        right = pdbqt_heavy_coordinates(_pdbqt(_atom(1, "C", 0.0, 0.0, 2.0, "C")))
        self.assertAlmostEqual(pose_pair_rmsd(left, right), 2.0, places=6)

    def test_shape_mismatch_raises(self) -> None:
        left = pdbqt_heavy_coordinates(
            _pdbqt(_atom(1, "C", 0.0, 0.0, 0.0, "C"), _atom(2, "O", 1.0, 0.0, 0.0, "O"))
        )
        right = pdbqt_heavy_coordinates(_pdbqt(_atom(1, "C", 0.0, 0.0, 0.0, "C")))
        with self.assertRaises(ValueError):
            pose_pair_rmsd(left, right)

    def test_empty_raises(self) -> None:
        empty = pdbqt_heavy_coordinates("ROOT\nENDROOT\n")
        with self.assertRaises(ValueError):
            pose_pair_rmsd(empty, empty)


if __name__ == "__main__":
    unittest.main()
