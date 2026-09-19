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
import subprocess
import sys
from threading import Lock

from core.file_utils import validate_ligand_pdbqt
from core.conversion_io import atomic_conversion, validate_prepared_pdbqt
from core.native_tools import find_obabel_executable, native_tool_env

logger = logging.getLogger(__name__)
_RECEPTOR_CLI_LOCK = Lock()
NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
# Physiological pH used when Open Babel protonates a ligand (obabel -p 7.4).
LIGAND_PROTONATION_PH = 7.4


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
            lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
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
                charge_field = line[70:76].strip()
                if filepath.suffix.lower() == ".pdbqt" or (charge_field and _is_float(charge_field)):
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
    @atomic_conversion("ligand")
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

        multi_note = FileConverter._multi_molecule_note(input_path, input_format)

        try:
            source_text = input_path.read_text(encoding="utf-8-sig")
            if input_format == "mol2":
                mol = Chem.MolFromMol2Block(source_text, removeHs=False)
                if mol is None:
                    mol = FileConverter._mol2_fallback_via_molblock(input_path)
                if mol is None:
                    raise ValueError(
                        "Não foi possível interpretar o arquivo MOL2. Verifique se o arquivo "
                        "está bem formado ou converta para SDF/PDB antes de continuar."
                    )
            elif input_format == "sdf":
                supplier = Chem.SDMolSupplier()
                supplier.SetData(source_text, removeHs=False)
                mol = next(iter(supplier), None)
            else:
                from core.receptor_input import normalize_receptor_pdb
                pdb_text, _ = normalize_receptor_pdb(source_text)
                mol = Chem.MolFromPDBBlock(pdb_text, removeHs=False)
            if mol is None:
                raise ValueError(
                    f"RDKit não conseguiu interpretar o ligante {input_format.upper()}."
                )

            mol, preparation_note = FileConverter._prepare_ligand_molecule(mol)

            try:
                AllChem.ComputeGasteigerCharges(mol)
            except Exception:  # noqa: BLE001 - retry after sanitization
                Chem.SanitizeMol(mol)
                AllChem.ComputeGasteigerCharges(mol)

            if FileConverter._has_nan_charges(mol):
                Chem.SanitizeMol(mol)
                AllChem.ComputeGasteigerCharges(mol)
                if FileConverter._has_nan_charges(mol):
                    raise ValueError("Não foi possível calcular cargas Gasteiger finitas; revise a química do ligante.")

            preparator = MoleculePreparation()
            setups = preparator.prepare(mol)
            FileConverter._remove_stale_output(output_path)
            if not setups:
                raise ValueError("Meeko não retornou setups para o ligante.")
            pdbqt_text, ok, error_msg = PDBQTWriterLegacy.write_string(setups[0], add_index_map=True)
            if not ok:
                raise ValueError(error_msg)
            output_path.write_text(pdbqt_text, encoding="utf-8")

            pre_stats = FileConverter._bond_length_stats(mol)
            post_stats = "coordenadas dos átomos pesados verificadas pelo mapa de átomos Meeko"
            message = (
                f"Ligante {input_format.upper()} convertido com RDKit + Meeko "
                "(cargas Gasteiger)."
            )
            if preparation_note:
                message = f"{message}\n{preparation_note}"
            if multi_note:
                message = f"{message}\n{multi_note}"
            log = FileConverter._geometry_log(
                message,
                pre_stats,
                post_stats,
            )
            return FileConverter._validated_ligand_result(output_path, log, "", mol)
        except Exception as exc:  # noqa: BLE001 - preserve the selected preparation engine
            return ConversionResult(
                False,
                output_path,
                multi_note,
                f"Erro: não foi possível converter o ligante {input_format.upper()} "
                f"com RDKit/Meeko: {exc}\nRevise a estrutura ou selecione Open Babel explicitamente.",
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
            previous_error="Preparação alternativa com Open Babel.",
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
            (result.log or "") + "\nLigante convertido com Open Babel.",
            result.errors,
        )

    @staticmethod
    def _multi_molecule_note(input_path: Path, input_format: str) -> str:
        """Warn when a MOL2/SDF holds several molecules; only the first is converted.

        RDKit and Open Babel both read a single record here, so a multi-molecule
        library would otherwise be silently truncated to its first entry.
        """
        if input_format not in {"mol2", "sdf"}:
            return ""
        marker = "@<TRIPOS>MOLECULE" if input_format == "mol2" else "$$$$"
        try:
            count = input_path.read_text(encoding="utf-8", errors="replace").count(
                marker
            )
        except OSError:
            return ""
        if count <= 1:
            return ""
        return (
            f"Aviso: o arquivo contém {count} moléculas; apenas a primeira foi "
            "convertida. Separe-as em arquivos individuais para o modo de triagem."
        )

    @staticmethod
    def _mol2_fallback_via_molblock(input_path: Path):
        """Read unsupported MOL2 variants with Open Babel, preserving formal charges."""
        from rdkit import Chem
        from openbabel import pybel

        molecule = pybel.readstring("mol2", input_path.read_text(encoding="utf-8"))
        return Chem.MolFromMolBlock(molecule.write("mol"), removeHs=False)


    @staticmethod
    def _prepare_ligand_molecule(mol) -> tuple[object, str]:
        """Return an RDKit ligand ready for Meeko, keeping one covalent component."""
        from rdkit import Chem
        from rdkit.Chem import AllChem

        working = Chem.Mol(mol)
        Chem.SanitizeMol(working)

        fragments = Chem.GetMolFrags(working, asMols=True, sanitizeFrags=True)
        note = ""
        if len(fragments) > 1:
            selected = max(
                fragments,
                key=lambda fragment: sum(
                    1 for atom in fragment.GetAtoms() if atom.GetAtomicNum() > 1
                ),
            )
            note = (
                "Ligante continha múltiplos fragmentos; mantido o maior fragmento "
                "covalente para evitar sais/contraíons desconectados no PDBQT."
            )
            working = Chem.Mol(selected)

        Chem.Kekulize(working, clearAromaticFlags=False)
        working = Chem.AddHs(working, addCoords=True)

        if working.GetNumConformers() == 0 or not working.GetConformer().Is3D():
            working.RemoveAllConformers()
            params = AllChem.ETKDGv3()
            params.randomSeed = 61453
            if AllChem.EmbedMolecule(working, params) != 0:
                raise ValueError(
                    "RDKit não conseguiu gerar coordenadas 3D para o ligante."
                )
            if AllChem.MMFFHasAllMoleculeParams(working):
                AllChem.MMFFOptimizeMolecule(working, maxIters=200)
            note = (note + " Coordenadas 3D geradas com RDKit ETKDGv3.").strip()
        return working, note

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
    @atomic_conversion("receptor")
    def convert_pdb_to_pdbqt_receptor(
        input_path: Path, output_path: Path, allow_fallback: bool = False
    ) -> ConversionResult:
        """Convert a receptor PDB to PDBQT with Meeko in-process, OpenBabel fallback."""
        meeko_result = FileConverter._convert_receptor_via_meeko(input_path, output_path)
        if meeko_result is not None and meeko_result.success:
            return meeko_result
        primary_log = (
            meeko_result.log + "\n" + meeko_result.errors
            if meeko_result is not None
            else "Meeko (mk_prepare_receptor) indisponível."
        )
        if not allow_fallback:
            return ConversionResult(False, output_path, primary_log,
                "Meeko não preparou o receptor. Revise os resíduos e átomos do PDB; "
                "Open Babel pode ser selecionado explicitamente no conversor.")
        return FileConverter._convert_via_openbabel(
            input_path, output_path, receptor=True, previous_error=primary_log
        )

    @staticmethod
    def _convert_receptor_via_meeko(
        input_path: Path, output_path: Path
    ) -> ConversionResult | None:
        """Serialize the CLI entry point, which temporarily changes sys.argv."""
        with _RECEPTOR_CLI_LOCK:
            return FileConverter._convert_receptor_via_meeko_locked(input_path, output_path)

    @staticmethod
    def _convert_receptor_via_meeko_locked(
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
        Alternate conformation A is selected explicitly; incomplete residues
        cause failure instead of being silently removed. Returns ``None`` when Meeko cannot be imported so the caller
        falls back to Open Babel.
        """
        try:
            from meeko.cli import mk_prepare_receptor as receptor_cli
        except Exception:  # noqa: BLE001 - missing/broken Meeko -> OpenBabel fallback
            return None

        import contextlib
        import io
        from core.receptor_input import normalize_receptor_pdb

        normalized, repaired_count = normalize_receptor_pdb(input_path.read_text(encoding="utf-8"))
        normalized_path = output_path.parent / "normalized_receptor.pdb"
        normalized_path.write_text(normalized, encoding="utf-8")

        argv = [
            "mk_prepare_receptor",
            "--read_pdb",
            str(normalized_path),
            "-o",
            str(output_path.with_suffix("")),
            "-p",
            str(output_path),
            "--default_altloc",
            "A",
        ]
        captured = io.StringIO()
        saved_argv = sys.argv
        exit_code: int = 0
        FileConverter._remove_stale_output(output_path)
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

        if exit_code == 0 and output_path.exists() and output_path.stat().st_size > 0:
            return ConversionResult(
                True,
                output_path,
                f"Receptor preparado com Meeko (mk_prepare_receptor). Colunas PDB normalizadas: {repaired_count}. Conformações alternativas: A quando presentes.\n" + captured.getvalue(),
                "",
            )
        return ConversionResult(
            False,
            output_path,
            captured.getvalue(),
            f"Meeko não gerou o PDBQT do receptor (código {exit_code}).",
        )

    @staticmethod
    @atomic_conversion("receptor")
    def convert_mol2_to_pdbqt_receptor(
        input_path: Path, output_path: Path
    ) -> ConversionResult:
        """Read MOL2/SDF via Open Babel, then parameterize the receptor with Meeko."""
        import tempfile
        try:
            from openbabel import pybel
            if FileConverter._multi_molecule_note(input_path, FileConverter._obabel_input_format(input_path)):
                raise ValueError("O receptor contém múltiplas moléculas/registros. Selecione uma estrutura por arquivo.")
            with tempfile.TemporaryDirectory(prefix="vinalab_receptor_") as directory:
                intermediate = Path(directory) / "receptor.pdb"
                molecule = pybel.readstring(FileConverter._obabel_input_format(input_path), input_path.read_text(encoding="utf-8-sig"))
                # Imported hydrogen names/residue assignments are not reliable in
                # SDF/MOL2. Meeko rebuilds them from its receptor templates.
                molecule.OBMol.DeleteHydrogens()
                # Open Babel may append hydrogens after all heavy atoms, revisiting
                # residues. Meeko requires each residue's atoms to be contiguous.
                residues = {}
                for line in molecule.write("pdb").splitlines():
                    if line.startswith(("ATOM  ", "HETATM")):
                        residues.setdefault(line[17:27], []).append(line)
                intermediate.write_text("\n".join(
                    line for atoms in residues.values() for line in atoms
                ) + "\nEND\n", encoding="utf-8")
                result = FileConverter.convert_pdb_to_pdbqt_receptor(intermediate, output_path)
                return ConversionResult(result.success, result.output_path,
                    "Leitura MOL2/SDF: Open Babel; preparação PDBQT: Meeko.\n" + result.log,
                    result.errors)
        except Exception as exc:
            return ConversionResult(False, output_path, "", f"Falha ao ler receptor MOL2/SDF: {exc}")

    @staticmethod
    def auto_convert(input_path: Path, molecule_type: str) -> ConversionResult:
        """Auto-detect input format and convert to PDBQT for ligand or receptor."""
        detected = FileConverter._detect_format(input_path)
        output_path = input_path.with_suffix(".pdbqt")
        if detected == "pdbqt":
            try:
                validate_prepared_pdbqt(input_path, molecule_type)
            except (ValueError, OSError) as exc:
                return ConversionResult(False, input_path, "", str(exc))
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
        obabel_cli_available = find_obabel_executable() is not None
        return {
            "rdkit": importlib.util.find_spec("rdkit") is not None,
            "meeko": importlib.util.find_spec("meeko") is not None,
            "openbabel_py": openbabel_available,
            "obabel_cli": obabel_cli_available,
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
    def _convert_via_openbabel_py_api(
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
            molecule = pybel.readstring(input_format, input_path.read_text(encoding="utf-8-sig"))
            if receptor:
                molecule.OBMol.AddHydrogens()
            else:
                # Peptide/ligand MOL2 files often carry charged termini (N.4, O.co2)
                # and no explicit hydrogens; pH-aware protonation is what makes them
                # usable, mirroring `obabel ... -p 7.4`.
                molecule.OBMol.AddHydrogens(False, True, LIGAND_PROTONATION_PH)
            options = {"r": True} if receptor else {}
            output_path.write_text(molecule.write("pdbqt", opt=options), encoding="utf-8")
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
                f"{previous_error}\n{descriptor} convertido com Open Babel (API em processo).",
                "",
            )
        return ConversionResult(
            False,
            output_path,
            "",
            f"{previous_error}\nOpen Babel não gerou o PDBQT.",
        )

    @staticmethod
    @atomic_conversion("dynamic")
    def _convert_via_openbabel(
        input_path: Path,
        output_path: Path,
        receptor: bool,
        previous_error: str,
    ) -> ConversionResult:
        """Convert to PDBQT with Open Babel API first, then the CLI runtime."""
        input_format = FileConverter._obabel_input_format(input_path)
        multi_note = FileConverter._multi_molecule_note(input_path, input_format)
        if multi_note and receptor:
            return ConversionResult(False, output_path, "", "O receptor contém múltiplas moléculas/registros. Selecione uma estrutura por arquivo.")
        if multi_note:
            previous_error = previous_error + "\n" + multi_note
        if not receptor and input_format in {"sdf", "mol"}:
            from openbabel import pybel
            molecule = pybel.readstring(input_format, input_path.read_text(encoding="utf-8-sig"))
            if molecule.OBMol.GetDimension() != 3:
                return ConversionResult(False, output_path, "", "O ligante não possui coordenadas 3D. Selecione Meeko para gerar um conformero 3D antes do docking.")
        FileConverter._remove_stale_output(output_path)
        api_result = FileConverter._convert_via_openbabel_py_api(
            input_path, output_path, receptor, previous_error
        )
        if api_result.success:
            return api_result
        cli_error = api_result.errors or previous_error
        return FileConverter._convert_via_openbabel_cli(
            input_path, output_path, receptor, cli_error
        )

    @staticmethod
    def _convert_via_openbabel_cli(
        input_path: Path,
        output_path: Path,
        receptor: bool,
        previous_error: str,
    ) -> ConversionResult:
        """Convert to PDBQT through the bundled Open Babel CLI."""
        obabel = find_obabel_executable()
        if obabel is None:
            return ConversionResult(
                False,
                output_path,
                "",
                f"{previous_error}\nOpen Babel CLI não encontrado.",
            )

        command = [str(obabel), str(input_path), "-O", str(output_path)]
        if receptor:
            command.append("-xr")
        else:
            command.extend(
                ["-p", str(LIGAND_PROTONATION_PH), "--partialcharge", "gasteiger"]
            )
        try:
            FileConverter._remove_stale_output(output_path)
            completed = subprocess.run(
                command,
                env=native_tool_env(obabel),
                capture_output=True,
                text=True,
                check=False,
                creationflags=NO_WINDOW,
            )
        except OSError as exc:
            return ConversionResult(
                False,
                output_path,
                "",
                f"{previous_error}\nOpen Babel CLI falhou ao iniciar: {exc}",
            )
        if completed.returncode != 0:
            message = (
                completed.stderr.strip()
                or completed.stdout.strip()
                or f"Open Babel CLI finalizou com código {completed.returncode}."
            )
            return ConversionResult(
                False,
                output_path,
                completed.stdout,
                f"{previous_error}\nOpen Babel CLI falhou: {message}",
            )
        if output_path.exists() and output_path.stat().st_size > 0:
            descriptor = "Receptor" if receptor else "Ligante"
            return ConversionResult(
                True,
                output_path,
                f"{descriptor} convertido com Open Babel CLI (fallback).",
                completed.stderr.strip(),
            )
        return ConversionResult(
            False,
            output_path,
            completed.stdout,
            f"{previous_error}\nOpen Babel CLI não gerou o PDBQT.",
        )

    @staticmethod
    def _remove_stale_output(output_path: Path) -> None:
        """Remove previous conversion output so stale files cannot look successful."""
        try:
            if output_path.exists():
                output_path.unlink()
        except OSError:
            pass

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
    def _validate_ligand_bond_geometry(output_path: Path, reference_mol) -> None:
        """Check retained heavy coordinates using Meeko's explicit atom mapping.

        PDBQT torsion-tree order is not RDKit atom order. Nonpolar hydrogens
        disappear and macrocycle pseudo-atoms may appear during preparation.
        """
        if reference_mol is None or reference_mol.GetNumConformers() == 0:
            return
        index_map = {}
        coordinates = {}
        for line in output_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("REMARK INDEX MAP"):
                pairs = [int(value) for value in line.split()[3:]]
                index_map.update(zip(pairs[::2], pairs[1::2]))
            elif line.startswith(("ATOM  ", "HETATM")):
                coordinates[int(line[6:11])] = tuple(float(line[i:i + 8]) for i in (30, 38, 46))
        if not index_map:
            raise ValueError("Meeko não forneceu o mapa de átomos para validar a geometria.")
        conformer = reference_mol.GetConformer()
        for atom in reference_mol.GetAtoms():
            if atom.GetAtomicNum() == 1:
                continue
            serial = index_map.get(atom.GetIdx() + 1)
            if serial not in coordinates:
                raise ValueError("Um átomo pesado foi perdido durante a conversão.")
            expected = tuple(conformer.GetAtomPosition(atom.GetIdx()))
            if FileConverter._distance(expected, coordinates[serial]) > 0.001:
                raise ValueError("As coordenadas de um átomo pesado mudaram durante a conversão.")

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
