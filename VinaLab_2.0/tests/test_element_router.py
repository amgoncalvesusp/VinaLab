from __future__ import annotations

import importlib


def _router_type():
    try:
        module = importlib.import_module("vinalab_core.prepare.element_router")
    except ModuleNotFoundError:
        return None
    return getattr(module, "ElementRouter", None)


def test_element_router_is_available_for_exotic_ligand_detection() -> None:
    assert _router_type() is not None


def test_element_router_flags_boron_and_disables_autodock_scoring() -> None:
    router_type = _router_type()
    assert router_type is not None
    pdbqt = """
ATOM      1  B1  LIG     1       0.000   0.000   0.000  0.00  0.00     0.000 B
ATOM      2  O1  LIG     1       1.000   0.000   0.000  0.00  0.00    -0.500 OA
"""

    route = router_type().inspect_pdbqt_text(pdbqt)

    assert route.elements == frozenset({"B", "O"})
    assert route.exotic_elements == frozenset({"B"})
    assert route.requires_exotic_scoring
    assert "vina" not in route.compatible_scorers
    assert "xtb_gfn2" in route.compatible_scorers
