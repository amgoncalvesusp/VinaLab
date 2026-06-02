# -*- coding: utf-8 -*-
"""Symmetry- and order-aware RMSD utilities for docking pose comparison.

Docking validation (redocking success rates, Top-N < 2 Å) and pose clustering
both depend on a correct heavy-atom RMSD.  A naive positional RMSD
(``sqrt(mean(||a_i - b_i||^2))``) is only valid when the two structures list
their atoms in exactly the same order *and* the molecule has no topological
symmetry.  Neither assumption holds when a docked pose is compared against a
crystallographic reference that was prepared by a different tool, nor for
molecules with symmetric groups (phenyl, carboxylate, nitro, equivalent
halogens, ...).  In those cases naive RMSD systematically *overestimates* and
can mislabel a correct pose as a failure.

This module provides:

* ``pose_pair_rmsd`` — direct, order-dependent RMSD.  Correct *only* for poses
  that share an identical atom ordering, e.g. several poses of the same ligand
  emitted by a single Vina run.  Used for pose clustering.
* ``symmetry_corrected_rmsd`` — element-constrained optimal-assignment
  (Hungarian) RMSD that tolerates atom reordering and topological symmetry.
  Used whenever the two structures may not share an atom order, e.g. a docked
  pose versus a crystallographic reference.  It also reports an explicit
  *not comparable* state when the two molecules do not share the same
  heavy-atom element composition, instead of silently returning a sentinel.

Method note for ``symmetry_corrected_rmsd``: atoms are grouped by element and
matched within each element group by minimising the total squared displacement
(``scipy.optimize.linear_sum_assignment``).  This is the standard
assignment-based symmetry correction and is dependency-light and deterministic.
It can, in principle, slightly *underestimate* relative to a full
graph-automorphism RMSD (e.g. ``spyrmsd``) when atoms of the same element sit in
chemically distinct environments; for redocking validation of a pose that is
already close to the reference this is an acceptable and well-bounded
approximation, and a large improvement over order-dependent RMSD.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RmsdResult:
    """Outcome of a symmetry-corrected RMSD comparison.

    ``comparable`` is False when the two structures cannot be meaningfully
    compared (no heavy atoms, or different heavy-atom element composition).  In
    that case ``value`` is ``nan`` and ``reason`` explains why.
    """

    value: float
    comparable: bool
    reason: str = ""


def _heavy_element_from_line(line: str) -> str | None:
    """Return the element symbol for a heavy ATOM/HETATM record, or None for H/invalid."""
    atom_name = line[12:16].strip()
    element = line[76:78].strip() if len(line) >= 78 else ""
    if not element:
        element = "".join(char for char in atom_name if char.isalpha())[:1]
    element = element.strip()
    if not element or element.upper().startswith("H"):
        return None
    return element.upper()


def pdbqt_text_heavy_atoms(text: str) -> list[tuple[str, float, float, float]]:
    """Parse heavy-atom (element, x, y, z) tuples from PDBQT text, preserving order."""
    atoms: list[tuple[str, float, float, float]] = []
    for line in text.splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            continue
        element = _heavy_element_from_line(line)
        if element is None:
            continue
        try:
            x = float(line[30:38])
            y = float(line[38:46])
            z = float(line[46:54])
        except ValueError:
            parts = line.split()
            try:
                x, y, z = float(parts[5]), float(parts[6]), float(parts[7])
            except (IndexError, ValueError):
                continue
        atoms.append((element, x, y, z))
    return atoms


def pdbqt_heavy_coordinates(text: str) -> np.ndarray:
    """Return an (N, 3) array of heavy-atom coordinates in file order."""
    atoms = pdbqt_text_heavy_atoms(text)
    if not atoms:
        return np.empty((0, 3), dtype=float)
    return np.asarray([(x, y, z) for _element, x, y, z in atoms], dtype=float)


def pose_pair_rmsd(
    left_coordinates: np.ndarray, right_coordinates: np.ndarray
) -> float:
    """Direct order-dependent heavy-atom RMSD between two same-ordered poses.

    Raises ValueError when the two coordinate sets cannot be compared
    one-to-one (empty or differing shapes).  Callers that legitimately may hit a
    mismatch must handle the exception rather than receive a misleading number.
    """
    if left_coordinates.shape != right_coordinates.shape:
        raise ValueError(
            f"Conjuntos de coordenadas incompatíveis: {left_coordinates.shape} vs {right_coordinates.shape}."
        )
    if len(left_coordinates) == 0:
        raise ValueError("Conjunto de coordenadas vazio; RMSD indefinido.")
    delta = left_coordinates - right_coordinates
    return float(np.sqrt(np.mean(np.sum(delta * delta, axis=1))))


def symmetry_corrected_rmsd(probe_text: str, reference_text: str) -> RmsdResult:
    """Element-constrained optimal-assignment RMSD between two PDBQT structures.

    Tolerates differing atom order and topological symmetry.  Returns a
    not-comparable result (rather than a sentinel distance) when the two
    structures lack heavy atoms or differ in heavy-atom element composition.
    """
    from scipy.optimize import linear_sum_assignment

    probe = pdbqt_text_heavy_atoms(probe_text)
    reference = pdbqt_text_heavy_atoms(reference_text)
    if not probe or not reference:
        return RmsdResult(
            float("nan"), False, "Sem átomos pesados em uma das estruturas."
        )

    probe_counts = Counter(element for element, *_ in probe)
    reference_counts = Counter(element for element, *_ in reference)
    if probe_counts != reference_counts:
        return RmsdResult(
            float("nan"),
            False,
            "Composição de átomos pesados difere "
            f"(pose {dict(sorted(probe_counts.items()))} vs referência {dict(sorted(reference_counts.items()))}); "
            "não é a mesma molécula ou a preparação removeu/adicionou átomos.",
        )

    total_squared = 0.0
    for element in probe_counts:
        probe_xyz = np.asarray(
            [(x, y, z) for el, x, y, z in probe if el == element], dtype=float
        )
        reference_xyz = np.asarray(
            [(x, y, z) for el, x, y, z in reference if el == element], dtype=float
        )
        cost = np.sum((probe_xyz[:, None, :] - reference_xyz[None, :, :]) ** 2, axis=2)
        rows, cols = linear_sum_assignment(cost)
        total_squared += float(cost[rows, cols].sum())

    rmsd = float(np.sqrt(total_squared / len(probe)))
    return RmsdResult(rmsd, True)
