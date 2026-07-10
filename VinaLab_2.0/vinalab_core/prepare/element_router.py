"""Element-aware routing that preserves exotic atoms such as Boron."""

from __future__ import annotations

from dataclasses import dataclass


EXOTIC_ELEMENTS = frozenset({"B", "Si", "Se", "As", "Te", "Ge", "Sb"})
METALS = frozenset({"Mg", "Mn", "Zn", "Ca", "Fe", "Cu", "Ni", "Co", "Cd", "Hg", "Pt", "Pd", "Ru", "Au", "Ag", "Mo", "V", "W"})
AUTODOCK_TYPE_ELEMENTS = {
    "A": "C", "C": "C", "N": "N", "NA": "N", "NS": "N", "O": "O", "OA": "O", "OS": "O",
    "S": "S", "SA": "S", "P": "P", "F": "F", "Cl": "Cl", "Br": "Br", "I": "I", "H": "H",
    "HD": "H", "HS": "H", "Mg": "Mg", "Mn": "Mn", "Zn": "Zn", "Ca": "Ca", "Fe": "Fe", "Cu": "Cu",
}


@dataclass(frozen=True, slots=True)
class ElementRoute:
    elements: frozenset[str]
    exotic_elements: frozenset[str]
    requires_exotic_scoring: bool
    compatible_scorers: tuple[str, ...]


class ElementRouter:
    """Identifies element routes without rewriting or silently deleting atoms."""

    def inspect_pdbqt_text(self, pdbqt: str) -> ElementRoute:
        elements = frozenset(
            self._element_from_autodock_type(line.split()[-1])
            for line in pdbqt.splitlines()
            if line.startswith(("ATOM", "HETATM"))
        )
        exotic = elements.intersection(EXOTIC_ELEMENTS | METALS)
        if exotic:
            return ElementRoute(
                elements=elements,
                exotic_elements=frozenset(exotic),
                requires_exotic_scoring=True,
                compatible_scorers=("xtb_gfn2", "xtb_gfnff", "pm6_sqm", "uff_ie"),
            )
        return ElementRoute(
            elements=elements,
            exotic_elements=frozenset(),
            requires_exotic_scoring=False,
            compatible_scorers=("vina", "vinardo", "smina", "xtb_gfn2", "uff_ie"),
        )

    @staticmethod
    def _element_from_autodock_type(atom_type: str) -> str:
        if atom_type in AUTODOCK_TYPE_ELEMENTS:
            return AUTODOCK_TYPE_ELEMENTS[atom_type]
        if len(atom_type) >= 2 and atom_type[:2] in EXOTIC_ELEMENTS | METALS:
            return atom_type[:2]
        return atom_type[:1]
