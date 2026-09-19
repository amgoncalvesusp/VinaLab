"""Real format matrix shared by source and frozen release validation."""

from pathlib import Path


def check_conversion_formats(root: Path) -> list[str]:
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from openbabel import pybel
    from core.converter import FileConverter
    from core.conversion_io import validate_prepared_pdbqt

    completed = []
    folder = root / "conversion formats \u00e7 \u03b1"
    folder.mkdir(exist_ok=True)
    for role in ("ligand", "receptor"):
        base = Chem.MolFromSmiles("C[N+](C)(C)CC(=O)[O-]") if role == "ligand" else Chem.MolFromSequence("AG")
        molecule = Chem.AddHs(base)
        if AllChem.EmbedMolecule(molecule, randomSeed=42) != 0:
            raise RuntimeError("Could not embed smoke molecule")
        for fmt in ("pdb", "mol2", "sdf"):
            source = folder / f"{role}_{fmt}.{fmt}"
            pdb = Chem.MolToPDBBlock(Chem.RemoveHs(molecule) if role == "receptor" else molecule)
            if fmt == "pdb":
                # Reproduce both long headers and overflowing occupancy fields.
                data = "REMARK long header\n" * 90 + "\n".join(
                    line[:54] + "  -0.00" + line[60:] if line.startswith(("ATOM  ", "HETATM")) else line
                    for line in pdb.splitlines()
                )
            else:
                obmol = pybel.readstring("pdb" if role == "receptor" else "mol",
                                         pdb if role == "receptor" else Chem.MolToMolBlock(molecule))
                data = obmol.write(fmt)
            source.write_text(data, encoding="utf-8")
            original = source.read_bytes()
            result = FileConverter.auto_convert(source, role)
            if not result.success:
                raise RuntimeError(f"{role}/{fmt}: {result.log}\n{result.errors}")
            validate_prepared_pdbqt(result.output_path, role)
            if source.read_bytes() != original:
                raise RuntimeError("Conversion modified source")
            completed.append(f"{role}/{fmt}/Meeko")
    return completed
