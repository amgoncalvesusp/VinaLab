# -*- coding: utf-8 -*-
"""Heavy-atom RMSD pose clustering, independent of any Qt widget.

Extracted from ResultsTab so the clustering math can be unit-tested without a
GUI. The function is parameterised by callbacks for coordinate extraction, RMSD,
and docking score, so it has no dependency on result-row internals beyond the
``ligand_name`` grouping key.
"""

from __future__ import annotations

from collections.abc import Callable
import logging

logger = logging.getLogger(__name__)


def build_pose_clusters(
    results: list[dict],
    coords_fn: Callable[[dict], object],
    rmsd_fn: Callable[[object, object], float],
    score_fn: Callable[[dict], float],
    cutoff: float,
) -> list[dict]:
    """Cluster poses of each ligand by heavy-atom RMSD (average linkage).

    ``coords_fn(row)`` returns an (N, 3) heavy-atom coordinate array and may
    raise if a pose is unreadable; such poses are skipped and logged.
    ``rmsd_fn(a, b)`` returns the RMSD between two coordinate arrays and may
    raise ValueError when undefined (handled with a large fallback distance).
    Raises ImportError when SciPy is unavailable, so the caller can render a
    degraded message instead of crashing.
    """
    import numpy as np
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform

    clusters: list[dict] = []
    grouped_rows: dict[str, list[dict]] = {}
    for row in results:
        grouped_rows.setdefault(str(row.get("ligand_name", "")), []).append(row)

    for ligand_name, rows in sorted(grouped_rows.items()):
        prepared: list[tuple[dict, object]] = []
        for row in rows:
            try:
                coordinates = coords_fn(row)
            except Exception as exc:  # noqa: BLE001 - skip unreadable pose but record why
                logger.warning(
                    "Pose %s do ligante %s ignorada no agrupamento: %s",
                    row.get("mode"),
                    ligand_name,
                    exc,
                )
                continue
            if len(coordinates) > 0:
                prepared.append((row, coordinates))
        if not prepared:
            continue
        labels = [1]
        if len(prepared) > 1:
            distance_matrix = np.zeros((len(prepared), len(prepared)), dtype=float)
            for left_index, (_left_row, left_coordinates) in enumerate(prepared):
                for right_index in range(left_index + 1, len(prepared)):
                    right_coordinates = prepared[right_index][1]
                    try:
                        rmsd = rmsd_fn(left_coordinates, right_coordinates)
                    except ValueError as exc:
                        logger.warning(
                            "RMSD entre poses %d e %d do ligante %s indefinido (%s); "
                            "usando distância grande no agrupamento.",
                            left_index,
                            right_index,
                            ligand_name,
                            exc,
                        )
                        rmsd = float(max(cutoff * 10.0, 1000.0))
                    distance_matrix[left_index, right_index] = rmsd
                    distance_matrix[right_index, left_index] = rmsd
            condensed = squareform(distance_matrix, checks=False)
            labels = list(
                fcluster(
                    linkage(condensed, method="average"),
                    t=cutoff,
                    criterion="distance",
                )
            )

        cluster_rows: dict[int, list[dict]] = {}
        for label, (row, _coordinates) in zip(labels, prepared, strict=False):
            cluster_rows.setdefault(int(label), []).append(row)
        for cluster_id, members in sorted(cluster_rows.items()):
            representative = min(members, key=score_fn)
            clusters.append(
                {
                    "ligand": ligand_name,
                    "cluster_id": cluster_id,
                    "size": len(members),
                    "best_score": score_fn(representative),
                    "representative": representative,
                    "members": members,
                }
            )
    return clusters
