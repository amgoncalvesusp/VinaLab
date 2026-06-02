# -*- coding: utf-8 -*-
"""Unit tests for heavy-atom RMSD pose clustering."""

import unittest

import numpy as np

from tabs.results_clustering import build_pose_clusters


def _coords(row):
    return np.asarray(row["xyz"], dtype=float)


def _rmsd(a, b):
    if a.shape != b.shape:
        raise ValueError("shape mismatch")
    return float(np.sqrt(np.mean(np.sum((a - b) ** 2, axis=1))))


def _score(row):
    return float(row["affinity"])


class BuildPoseClustersTests(unittest.TestCase):
    """Cover grouping, cutoff behavior, and representative selection."""

    def test_two_close_poses_merge_one_cluster(self) -> None:
        rows = [
            {"ligand_name": "L", "mode": 1, "affinity": -8.0, "xyz": [[0, 0, 0]]},
            {"ligand_name": "L", "mode": 2, "affinity": -7.0, "xyz": [[0.5, 0, 0]]},
        ]
        clusters = build_pose_clusters(rows, _coords, _rmsd, _score, cutoff=2.0)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0]["size"], 2)
        # representative = best (most negative) score
        self.assertEqual(clusters[0]["representative"]["mode"], 1)
        self.assertAlmostEqual(clusters[0]["best_score"], -8.0)

    def test_two_far_poses_split(self) -> None:
        rows = [
            {"ligand_name": "L", "mode": 1, "affinity": -8.0, "xyz": [[0, 0, 0]]},
            {"ligand_name": "L", "mode": 2, "affinity": -7.0, "xyz": [[10, 0, 0]]},
        ]
        clusters = build_pose_clusters(rows, _coords, _rmsd, _score, cutoff=2.0)
        self.assertEqual(len(clusters), 2)

    def test_distinct_ligands_never_share_cluster(self) -> None:
        rows = [
            {"ligand_name": "A", "mode": 1, "affinity": -8.0, "xyz": [[0, 0, 0]]},
            {"ligand_name": "B", "mode": 1, "affinity": -8.0, "xyz": [[0, 0, 0]]},
        ]
        clusters = build_pose_clusters(rows, _coords, _rmsd, _score, cutoff=2.0)
        self.assertEqual({c["ligand"] for c in clusters}, {"A", "B"})

    def test_unreadable_pose_skipped(self) -> None:
        def coords(row):
            if row["mode"] == 2:
                raise RuntimeError("unreadable")
            return np.asarray(row["xyz"], dtype=float)

        rows = [
            {"ligand_name": "L", "mode": 1, "affinity": -8.0, "xyz": [[0, 0, 0]]},
            {"ligand_name": "L", "mode": 2, "affinity": -7.0, "xyz": [[0, 0, 0]]},
        ]
        clusters = build_pose_clusters(rows, coords, _rmsd, _score, cutoff=2.0)
        self.assertEqual(sum(c["size"] for c in clusters), 1)


if __name__ == "__main__":
    unittest.main()
