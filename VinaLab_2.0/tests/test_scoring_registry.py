from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def _registry_type():
    try:
        module = importlib.import_module("vinalab_core.scoring.registry")
    except ModuleNotFoundError:
        return None
    return getattr(module, "ScoringRegistry", None)


def test_scoring_registry_is_available_for_element_aware_scoring_plans() -> None:
    assert _registry_type() is not None


def test_scoring_registry_routes_boron_away_from_vina_and_toward_xtb(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("shutil.which", lambda _: None)
    registry_type = _registry_type()
    assert registry_type is not None
    registry = registry_type(tmp_path)

    plan = registry.plan_for_elements(frozenset({"B", "O"}))

    assert plan.recommended_key == "xtb_gfn2"
    assert not plan.option("vina").compatible
    assert plan.option("xtb_gfn2").compatible
    assert not plan.option("xtb_gfn2").available
    assert "xtb" in plan.option("xtb_gfn2").reason.lower()


def test_unimplemented_uff_is_not_available(tmp_path):
    plan = _registry_type()(tmp_path).plan_for_elements(frozenset({"C", "H"}))
    assert not plan.option("uff_ie").available
    assert "interaction energy" in plan.option("xtb_gfn2").label
    assert plan.option("xtb_gfnff").key == "xtb_gfnff"


@pytest.mark.parametrize("element", ["Zn", "Mg", "Na", "K", "Fe", "Si", "Se"])
def test_vina_supported_elements_are_not_blanket_rejected(tmp_path, element):
    registry = _registry_type()(tmp_path)
    plan = registry.plan_for_elements(frozenset({"C", element}))
    assert plan.recommended_key == "vina"
    assert plan.option("vina").compatible
    assert plan.option("vinardo").compatible
    assert not plan.option("uff_ie").available


@pytest.mark.parametrize("available", [False, True])
def test_vinardo_uses_vina_binary_availability(tmp_path, monkeypatch, available):
    registry = _registry_type()(tmp_path)
    monkeypatch.setattr(registry.locator, "find", lambda name: tmp_path / "vina.exe" if name == "vina" and available else None)
    option = registry.plan_for_elements(frozenset({"C"})).option("vinardo")
    assert option.label == "Vinardo"
    assert option.available is available


@pytest.mark.parametrize("element", ["B", "Pt", "Unknown"])
def test_unsupported_elements_reject_both_vina_scorers(tmp_path, element):
    plan = _registry_type()(tmp_path).plan_for_elements(frozenset({element}))
    for key in ("vina", "vinardo"):
        assert not plan.option(key).compatible
        assert element in plan.option(key).reason
