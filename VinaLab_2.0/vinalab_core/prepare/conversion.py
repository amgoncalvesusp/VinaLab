"""Self-contained RDKit/Meeko ligand and Meeko/OpenBabel receptor preparation."""
from dataclasses import dataclass
from pathlib import Path

from vinalab_core.prepare.molecule import load_molecule, validate_coordinates


@dataclass(frozen=True, slots=True)
class ConversionResult:
    success: bool
    output_path: Path
    log: str = ""
    errors: str = ""


def convert_ligand(input_path, output_path):
    output = Path(output_path)
    try:
        if output.exists():
            raise ValueError("Output already exists; choose a new path")
        from meeko import MoleculePreparation, PDBQTWriterLegacy
        from rdkit import Chem
        from rdkit.Chem import AllChem
        if Path(input_path).resolve() == output.resolve():
            raise ValueError("Input and output must differ")
        mol = load_molecule(input_path)
        if len(Chem.GetMolFrags(mol)) != 1:
            raise ValueError("Disconnected ligand: remove salts or split fragments explicitly")
        mol = Chem.AddHs(mol, addCoords=True)
        generated = not mol.GetNumConformers() or not mol.GetConformer().Is3D()
        if generated:
            params = AllChem.ETKDGv3()
            params.randomSeed = 42
            if AllChem.EmbedMolecule(mol, params) != 0:
                raise ValueError("3D coordinate generation failed")
        validate_coordinates(mol.GetConformer().GetPositions())
        setups = MoleculePreparation().prepare(mol)
        if len(setups) != 1:
            raise ValueError("Ambiguous Meeko preparation: expected one ligand setup")
        text, ok, error = PDBQTWriterLegacy.write_string(setups[0])
        if not ok:
            raise ValueError(error)
        _validate_output(text, ligand=True)
        with output.open("x", encoding="utf-8") as handle:
            handle.write(text)
        note = "Generated 3D coordinates from 2D input" if generated else "Preserved input heavy-atom coordinates"
        return ConversionResult(True, output, f"RDKit + Meeko; Gasteiger charges. {note}. Protonation state follows input; no pH inference.")
    except Exception as exc:  # noqa: BLE001 - Normalize native preparation failures into a result.
        return ConversionResult(False, output, errors=str(exc))


def _validate_output(text, *, ligand):
    import math
    atoms = [line for line in text.splitlines() if line.startswith(("ATOM  ", "HETATM"))]
    validate_coordinates((float(a[30:38]), float(a[38:46]), float(a[46:54])) for a in atoms)
    if any(not math.isfinite(float(a[70:76])) for a in atoms):
        raise ValueError("Nonfinite PDBQT partial charges")
    if ligand and ("ROOT" not in text or "TORSDOF" not in text):
        raise ValueError("Ligand output lacks a torsion tree")
    if not ligand and any(line.startswith(("ROOT", "BRANCH", "TORSDOF")) for line in text.splitlines()):
        raise ValueError("Receptor output is not rigid PDBQT")


def _heavy_positions(text):
    return tuple((float(a[30:38]), float(a[38:46]), float(a[46:54]))
        for a in text.splitlines() if a.startswith(("ATOM  ", "HETATM"))
        and a[76:].strip().split()[0].upper() not in {"H", "HD", "HS"})


def _same_heavy_geometry(original, prepared):
    # Coordinate multisets only verify preservation, never define RMSD atom mappings.
    a, b = sorted(_heavy_positions(original)), sorted(_heavy_positions(prepared))
    if len(a) != len(b) or any(max(abs(x-y) for x, y in zip(p, q)) > .002 for p, q in zip(a, b)):
        raise ValueError("Receptor conversion changed heavy-atom coordinates or atom count")


def _openbabel_receptor(source):
    from openbabel import openbabel as ob
    conversion = ob.OBConversion()
    fmt = source.suffix.lower().lstrip(".")
    if not conversion.SetInAndOutFormats(fmt, "pdbqt"):
        raise ValueError("OpenBabel does not support this receptor format")
    molecule = ob.OBMol()
    if not conversion.ReadFile(molecule, str(source)) or molecule.NumAtoms() == 0:
        raise ValueError("OpenBabel could not read receptor")
    extra = ob.OBMol()
    if conversion.Read(extra):
        raise ValueError("Receptor file contains multiple molecules/models")
    before = tuple((a.GetX(), a.GetY(), a.GetZ()) for a in ob.OBMolAtomIter(molecule) if a.GetAtomicNum() != 1)
    validate_coordinates(before)
    if not molecule.Has3D():
        raise ValueError("Receptor requires prepared 3D coordinates")
    if not molecule.AddHydrogens():
        raise ValueError("OpenBabel could not add receptor hydrogens")
    charges = ob.OBChargeModel.FindType("gasteiger")
    if charges is None or not charges.ComputeCharges(molecule):
        raise ValueError("Gasteiger parameters unavailable for receptor")
    conversion.AddOption("r", ob.OBConversion.OUTOPTIONS)
    text = conversion.WriteString(molecule)
    after = sorted(_heavy_positions(text))
    if len(before) != len(after) or any(max(abs(x-y) for x, y in zip(p, q)) > .002 for p, q in zip(sorted(before), after)):
        raise ValueError("OpenBabel changed receptor heavy-atom coordinates/count")
    return text


def _meeko_receptor(source):
    from meeko import MoleculePreparation, PDBQTWriterLegacy, Polymer, ResidueChemTemplates
    polymer = Polymer.from_pdb_string(source.read_text(), ResidueChemTemplates.create_from_defaults(), MoleculePreparation())
    rigid, flexible = PDBQTWriterLegacy.write_from_polymer(polymer)
    if flexible:
        raise ValueError("Unexpected flexible receptor residues")
    _same_heavy_geometry(source.read_text(), rigid)
    return rigid


def convert_receptor(input_path, output_path):
    source, output = Path(input_path).resolve(), Path(output_path)
    try:
        if output.exists():
            raise ValueError("Output already exists; choose a new path")
        if source == output.resolve():
            raise ValueError("Input and output must differ")
        if source.suffix.lower() not in {".pdb", ".mol2", ".sdf", ".mol"}:
            raise ValueError("Receptor preparation supports PDB, MOL2, SDF, MOL")
        errors = []
        backends = (("Meeko", _meeko_receptor),) if source.suffix.lower() == ".pdb" else ()
        for backend, prepare in (*backends, ("OpenBabel bindings", _openbabel_receptor)):
            try:
                text = prepare(source)
                _validate_output(text, ligand=False)
            except Exception as exc:  # noqa: BLE001 - Isolate backend failures before trying the fallback.
                errors.append(f"{backend}: {exc}")
                continue
            with output.open("x", encoding="utf-8") as handle:
                handle.write(text)
            return ConversionResult(True, output, f"{backend} rigid receptor; heavy coordinates preserved; input protonation, no pH inference.\n" + "\n".join(errors))
        raise ValueError("\n".join(errors))
    except Exception as exc:  # noqa: BLE001 - Normalize native receptor preparation failures.
        return ConversionResult(False, output, errors=str(exc))


class ConversionService:
    @staticmethod
    def convert(input_path, output_path, role="ligand"):
        if role not in {"ligand", "receptor"}:
            raise ValueError("role must be ligand or receptor")
        return (convert_ligand if role == "ligand" else convert_receptor)(input_path, output_path)
