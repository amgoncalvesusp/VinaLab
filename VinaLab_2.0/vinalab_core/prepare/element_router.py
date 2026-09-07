"""Element-aware routing that preserves exotic atoms such as Boron."""

from __future__ import annotations

from dataclasses import dataclass

EXOTIC_ELEMENTS = frozenset({"B", "Si", "Se", "As", "Te", "Ge", "Sb"})
METALS = frozenset(
    {
        "Mg",
        "Mn",
        "Zn",
        "Ca",
        "Fe",
        "Cu",
        "Ni",
        "Co",
        "Cd",
        "Hg",
        "Pt",
        "Pd",
        "Ru",
        "Au",
        "Ag",
        "Mo",
        "V",
        "Na",
        "K",
        "U",
    }
)
AUTODOCK_TYPE_ELEMENTS = {
    "A": "C",
    "C": "C",
    "N": "N",
    "NA": "N",
    "NS": "N",
    "O": "O",
    "OA": "O",
    "OS": "O",
    "S": "S",
    "SA": "S",
    "P": "P",
    "F": "F",
    "Cl": "Cl",
    "Br": "Br",
    "I": "I",
    "H": "H",
    "HD": "H",
    "HS": "H",
    "Mg": "Mg",
    "Mn": "Mn",
    "Zn": "Zn",
    "Ca": "Ca",
    "Fe": "Fe",
    "Cu": "Cu",
    "Si": "Si",
    "At": "At",
    "Se": "Se",
    "CG0": "C",
    "CG1": "C",
    "CG2": "C",
    "CG3": "C",
    "G0": "Dummy",
    "G1": "Dummy",
    "G2": "Dummy",
    "G3": "Dummy",
    "W": "Dummy",
}

# AutoDock-Vina v1.2.7 src/lib/atom_constants.h; W is a hydrated-ligand dummy, not tungsten.
VINA_ATOM_TYPES = frozenset(AUTODOCK_TYPE_ELEMENTS).difference({"NS", "OS", "HS"}) | frozenset(
    {"Na", "K", "Hg", "Co", "U", "Cd", "Ni"}
)


@dataclass(frozen=True, slots=True)
class ElementRoute:
    elements: frozenset[str]
    exotic_elements: frozenset[str]
    requires_exotic_scoring: bool
    compatible_scorers: tuple[str, ...]


class ElementRouter:
    """Identifies element routes without rewriting or silently deleting atoms."""

    def inspect_pdbqt_text(self, pdbqt: str) -> ElementRoute:
        from vinalab_core.prepare.pdbqt_validator import PdbqtValidator, parse_atom_record

        report = PdbqtValidator().validate_text(pdbqt)
        if not report.ok:
            raise ValueError("; ".join(report.errors))
        elements = frozenset(
            self._element_from_autodock_type(parse_atom_record(line)[2])
            for line in pdbqt.splitlines()
            if line[:6].strip() in {"ATOM", "HETATM"}
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
        if atom_type in EXOTIC_ELEMENTS | METALS:
            return atom_type
        raise ValueError(f"unknown AutoDock atom type: {atom_type}")
