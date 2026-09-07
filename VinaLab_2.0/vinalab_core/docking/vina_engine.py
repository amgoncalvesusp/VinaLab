"""Safe AutoDock Vina command construction."""

from __future__ import annotations

from math import isfinite
from pathlib import Path

from vinalab_core.docking.search_box import SearchBox


class VinaCommandBuilder:
    """Constructs argument lists without a shell from canonical run settings."""

    def __init__(self, executable: str | Path) -> None:
        self.executable = Path(executable)

    def build(
        self,
        *,
        receptor: str | Path,
        ligand: str | Path,
        output: str | Path,
        search_box: SearchBox,
        cpu_threads: int,
        exhaustiveness: int,
        seed: int,
        scoring: str = "vina",
        num_modes: int = 9,
        energy_range: float = 3.0,
    ) -> list[str]:
        if any(type(value) is not int for value in (cpu_threads, exhaustiveness, seed, num_modes)):
            raise ValueError("cpu_threads, exhaustiveness, seed and num_modes must be integers")
        if scoring not in {"vina", "vinardo"}:
            raise ValueError("scoring must be vina or vinardo")
        if num_modes < 1:
            raise ValueError("num_modes must be at least one")
        if not isfinite(energy_range) or energy_range < 0:
            raise ValueError("energy_range must be finite and nonnegative")
        if cpu_threads < 1:
            raise ValueError("cpu_threads must be at least one")
        if exhaustiveness < 1:
            raise ValueError("exhaustiveness must be at least one")
        center = search_box.center
        size = search_box.size
        return [
            str(self.executable),
            "--receptor",
            str(receptor),
            "--ligand",
            str(ligand),
            "--out",
            str(output),
            "--center_x",
            _format_number(center[0]),
            "--center_y",
            _format_number(center[1]),
            "--center_z",
            _format_number(center[2]),
            "--size_x",
            _format_number(size[0]),
            "--size_y",
            _format_number(size[1]),
            "--size_z",
            _format_number(size[2]),
            "--cpu",
            str(cpu_threads),
            "--exhaustiveness",
            str(exhaustiveness),
            "--seed",
            str(seed),
            "--scoring",
            scoring,
            "--num_modes",
            str(num_modes),
            "--energy_range",
            _format_number(energy_range),
        ]


def _format_number(value: float) -> str:
    return format(value, ".12g")
