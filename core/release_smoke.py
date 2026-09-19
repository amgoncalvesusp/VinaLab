"""Smoke-test the actual frozen runtime without a developer Python environment."""

import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import traceback


def run(output_directory: str, receptor_path: str | None = None, ligand_path: str | None = None) -> int:
    root = Path(output_directory).resolve()
    for source in (receptor_path, ligand_path):
        if source and Path(source).resolve().is_relative_to(root):
            if sys.stderr is not None:
                print("Smoke inputs must be outside the output directory; no files changed.", file=sys.stderr)
            return 1
    root.mkdir(parents=True, exist_ok=True)
    report = {"success": False, "frozen": bool(getattr(sys, "frozen", False))}
    log = io.StringIO()
    try:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            from scripts.check_runtime_dependencies import main as check_runtime
            if check_runtime() != 0:
                raise RuntimeError("Runtime dependency check failed")
            from rdkit import Chem
            from rdkit.Chem import AllChem
            from core.converter import FileConverter
            from core.file_utils import validate_ligand_pdbqt, validate_pdbqt_charges
            from core.native_tools import find_vina_executable, native_tool_env
            from core.conversion_smoke import check_conversion_formats
            report["conversion_formats"] = check_conversion_formats(root)

            peptide = Chem.AddHs(Chem.MolFromSequence("AG"))
            AllChem.EmbedMolecule(peptide, randomSeed=42)
            receptor = root / "receptor.pdb"
            Chem.MolToPDBFile(Chem.RemoveHs(peptide), str(receptor))
            if receptor_path:
                receptor.write_bytes(Path(receptor_path).read_bytes())
            converted = FileConverter.auto_convert(receptor, "receptor")
            if not converted.success:
                raise RuntimeError(converted.log + converted.errors)
            assert "Meeko" in converted.log
            assert validate_pdbqt_charges(converted.output_path)
            ligand = root / "ligand.sdf"
            molecule = Chem.AddHs(Chem.MolFromSmiles("CCO"))
            AllChem.EmbedMolecule(molecule, randomSeed=42)
            with Chem.SDWriter(str(ligand)) as writer:
                writer.write(molecule)
            if ligand_path:
                original_ligand = Path(ligand_path)
                ligand = root / ("user_ligand" + original_ligand.suffix)
                ligand.write_bytes(original_ligand.read_bytes())
            prepared = FileConverter.auto_convert(ligand, "ligand")
            if not prepared.success:
                raise RuntimeError(prepared.log + prepared.errors)
            validate_ligand_pdbqt(prepared.output_path)
            vina = find_vina_executable()
            coordinates = [atom["xyz"] for atom in FileConverter._pdbqt_atoms(prepared.output_path)]
            center = [sum(xyz[axis] for xyz in coordinates) / len(coordinates) for axis in range(3)]
            for scoring in ("vina", "vinardo"):
                output = root / f"{scoring}_out.pdbqt"
                command = [str(vina), "--receptor", str(converted.output_path),
                           "--ligand", str(prepared.output_path), "--scoring", scoring,
                           "--center_x", str(center[0]), "--center_y", str(center[1]), "--center_z", str(center[2]),
                           "--size_x", "20", "--size_y", "20", "--size_z", "20",
                           "--exhaustiveness", "1", "--num_modes", "1", "--cpu", "1",
                           "--seed", "42", "--out", str(output)]
                result = subprocess.run(command, env=native_tool_env(vina), capture_output=True,
                    text=True, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0)
                if result.returncode or not output.exists() or "REMARK VINA RESULT" not in output.read_text():
                    raise RuntimeError(result.stdout + result.stderr)
                report[scoring] = output.name
                from tabs.results_dialogs import ExportWorker
                from core.complex_export import read_export_atoms
                exports = root / f"exports_{scoring}"
                exports.mkdir(exist_ok=True)
                row = {"_export_name": scoring, "output_file": str(output), "mode": 1,
                       "receptor_file": str(converted.output_path)}
                export_counts = {}
                for fmt in ("pdbqt", "pdb", "mol2"):
                    destination = exports / fmt
                    destination.mkdir(exist_ok=True)
                    worker = ExportWorker([row], destination, fmt, True, "en")
                    worker._export_row(row, destination, fmt)
                    complex_fmt = "mol2" if fmt == "mol2" else "pdb"
                    complex_path = destination / f"{scoring}_complex.{complex_fmt}"
                    export_counts[fmt] = len(read_export_atoms(complex_path.read_text(encoding="utf-8"), complex_fmt))
                report[f"{scoring}_complex_atoms"] = export_counts
            report["success"] = True
    except Exception:
        report["error"] = traceback.format_exc()
    report["log"] = log.getvalue()
    (root / "smoke.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["success"] else 1
