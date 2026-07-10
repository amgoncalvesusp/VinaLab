"""Parsing of AutoDock Vina standard output into typed docking results."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VinaPoseResult:
    mode: int
    affinity: float
    rmsd_lb: float
    rmsd_ub: float


class VinaResultsParser:
    """Reads only the stable numeric mode rows from Vina's standard table."""

    _ROW = re.compile(
        r"^\s*(?P<mode>\d+)\s+(?P<affinity>-?\d+(?:\.\d+)?)\s+"
        r"(?P<rmsd_lb>-?\d+(?:\.\d+)?)\s+(?P<rmsd_ub>-?\d+(?:\.\d+)?)\s*$"
    )

    def parse(self, output: str) -> tuple[VinaPoseResult, ...]:
        poses: list[VinaPoseResult] = []
        for line in output.splitlines():
            match = self._ROW.match(line)
            if match is None:
                continue
            poses.append(
                VinaPoseResult(
                    mode=int(match["mode"]),
                    affinity=float(match["affinity"]),
                    rmsd_lb=float(match["rmsd_lb"]),
                    rmsd_ub=float(match["rmsd_ub"]),
                )
            )
        return tuple(poses)
