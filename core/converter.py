# -*- coding: utf-8 -*-
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
import logging
import math
from pathlib import Path
import sys

from core.file_utils import validate_ligand_pdbqt

logger = logging.getLogger(__name__)


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
            lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()[
                :40
            ]
        except OSError:
            return "unknown"
        text = "\n".join(lines).lower()
        if "@<tripos>molecule" in text:
            return "mol2"
        if filepath.suffix.lower() in {".sdf", ".mol"} or any(
            marker in text for marker in ("v2000", "v3000", "$$$$", "m  end")
        ):
            return "sdf"
        torsion_markers = {"ROOT", "ENDROOT", "BRANCH", "ENDBRANCH", "TORSDOF"}
        autodock_only_types = {"A", "HD", "HS", "OA", "OS", "NA", "NS", "SA"}
        for line in lines:
            first = line.split(maxsplit=1)[0] if line.split() else ""
            if first in torsion_markers:
                return "pdbqt"
        for line in lines:
            if line.startswith(("ATOM", "HETATM")):
                last_token = line.split()[-1] if line.split() else ""
                # AutoDock-only atom types (HD, OA, NA, ...) never appear as PDB element symbols.
                if last_token in autodock_only_types:
                    return "pdbqt"
                # PDBQT carries a partial charge in the fixed-width columns 67-76;
                # a plain PDB record leaves that column blank (element sits in 77-78).
                charge_field = line[66:76].strip()
                if charge_field and _is_float(charge_field):
                    return "pdbqt"
                return "pdb"
        return "unknown"

    @staticmethod
    def convert_pdb_to_pdbqt_ligand(
        input_path: Path, output_path: Path
    ) -> ConversionResult:
        """Convert a ligand PDB file to PDBQT exclusively via RDKit + Meeko."""
        return FileConverter._convert_ligand_rdkit_meeko(input_path, output_path, "pdb")

    @staticmethod
    def convert_mol2_to_pdbqt_ligand(
        input_path: Path, output_path: Path
    ) -> ConversionResult:
        """Convert a ligand MOL2 file to PDBQT exclusively via RDKit + Meeko."""
        return FileConverter._convert_ligand_rdkit_meeko(
            input_path, output_path, "mol2"
        )

    @staticmethod
    def _convert_ligand_rdkit_meeko(
        input_path: Path, output_path: Path, input_format: str
    ) -> ConversionResult:
        """RDKit-loads, embeds (if needed), Gasteiger-charges, and Meeko-writes a ligand PDBQT."""
        try:
            from rdkit import Chem
            from rdkit.Chem import AllChem
            from meeko import MoleculePreparation, PDBQTWriterLegacy
        except ImportError as exc:
            return ConversionResult(
                False, output_path, "", f"RDKit ou Meeko indisponíveis: {exc}"
            )

        try:
            if input_format == "mol2":
                mol = Chem.MolFromMol2File(str(input_path), removeHs=False)
                if mol is None:
                    mol = FileConverter._mol2_fallback_via_molblock(input_path)
                if mol is None:
                    raise ValueError(
                        "Não foi possível interpretar o arquivo MOL2. Verifique se o arquivo "
                        "está bem formado ou converta para SDF/PDB antes de continuar."
                    )
            elif input_format == "sdf":
                supplier = Chem.SDMolSupplier(str(input_path), removeHs=False)
                mol = next((m for m in supplier if m is not None), None)
            else:
                mol = Chem.MolFromPDBFile(str(input_path), removeHs=False)
            if mol is None:
                raise ValueError(
                    f"RDKit não conseguiu interpretar o ligante {input_format.upper()}."
                )

            # Sanitize and Kekulize to preserve aromatic ring geometry
            Chem.SanitizeMol(mol)
            Chem.Kekulize(mol, clearAromaticFlags=False)

            # Add explicit hydrogens (many PDB files omit them)
            mol = Chem.AddHs(mol, addCoords=True)

            if mol.GetNumConformers() == 0:
                params = AllChem.ETKDGv3()
                if AllChem.EmbedMolecule(mol, params) != 0:
                    raise ValueError(
                        "RDKit não conseguiu gerar coordenadas 3D para o ligante."
                    )

            try:
                AllChem.ComputeGasteigerCharges(mol)
            except Exception:  # noqa: BLE001 - retry after sanitization
                Chem.SanitizeMol(mol)
                AllChem.ComputeGasteigerCharges(mol)

            if FileConverter._has_nan_charges(mol):
                Chem.SanitizeMol(mol)
                AllChem.ComputeGasteigerCharges(mol)
                if FileConverter._has_nan_charges(mol):
                    FileConverter._sanitize_nan_charges(mol)

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
        except Exception as exc:  # noqa: BLE001 - RDKit/Meeko failed; try Open Babel fallback
            fallback = FileConverter._convert_ligand_via_obabel(input_path, output_path)
            if fallback.success:
                return fallback
            return ConversionResult(
                False,
                output_path,
                fallback.log,
                f"Erro: não foi possível converter o ligante {input_format.upper()} "
                f"com RDKit/Meeko nem com Open Babel.\nRDKit/Meeko: {exc}\n{fallback.errors}",
            )

    @staticmethod
    def _convert_ligand_via_obabel(
        input_path: Path, output_path: Path
    ) -> ConversionResult:
        """Open Babel ligand fallback: convert MOL2/SDF/PDB straight to PDBQT.

        Open Babel infers the input format from the file extension, adds hydrogens
        and Gasteiger charges, and writes a single-ligand PDBQT. Used when the
        RDKit + Meeko pipeline cannot parse the input (common with some MOL2/SDF
        variants), matching the "go through an intermediate and let the converter
        do it" approach.
        """
        result = FileConverter._convert_via_openbabel(
            input_path,
            output_path,
            receptor=False,
            previous_error="RDKit/Meeko indisponível para o ligante.",
        )
        if not result.success or not output_path.exists():
            return result
        try:
            validate_ligand_pdbqt(output_path)
        except ValueError as exc:
            return ConversionResult(
                False,
                output_path,
                result.log,
                f"Open Babel gerou um PDBQT inválido: {exc}",
            )
        return ConversionResult(
            True,
            output_path,
            (result.log or "") + "\nLigante convertido com Open Babel (fallback).",
            result.errors,
        )

    @staticmethod
    def _mol2_fallback_via_molblock(input_path: Path):
        """Retry MOL2 parsing by stripping MOL2 headers and reading remaining block via RDKit.

        When RDKit's MOL2 parser fails (common with certain Gaussian/Sybyl variants),
        attempt to extract the atom and bond tables and pass them as a synthetic MOL
        block. Returns an RDKit Mol or None.
        """
        try:
            from rdkit import Chem
        except ImportError:
            return None
        try:
            raw = input_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        sections: dict[str, list[str]] = {}
        current: str | None = None
        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("@<TRIPOS>"):
                current = stripped.split("@<TRIPOS>", 1)[1].strip().upper()
                sections[current] = []
                continue
            if current is not None:
                sections[current].append(line)
        atoms = sections.get("ATOM", [])
        bonds = sections.get("BOND", [])
        if not atoms:
            return None
        mol_lines: list[str] = [
            "",
            "  VinaLab MOL2 fallback",
            "",
            f"{len(atoms):>3}{len(bonds):>3}  0  0  0  0  0  0  0  0999 V2000",
        ]
        for atom_line in atoms:
            tokens = atom_line.split()
            if len(tokens) < 6:
                return None
            try:
                x = float(tokens[2])
                y = float(tokens[3])
                z = float(tokens[4])
            except ValueError:
                return None
            symbol = (
                "".join(ch for ch in tokens[5].split(".")[0] if ch.isalpha()) or "C"
            )
            mol_lines.append(
                f"{x:10.4f}{y:10.4f}{z:10.4f} {symbol:<3} 0  0  0  0  0  0  0  0  0  0  0  0"
            )
        for bond_line in bonds:
            tokens = bond_line.split()
            if len(tokens) < 4:
                continue
            try:
                begin = int(tokens[1])
                end = int(tokens[2])
            except ValueError:
                continue
            bond_order_token = tokens[3]
            order_map = {
                "1": 1,
                "2": 2,
                "3": 3,
                "ar": 4,
                "am": 1,
                "du": 1,
                "un": 1,
                "nc": 1,
            }
            order = order_map.get(bond_order_token.lower(), 1)
            mol_lines.append(f"{begin:>3}{end:>3}{order:>3}  0  0  0  0")
        mol_lines.append("M  END")
        mol_block = "\n".join(mol_lines) + "\n"
        return Chem.MolFromMolBlock(mol_block, removeHs=False, sanitize=False)

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
    def _sanitize_nan_charges(mol) -> int:
        """Replace any NaN/inf/missing Gasteiger partial charge with 0.0 in-place.

        RDKit's Gasteiger implementation may leave NaN/inf values in the
        ``_GasteigerCharge`` property for some substructures (unusual
        heteroatoms, charged groups, borderline aromatic systems). Meeko
        then refuses to prepare the molecule with ``non finite charge: nan``.
        Rather than abort the whole conversion, we sanitize the offending
        atoms to 0.0 (neutral) so Meeko can still produce a valid PDBQT.
        Returns the number of atoms that were sanitized.
        """
        sanitized = 0
        for atom in mol.GetAtoms():
            try:
                value = (
                    float(atom.GetProp("_GasteigerCharge"))
                    if atom.HasProp("_GasteigerCharge")
                    else float("nan")
                )
            except ValueError:
                value = float("nan")
            if math.isnan(value) or math.isinf(value):
                atom.SetProp("_GasteigerCharge", "0.0")
                sanitized += 1
        if sanitized:
            logger.warning(
                "Ligante continha %d átomo(s) com carga Gasteiger inválida (NaN/inf). "
                "Substituídos por 0.0 (neutro) para destravar o Meeko.",
                sanitized,
            )
        else:
            logger.info("Cargas Gasteiger validadas; nenhuma sanitização necessária.")
        return sanitized

    @staticmethod
    def convert_pdb_to_pdbqt_receptor(
        input_path: Path, output_path: Path
    ) -> ConversionResult:
        """Convert a receptor PDB to PDBQT with Meeko in-process, OpenBabel fallback."""
        meeko_result = FileConverter._convert_receptor_via_meeko(input_path, output_path)
        if meeko_result is not None and meeko_result.success:
            return meeko_result
        primary_log = (
            meeko_result.errors
            if meeko_result is not None
            else "Meeko (mk_prepare_receptor) indisponível."
        )
        return FileConverter._convert_via_openbabel(
            input_path, output_path, receptor=True, previous_error=primary_log
        )

    @staticmethod
    def _convert_receptor_via_meeko(
        input_path: Path, output_path: Path
    ) -> ConversionResult | None:
        """Prepare a receptor PDBQT in-process via Meeko's CLI entry point.

        Meeko ships ``mk_prepare_receptor`` only as a console-script executable,
        which PyInstaller does not bundle, so the frozen app cannot reach it with
        ``subprocess``/``shutil.which`` (that was the "mk_prepare_receptor.py não
        está disponível" failure). The same code is importable as
        ``meeko.cli.mk_prepare_receptor`` — already collected into the bundle — so
        we run its ``main()`` in-process. Meeko 0.7 arguments: ``--read_pdb`` reads
        a PDB without ProDy, ``-p`` writes the PDBQT (``-o`` is only a basename),
        and ``--allow_bad_res`` drops residues with missing atoms instead of
        aborting. Returns ``None`` when Meeko cannot be imported so the caller
        falls back to Open Babel.
        """
        try:
            from meeko.cli import mk_prepare_receptor as receptor_cli
        except Exception:  # noqa: BLE001 - missing/broken Meeko -> OpenBabel fallback
            return None

        import contextlib
        import io

        argv = [
            "mk_prepare_receptor",
            "--read_pdb",
            str(input_path),
            "-o",
            str(output_path.with_suffix("")),
            "-p",
            str(output_path),
            "--allow_bad_res",
        ]
        captured = io.StringIO()
        saved_argv = sys.argv
        exit_code: int = 0
        try:
            sys.argv = argv
            with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(
                captured
            ):
                try:
                    receptor_cli.main()
                except SystemExit as exit_signal:
                    exit_code = (
                        exit_signal.code
                        if isinstance(exit_signal.code, int)
                        else 0
                    )
        except Exception as exc:  # noqa: BLE001 - report and let caller fall back
            return ConversionResult(
                False,
                output_path,
                captured.getvalue(),
                f"Meeko (mk_prepare_receptor) falhou: {exc}",
            )
        finally:
            sys.argv = saved_argv

        if output_path.exists() and output_path.stat().st_size > 0:
            return ConversionResult(
                True,
                output_path,
                captured.getvalue()
                or "Receptor preparado com Meeko (mk_prepare_receptor, em processo).",
                "",
            )
        return ConversionResult(
            False,
            output_path,
            captured.getvalue(),
            f"Meeko não gerou o PDBQT do receptor (código {exit_code}).",
        )

    @staticmethod
    def convert_mol2_to_pdbqt_receptor(
        input_path: Path, output_path: Path
    ) -> ConversionResult:
        """Convert a receptor MOL2 file to PDBQT with Open Babel (rigid receptor)."""
        return FileConverter._convert_via_openbabel(
            input_path,
            output_path,
            receptor=True,
            previous_error="MOL2 receptor requer Open Babel.",
        )

    @staticmethod
    def auto_convert(input_path: Path, molecule_type: str) -> ConversionResult:
        """Auto-detect input format and convert to PDBQT for ligand or receptor."""
        detected = FileConverter._detect_format(input_path)
        output_path = input_path.with_suffix(".pdbqt")
        if detected == "pdbqt":
            return ConversionResult(
                True,
                input_path,
                "Arquivo já está em PDBQT; conversão não necessária.",
                "",
            )
        if detected == "unknown":
            return ConversionResult(
                False, output_path, "", "Formato de arquivo não reconhecido."
            )
        if molecule_type == "receptor":
            if detected == "pdb":
                return FileConverter.convert_pdb_to_pdbqt_receptor(
                    input_path, output_path
                )
            if detected in {"mol2", "sdf"}:
                return FileConverter.convert_mol2_to_pdbqt_receptor(
                    input_path, output_path
                )
            return ConversionResult(
                False,
                output_path,
                "",
                "A conversão de receptor aceita entrada PDB, MOL2, SDF ou PDBQT.",
            )
        if detected == "pdb":
            return FileConverter.convert_pdb_to_pdbqt_ligand(input_path, output_path)
        if detected == "mol2":
            return FileConverter.convert_mol2_to_pdbqt_ligand(input_path, output_path)
        if detected == "sdf":
            return FileConverter._convert_ligand_rdkit_meeko(
                input_path, output_path, "sdf"
            )
        return ConversionResult(
            False, output_path, "", "Formato de arquivo não reconhecido."
        )

    @staticmethod
    def check_dependencies() -> dict:
        """Return availability of conversion libraries (all used in-process)."""
        meeko_receptor = importlib.util.find_spec("meeko") is not None and (
            importlib.util.find_spec("meeko.cli.mk_prepare_receptor") is not None
        )
        openbabel_available = importlib.util.find_spec("openbabel") is not None
        return {
            "rdkit": importlib.util.find_spec("rdkit") is not None,
            "meeko": importlib.util.find_spec("meeko") is not None,
            "openbabel_py": openbabel_available,
            "obabel_cli": openbabel_available,
            "mk_prepare_receptor": meeko_receptor,
        }

    @staticmethod
    def _obabel_input_format(input_path: Path) -> str:
        """Map a file suffix to an Open Babel input format string."""
        suffix = input_path.suffix.lower().lstrip(".")
        return {
            "pdb": "pdb",
            "ent": "pdb",
            "mol2": "mol2",
            "sdf": "sdf",
            "mol": "mol",
            "pdbqt": "pdbqt",
            "xyz": "xyz",
            "cif": "cif",
            "mmcif": "mmcif",
        }.get(suffix, "pdb")

    @staticmethod
    def _convert_via_openbabel(
        input_path: Path,
        output_path: Path,
        receptor: bool,
        previous_error: str,
    ) -> ConversionResult:
        """Convert to PDBQT in-process with Open Babel's Python API (pybel).

        Using the ``openbabel`` module instead of spawning ``obabel.exe`` removes
        the dependency on a CLI being on PATH (it never is in the frozen app) and
        lets openbabel-wheel self-configure its plugin/data directories on import.
        ``opt={"r": True}`` is Open Babel's receptor mode (the ``-xr`` flag): a
        rigid receptor with no torsion tree. Gasteiger partial charges are written
        by Open Babel's PDBQT writer.
        """
        try:
            from openbabel import pybel
        except Exception as exc:  # noqa: BLE001 - no RDKit/Meeko and no Open Babel
            return ConversionResult(
                False,
                output_path,
                "",
                f"{previous_error}\nMeeko+RDKit e OpenBabel não estão disponíveis: {exc}",
            )

        input_format = FileConverter._obabel_input_format(input_path)
        try:
            molecule = next(pybel.readfile(input_format, str(input_path)))
            molecule.OBMol.AddHydrogens()
            options = {"r": True} if receptor else {}
            writer = pybel.Outputfile(
                "pdbqt", str(output_path), overwrite=True, opt=options
            )
            writer.write(molecule)
            writer.close()
        except Exception as exc:  # noqa: BLE001 - surface the underlying Open Babel error
            return ConversionResult(
                False,
                output_path,
                "",
                f"{previous_error}\nOpen Babel falhou: {exc}",
            )

        if output_path.exists() and output_path.stat().st_size > 0:
            descriptor = "Receptor" if receptor else "Ligante"
            return ConversionResult(
                True,
                output_path,
                f"{descriptor} convertido com Open Babel (API em processo).",
                "",
            )
        return ConversionResult(
            False,
            output_path,
            "",
            f"{previous_error}\nOpen Babel não gerou o PDBQT.",
        )

    @staticmethod
    def _validated_ligand_result(
        output_path: Path, log: str, errors: str, reference_mol=None
    ) -> ConversionResult:
        """Return a successful conversion only when the PDBQT is one connected ligand."""
        try:
            validate_ligand_pdbqt(output_path)
            FileConverter._validate_ligand_bond_geometry(output_path, reference_mol)
        except ValueError as exc:
            message = "Erro na conversão do ligante: geometria molecular inválida após conversão."
            return ConversionResult(
                False, output_path, log, f"{errors}\n{message}\n{exc}".strip()
            )
        return ConversionResult(True, output_path, log, errors)

    @staticmethod
    def _rdkit_ligand_mol(input_path: Path, input_format: str):
        """Load a ligand with RDKit while preserving atom order and 3D coordinates."""
        try:
            from rdkit import Chem

            if input_format == "pdb":
                return Chem.MolFromPDBFile(
                    str(input_path), removeHs=False, sanitize=False
                )
            if input_format == "mol2":
                return Chem.MolFromMol2File(
                    str(input_path), removeHs=False, sanitize=False
                )
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
            actual = FileConverter._distance(
                output_atoms[begin]["xyz"], output_atoms[end]["xyz"]
            )
            ideal = FileConverter._rdkit_ideal_bond_length(bond)
            if ideal <= 0:
                continue
            deviation = abs(actual - ideal) / ideal
            if deviation > 0.30:
                failures.append(
                    f"{begin + 1}-{end + 1}: observado={actual:.3f} Å, ideal={ideal:.3f} Å, desvio={deviation:.1%}"
                )
        if failures:
            raise ValueError(
                "Ligações fora da tolerância de 30%: " + "; ".join(failures[:8])
            )

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
            lengths.append(
                FileConverter._distance(
                    (begin.x, begin.y, begin.z), (end.x, end.y, end.z)
                )
            )
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
            FileConverter._distance(
                atoms[bond.GetBeginAtomIdx()]["xyz"], atoms[bond.GetEndAtomIdx()]["xyz"]
            )
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
        base = periodic_table.GetRcovalent(
            left.GetAtomicNum()
        ) + periodic_table.GetRcovalent(right.GetAtomicNum())
        order_scale = {
            Chem.BondType.SINGLE: 1.00,
            Chem.BondType.AROMATIC: 0.93,
            Chem.BondType.DOUBLE: 0.87,
            Chem.BondType.TRIPLE: 0.78,
        }.get(bond.GetBondType(), 1.00)
        return base * order_scale

    @staticmethod
    def _distance(
        left: tuple[float, float, float], right: tuple[float, float, float]
    ) -> float:
        """Return Euclidean distance between two 3D points."""
        return math.sqrt(
            (left[0] - right[0]) ** 2
            + (left[1] - right[1]) ** 2
            + (left[2] - right[2]) ** 2
        )


def _is_float(value: str) -> bool:
    """Return True if value can be parsed as float."""
    try:
        float(value)
    except ValueError:
        return False
    return True
