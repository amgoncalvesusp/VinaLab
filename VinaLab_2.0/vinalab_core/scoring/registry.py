"""Registry for transparent scoring availability and element compatibility."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vinalab_core.prepare.element_router import AUTODOCK_TYPE_ELEMENTS, VINA_ATOM_TYPES
from vinalab_core.tools.tool_locator import ToolLocator


@dataclass(frozen=True, slots=True)
class ScorerOption:
    key: str
    label: str
    compatible: bool
    available: bool
    reason: str = ""


@dataclass(frozen=True, slots=True)
class ScoringPlan:
    recommended_key: str
    options: tuple[ScorerOption, ...]

    def option(self, key: str) -> ScorerOption:
        for option in self.options:
            if option.key == key:
                return option
        raise KeyError(key)


class ScoringRegistry:
    """Selects scorers conservatively and makes missing dependencies visible."""

    def __init__(self, project_root: str | Path) -> None:
        self.locator = ToolLocator(project_root)

    def plan_for_elements(self, elements: frozenset[str]) -> ScoringPlan:
        supported = frozenset(AUTODOCK_TYPE_ELEMENTS.get(atom_type, atom_type) for atom_type in VINA_ATOM_TYPES)
        unsupported = elements.difference(supported)
        vina_available = self.locator.find("vina") is not None
        vina_reason = "" if vina_available else "Vina binary is not configured"
        xtb_available = self.locator.find("xtb") is not None
        xtb_reason = "" if xtb_available else "xTB binary is not configured"
        if unsupported:
            return ScoringPlan(
                recommended_key="xtb_gfn2",
                options=(
                    ScorerOption(
                        "vina",
                        "AutoDock Vina",
                        compatible=False,
                        available=vina_available,
                        reason=f"Unsupported Vina elements: {', '.join(sorted(unsupported))}",
                    ),
                    ScorerOption("vinardo", "Vinardo", False, vina_available,
                        f"Unsupported Vina elements: {', '.join(sorted(unsupported))}"),
                    ScorerOption("xtb_gfn2", "xTB GFN2 + ALPB water frozen interaction energy", True, xtb_available, xtb_reason),
                    ScorerOption("xtb_gfnff", "xTB GFN-FF + ALPB water frozen interaction energy", True, xtb_available, xtb_reason),
                    ScorerOption("pm6_sqm", "PM6/SQM2.20", True, False, "MOPAC/Cuby plugin is not configured"),
                    ScorerOption("uff_ie", "RDKit UFF interaction energy", True, False, "Validated topology-aware UFF interaction implementation unavailable"),
                ),
            )
        return ScoringPlan(
            recommended_key="vina",
            options=(
                ScorerOption("vina", "AutoDock Vina", True, vina_available, vina_reason),
                ScorerOption("vinardo", "Vinardo", True, vina_available, vina_reason),
                ScorerOption("xtb_gfn2", "xTB GFN2 + ALPB water frozen interaction energy", True, xtb_available, xtb_reason),
                ScorerOption("xtb_gfnff", "xTB GFN-FF + ALPB water frozen interaction energy", True, xtb_available, xtb_reason),
                ScorerOption("uff_ie", "RDKit UFF interaction energy", True, False, "Validated topology-aware UFF interaction implementation unavailable"),
            ),
        )
