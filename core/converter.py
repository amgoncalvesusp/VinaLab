"""Molecular file conversion utilities for AutoDock Vina.

AutoDock Vina 1.2.x accepts only PDBQT files for receptor and ligand inputs.
PDBQT extends PDB records with partial atomic charge (q) and AutoDock atom
type columns. Recommended conversion:
- Receptor: use Meeko/mk_prepare_receptor.py where available; OpenBabel with
  the -xr receptor flag is a fallback for simpler cases.
- Ligand: use Meeko with RDKit where available because torsions and atom
  typing are handled more accurately; OpenBabel is a fallback.
- MOL2 to PDBQT: Meeko through RDKit is preferred; OpenBabel can convert
  directly but may assign atom types differently.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import math
from pathlib import Path
import shutil
import subprocess
import sys

from core.file_utils import validate_ligand_pdbqt

NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0


@dataclass(frozen=True)
class ConversionResult:
    """Result object returned by file conversion operations."""

    success: bool
    output_path: Path
    log: str
    errors: str


class FileConverter:
    """Convert PDB and MOL2 molecular files to PDBQT."""

    @staticmethod
    def _detect_format(filepath: Path) -> str:
        """Detect pdb, mol2, pdbqt, or unknown from file contents."""
        try:
            lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()[:10]
        except OSError:
            return "unknown"
        text = "\n".join(lines).lower()
        if "@<tripos>molecule" in text:
            return "mol2"
        for line in lines:
            if line.startswith(("ATOM", "HETATM")):
                tokens = line.split()
                if len(line) > 79 or (len(tokens) >= 2 and _is_float(tokens[-2]) and tokens[-1].isalpha()):
                    return "pdbqt"
                return "pdb"
        return "unknown"

    @staticmethod
    def convert_pdb_to_pdbqt_ligand(input_path: Path, output_path: Path) -> ConversionResult:
        """Convert a ligand PDB file to PDBQT exclusively via RDKit + Meeko."""
        return FileConverter._convert_ligand_rdkit_meeko(input_path, output_path, "pdb")

    @staticmethod
    def convert_mol2_to_pdbqt_ligand(input_path: Path, output_path: Path) -> ConversionResult:
        """Convert a ligand MOL2 file to PDBQT exclusively via RDKit + Meeko."""
        return FileConverter._convert_ligand_rdkit_meeko(input_path, output_path, "mol2")

    @staticmethod
    def _convert_ligand_rdkit_meeko(input_path: Path, output_path: Path, input_format: str) -> ConversionResult:
        """RDKit-loads, embeds (if needed), Gasteiger-charges, and Meeko-writes a ligand PDBQT."""
        try:
            from rdkit import Chem
            from rdkit.Chem import AllChem
            from meeko import MoleculePreparation, PDBQTWriterLegacy
        except ImportError as exc:
            return ConversionResult(False, output_path, "", f"RDKit ou Meeko indisponíveis: {exc}")

        try:
            if input_format == "mol2":
                mol = Chem.MolFromMol2File(str(input_path), removeHs=False)
            elif input_format == "sdf":
                supplier = Chem.SDMolSupplier(str(input_path), removeHs=False)
                mol = next((m for m in supplier if m is not None), None)
            else:
                mol = Chem.MolFromPDBFile(str(input_path), removeHs=False)
            if mol is None:
                raise ValueError(f"RDKit não conseguiu interpretar o ligante {input_format.upper()}.")

            # Sanitize and Kekulize to preserve aromatic ring geometry
            Chem.SanitizeMol(mol)
            Chem.Kekulize(mol, clearAromaticFlags=False)

            # Add explicit hydrogens (many PDB files omit them)
            mol = Chem.AddHs(mol, addCoords=True)

            if mol.GetNumConformers() == 0:
                params = AllChem.ETKDGv3()
                if AllChem.EmbedMolecule(mol, params) != 0:
                    raise ValueError("RDKit não conseguiu gerar coordenadas 3D para o ligante.")

            try:
                AllChem.ComputeGasteigerCharges(mol)
            except Exception:
                Chem.SanitizeMol(mol)
                AllChem.ComputeGasteigerCharges(mol)

            if FileConverter._has_nan_charges(mol):
                Chem.SanitizeMol(mol)
                AllChem.ComputeGasteigerCharges(mol)
                if FileConverter._has_nan_charges(mol):
                    raise ValueError("Cargas parciais Gasteiger contêm NaN após sanitização do ligante.")

            preparator = MoleculePreparation()
            setups = preparator.prepare(mol)
            if hasattr(preparator, "write_pdbqt_file"):
                preparator.write_pdbqt_file(str(output_path))
            else:
                if not setups:
                    raise ValueError("Meeko não retornou setups para o ligante.")
                pdbqt_text, ok, error_msg = PDBQTWriterLegacy.write_string(setups[0])
                if not ok:
                    raise ValueError(error_msg)
                output_path.write_text(pdbqt_text, encoding="utf-8")

            pre_stats = FileConverter._bond_length_stats(mol)
            post_stats = FileConverter._bond_length_stats_from_pdbqt(output_path, mol)
            log = FileConverter._geometry_log(
                f"Ligante {input_format.upper()} convertido com RDKit + Meeko (cargas Gasteiger).",
                pre_stats,
                post_stats,
            )
            return FileConverter._validated_ligand_result(output_path, log, "", mol)
        except Exception as exc:  # noqa: BLE001 - any failure in the pipeline must surface in pt-BR
            return ConversionResult(
                False,
                output_path,
                "",
                f"Erro: geometria do ligante inválida após conversão. Verifique o arquivo de entrada.\n{exc}",
            )

    @staticmethod
    def _has_nan_charges(mol) -> bool:
        """Return True when any atom carries a NaN Gasteiger partial charge."""
        for atom in mol.GetAtoms():
            if not atom.HasProp("_GasteigerCharge"):
                return True
            try:
                value = float(atom.GetProp("_GasteigerCharge"))
            except ValueError:
                return True
            if math.isnan(value) or math.isinf(value):
                return True
        return False

    @staticmethod
    def convert_pdb_to_pdbqt_receptor(input_path: Path, output_path: Path) -> ConversionResult:
        """Convert a receptor PDB file to PDBQT using mk_prepare_receptor.py, then OpenBabel fallback."""
        if shutil.which("mk_prepare_receptor.py"):
            try:
                result = subprocess.run(
                    ["mk_prepare_receptor.py", "-i", str(input_path), "-o", str(output_path)],
                    capture_output=True,
                    text=True,
                    check=True,
                    creationflags=NO_WINDOW,
                )
                return ConversionResult(True, output_path, result.stdout, result.stderr)
            except subprocess.CalledProcessError as primary_error:
                primary_log = primary_error.stderr or str(primary_error)
            except OSError as primary_error:
                primary_log = str(primary_error)
        else:
            primary_log = "mk_prepare_receptor.py não está disponível."
        return FileConverter._run_openbabel(input_path, output_path, ["-xr"], primary_log)

    @staticmethod
    def auto_convert(input_path: Path, molecule_type: str) -> ConversionResult:
        """Auto-detect input format and convert to PDBQT for ligand or receptor."""
        detected = FileConverter._detect_format(input_path)
        output_path = input_path.with_suffix(".pdbqt")
        if detected == "pdbqt":
            return ConversionResult(True, input_path, "Arquivo já está em PDBQT; conversão não necessária.", "")
        if detected == "unknown":
            return ConversionResult(False, output_path, "", "Formato de arquivo não reconhecido.")
        if molecule_type == "receptor":
            if detected != "pdb":
                return ConversionResult(False, output_path, "", "A conversão de receptor aceita entrada PDB.")
            return FileConverter.convert_pdb_to_pdbqt_receptor(input_path, output_path)
        if detected == "pdb":
            return FileConverter.convert_pdb_to_pdbqt_ligand(input_path, output_path)
        if detected == "mol2":
            return FileConverter.convert_mol2_to_pdbqt_ligand(input_path, output_path)
        return ConversionResult(False, output_path, "", "Formato de arquivo não reconhecido.")

    @staticmethod
    def check_dependencies() -> dict:
        """Return availability of conversion libraries and command-line tools."""
        obabel_name = "obabel.exe" if sys.platform.startswith("win") else "obabel"
        scripts_obabel = Path(sys.executable).resolve().parent / obabel_name
        return {
            "rdkit": importlib.util.find_spec("rdkit") is not None,
            "meeko": importlib.util.find_spec("meeko") is not None,
            "openbabel_py": importlib.util.find_spec("openbabel") is not None,
            "obabel_cli": shutil.which("obabel") is not None or scripts_obabel.exists(),
            "mk_prepare_receptor": shutil.which("mk_prepare_receptor.py") is not None,
        }

    @staticmethod
    def _run_openbabel(input_path: Path, output_path: Path, extra_args: list[str], previous_error: str) -> ConversionResult:
        """Run OpenBabel CLI conversion as a fallback."""
        obabel = shutil.which("obabel")
        if obabel is None:
            candidate = Path(sys.executable).resolve().parent / ("obabel.exe" if sys.platform.startswith("win") else "obabel")
            obabel = str(candidate) if candidate.exists() else None
        if obabel is None:
            return ConversionResult(False, output_path, "", f"{previous_error}\nMeeko+RDKit e OpenBabel não estão disponíveis.")
        try:
            result = subprocess.run(
                [obabel, str(input_path), "-O", str(output_path), *extra_args],
                capture_output=True,
                text=True,
                check=True,
                creationflags=NO_WINDOW,
            )
            return ConversionResult(True, output_path, result.stdout or "Convertido com OpenBabel.", result.stderr)
        except subprocess.CalledProcessError as fallback_error:
            return ConversionResult(False, output_path, fallback_error.stdout or "", f"{previous_error}\n{fallback_error.stderr}")

    @staticmethod
    def _run_meeko_ligand(
        input_path: Path,
        output_path: Path,
        input_format: str,
        previous_error: str,
        reference_mol=None,
        pre_stats: str = "indisponível",
    ) -> ConversionResult:
        """Fallback ligand conversion with Meeko/RDKit when direct Open Babel fails."""
        try:
            from rdkit import Chem
            from meeko import MoleculePreparation, PDBQTWriterLegacy

            mol = reference_mol or (
                Chem.MolFromPDBFile(str(input_path), removeHs=False)
                if input_format == "pdb"
                else Chem.MolFromMol2File(str(input_path), removeHs=False)
            )
            if mol is None:
                raise ValueError(f"RDKit não conseguiu interpretar o ligante {input_format.upper()}.")
            if mol.GetNumConformers() == 0:
                raise ValueError("O ligante não tem coordenadas 3D para preservar.")
            mol_block = Chem.MolToMolBlock(mol)
            pdb_mol = Chem.MolFromMolBlock(mol_block, removeHs=False, sanitize=False)
            if pdb_mol is None:
                raise ValueError("RDKit não conseguiu recriar o bloco molecular do ligante.")
            Chem.rdmolfiles.MolToPDBBlock(pdb_mol)
            preparator = MoleculePreparation()
            setups = preparator.prepare(pdb_mol)
            if hasattr(preparator, "write_pdbqt_file"):
                preparator.write_pdbqt_file(str(output_path))
            else:
                pdbqt_text, ok, error_msg = PDBQTWriterLegacy.write_string(setups[0])
                if not ok:
                    raise ValueError(error_msg)
                output_path.write_text(pdbqt_text, encoding="utf-8")
            return FileConverter._validated_ligand_result(
                output_path,
                FileConverter._geometry_log(
                    f"{previous_error}\nFallback: ligante convertido com Meeko + RDKit.",
                    pre_stats,
                    FileConverter._bond_length_stats_from_pdbqt(output_path, mol),
                ),
                "",
                mol,
            )
        except Exception as exc:  # noqa: BLE001 - all conversion attempts should be reported together
            message = "Erro na conversão do ligante: geometria molecular inválida após conversão."
            return ConversionResult(False, output_path, "", f"{previous_error}\nFallback Meeko + RDKit falhou: {exc}\n{message}".strip())

    @staticmethod
    def _validated_ligand_result(output_path: Path, log: str, errors: str, reference_mol=None) -> ConversionResult:
        """Return a successful conversion only when the PDBQT is one connected ligand."""
        try:
            validate_ligand_pdbqt(output_path)
            FileConverter._validate_ligand_bond_geometry(output_path, reference_mol)
        except ValueError as exc:
            message = "Erro na conversão do ligante: geometria molecular inválida após conversão."
            return ConversionResult(False, output_path, log, f"{errors}\n{message}\n{exc}".strip())
        return ConversionResult(True, output_path, log, errors)

    @staticmethod
    def _rdkit_ligand_mol(input_path: Path, input_format: str):
        """Load a ligand with RDKit while preserving atom order and 3D coordinates."""
        try:
            from rdkit import Chem

            if input_format == "pdb":
                return Chem.MolFromPDBFile(str(input_path), removeHs=False, sanitize=False)
            if input_format == "mol2":
                return Chem.MolFromMol2File(str(input_path), removeHs=False, sanitize=False)
        except Exception:  # noqa: BLE001 - missing/invalid RDKit is handled by validation failure
            return None
        return None

    @staticmethod
    def _validate_ligand_bond_geometry(output_path: Path, reference_mol) -> None:
        """Validate converted PDBQT bond lengths against RDKit bond-type expectations.

        Meeko may add, remove, or reorder hydrogens during preparation, so an
        atom-count mismatch is tolerated.  Bond-length validation only runs when
        the counts match exactly.
        """
        if reference_mol is None or reference_mol.GetNumConformers() == 0:
            return  # skip validation when reference is unavailable
        output_atoms = FileConverter._pdbqt_atoms(output_path)
        if len(output_atoms) != reference_mol.GetNumAtoms():
            return  # Meeko changed hydrogen count — cannot map bonds 1:1
        failures: list[str] = []
        for bond in reference_mol.GetBonds():
            begin = bond.GetBeginAtomIdx()
            end = bond.GetEndAtomIdx()
            if begin >= len(output_atoms) or end >= len(output_atoms):
                continue
            actual = FileConverter._distance(output_atoms[begin]["xyz"], output_atoms[end]["xyz"])
            ideal = FileConverter._rdkit_ideal_bond_length(bond)
            if ideal <= 0:
                continue
            deviation = abs(actual - ideal) / ideal
            if deviation > 0.30:
                failures.append(
                    f"{begin + 1}-{end + 1}: observado={actual:.3f} Å, ideal={ideal:.3f} Å, desvio={deviation:.1%}"
                )
        if failures:
            raise ValueError("Ligações fora da tolerância de 30%: " + "; ".join(failures[:8]))

    @staticmethod
    def _bond_length_stats(mol) -> str:
        """Return concise bond-length stats for debug logging."""
        if mol is None or mol.GetNumConformers() == 0:
            return "indisponível"
        conformer = mol.GetConformer()
        lengths = []
        for bond in mol.GetBonds():
            begin = conformer.GetAtomPosition(bond.GetBeginAtomIdx())
            end = conformer.GetAtomPosition(bond.GetEndAtomIdx())
            lengths.append(FileConverter._distance((begin.x, begin.y, begin.z), (end.x, end.y, end.z)))
        return FileConverter._format_stats(lengths)

    @staticmethod
    def _bond_length_stats_from_pdbqt(path: Path, reference_mol) -> str:
        """Return output bond stats using the reference molecule's bond graph."""
        if reference_mol is None:
            return "indisponível"
        atoms = FileConverter._pdbqt_atoms(path)
        if len(atoms) != reference_mol.GetNumAtoms():
            return f"indisponível (átomos entrada={reference_mol.GetNumAtoms()}, saída={len(atoms)})"
        lengths = [
            FileConverter._distance(atoms[bond.GetBeginAtomIdx()]["xyz"], atoms[bond.GetEndAtomIdx()]["xyz"])
            for bond in reference_mol.GetBonds()
        ]
        return FileConverter._format_stats(lengths)

    @staticmethod
    def _geometry_log(message: str, pre_stats: str, post_stats: str) -> str:
        """Build a debug-console conversion log with pre/post bond length stats."""
        return f"{message}\nEstatísticas de ligações antes da conversão: {pre_stats}\nEstatísticas de ligações após conversão: {post_stats}"

    @staticmethod
    def _format_stats(lengths: list[float]) -> str:
        """Format min/mean/max bond lengths."""
        if not lengths:
            return "sem ligações"
        mean = sum(lengths) / len(lengths)
        return f"n={len(lengths)}, mín={min(lengths):.3f} Å, média={mean:.3f} Å, máx={max(lengths):.3f} Å"

    @staticmethod
    def _pdbqt_atoms(path: Path) -> list[dict]:
        """Parse PDBQT atom coordinates in file order."""
        atoms: list[dict] = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith(("ATOM", "HETATM")):
                continue
            try:
                xyz = (float(line[30:38]), float(line[38:46]), float(line[46:54]))
            except ValueError:
                parts = line.split()
                try:
                    xyz = (float(parts[5]), float(parts[6]), float(parts[7]))
                except (IndexError, ValueError):
                    continue
            atoms.append({"xyz": xyz})
        return atoms

    @staticmethod
    def _rdkit_ideal_bond_length(bond) -> float:
        """Estimate ideal bond length from RDKit atom radii and bond order."""
        from rdkit import Chem

        periodic_table = Chem.GetPeriodicTable()
        left = bond.GetBeginAtom()
        right = bond.GetEndAtom()
        base = periodic_table.GetRcovalent(left.GetAtomicNum()) + periodic_table.GetRcovalent(right.GetAtomicNum())
        order_scale = {
            Chem.BondType.SINGLE: 1.00,
            Chem.BondType.AROMATIC: 0.93,
            Chem.BondType.DOUBLE: 0.87,
            Chem.BondType.TRIPLE: 0.78,
        }.get(bond.GetBondType(), 1.00)
        return base * order_scale

    @staticmethod
    def _distance(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
        """Return Euclidean distance between two 3D points."""
        return math.sqrt((left[0] - right[0]) ** 2 + (left[1] - right[1]) ** 2 + (left[2] - right[2]) ** 2)


def _is_float(value: str) -> bool:
    """Return True if value can be parsed as float."""
    try:
        float(value)
    except ValueError:
        return False
    return True
