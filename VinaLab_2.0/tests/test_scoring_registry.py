from __future__ import annotations

import importlib
from pathlib import Path


def _registry_type():
    try:
        module = importlib.import_module("vinalab_core.scoring.registry")
    except ModuleNotFoundError:
        return None
    return getattr(module, "ScoringRegistry", None)


def test_scoring_registry_is_available_for_element_aware_scoring_plans() -> None:
    assert _registry_type() is not None


def test_scoring_registry_routes_boron_away_from_vina_and_toward_xtb(tmp_path: Path) -> None:
    registry_type = _registry_type()
    assert registry_type is not None
    registry = registry_type(tmp_path)

    plan = registry.plan_for_elements(frozenset({"B", "O"}))

    assert plan.recommended_key == "xtb_gfn2"
    assert not plan.option("vina").compatible
    assert plan.option("xtb_gfn2").compatible
    assert not plan.option("xtb_gfn2").available
    assert "xtb" in plan.option("xtb_gfn2").reason.lower()
