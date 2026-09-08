"""Smoke-test the actual frozen runtime without a developer Python environment."""

import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import traceback


def run(output_directory: str) -> int:
    root = Path(output_directory).resolve()
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

            peptide = Chem.AddHs(Chem.MolFromSequence("AG"))
            AllChem.EmbedMolecule(peptide, randomSeed=42)
            receptor = root / "receptor.pdb"
            Chem.MolToPDBFile(Chem.RemoveHs(peptide), str(receptor))
            converted = FileConverter.auto_convert(receptor, "receptor")
            if not converted.success:
                raise RuntimeError(converted.log + converted.errors)
            assert "Meeko" in converted.log
            validate_pdbqt_charges(converted.output_path)
            ligand = root / "ligand.sdf"
            molecule = Chem.AddHs(Chem.MolFromSmiles("CCO"))
            AllChem.EmbedMolecule(molecule, randomSeed=42)
            with Chem.SDWriter(str(ligand)) as writer:
                writer.write(molecule)
            prepared = FileConverter.auto_convert(ligand, "ligand")
            if not prepared.success:
                raise RuntimeError(prepared.log + prepared.errors)
            validate_ligand_pdbqt(prepared.output_path)
            vina = find_vina_executable()
            for scoring in ("vina", "vinardo"):
                output = root / f"{scoring}_out.pdbqt"
                command = [str(vina), "--receptor", str(converted.output_path),
                           "--ligand", str(prepared.output_path), "--scoring", scoring,
                           "--center_x", "0", "--center_y", "0", "--center_z", "0",
                           "--size_x", "20", "--size_y", "20", "--size_z", "20",
                           "--exhaustiveness", "1", "--num_modes", "1", "--cpu", "1",
                           "--seed", "42", "--out", str(output)]
                result = subprocess.run(command, env=native_tool_env(vina), capture_output=True,
                    text=True, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0)
                if result.returncode or not output.exists() or "REMARK VINA RESULT" not in output.read_text():
                    raise RuntimeError(result.stdout + result.stderr)
                report[scoring] = output.name
            report["success"] = True
    except Exception:
        report["error"] = traceback.format_exc()
    report["log"] = log.getvalue()
    (root / "smoke.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["success"] else 1
