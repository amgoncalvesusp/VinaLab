"""Registry for transparent scoring availability and element compatibility."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vinalab_core.prepare.element_router import EXOTIC_ELEMENTS, METALS
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
        exotic = elements.intersection(EXOTIC_ELEMENTS | METALS)
        xtb_available = self.locator.find("xtb") is not None
        xtb_reason = "" if xtb_available else "xTB binary is not configured"
        if exotic:
            return ScoringPlan(
                recommended_key="xtb_gfn2",
                options=(
                    ScorerOption(
                        "vina",
                        "AutoDock Vina",
                        compatible=False,
                        available=self.locator.find("vina") is not None,
                        reason=f"Unsupported exotic elements: {', '.join(sorted(exotic))}",
                    ),
                    ScorerOption("xtb_gfn2", "xTB GFN2 + ALPB", True, xtb_available, xtb_reason),
                    ScorerOption("xtb_gfnff", "xTB GFN-FF + ALPB", True, xtb_available, xtb_reason),
                    ScorerOption("pm6_sqm", "PM6/SQM2.20", True, False, "MOPAC/Cuby plugin is not configured"),
                    ScorerOption("uff_ie", "RDKit UFF interaction energy", True, True),
                ),
            )
        return ScoringPlan(
            recommended_key="vina",
            options=(
                ScorerOption("vina", "AutoDock Vina", True, self.locator.find("vina") is not None),
                ScorerOption("vinardo", "Vinardo", True, False, "Vinardo plugin is not configured"),
                ScorerOption("xtb_gfn2", "xTB GFN2 + ALPB", True, xtb_available, xtb_reason),
                ScorerOption("uff_ie", "RDKit UFF interaction energy", True, True),
            ),
        )
