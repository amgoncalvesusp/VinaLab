"""Synthetic native-engine QA; not a scientific accuracy or affinity benchmark."""

import argparse
import json
import math
import sys
import traceback
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

from vinalab_core.runtime_paths import resource_root


def _conversion(root):
    from meeko import ResidueChemTemplates
    from rdkit import Chem
    from rdkit.Chem import AllChem

    from vinalab_core.prepare.conversion import convert_ligand, convert_receptor

    ResidueChemTemplates.create_from_defaults()
    molecules = (("ligand", Chem.MolFromSmiles("CCO")),
                 ("receptor", Chem.MolFromSequence("AAA")))
    for name, molecule in molecules:
        molecule = Chem.AddHs(molecule)
        if AllChem.EmbedMolecule(molecule, randomSeed=17) != 0:
            raise RuntimeError(f"Could not generate {name} coordinates")
        if name == "ligand":
            with Chem.SDWriter(str(root / "ligand.sdf")) as writer:
                writer.write(molecule)
        else:
            Chem.MolToPDBFile(molecule, str(root / "receptor.pdb"))
    ligand = convert_ligand(root / "ligand.sdf", root / "ligand.pdbqt")
    receptor = convert_receptor(root / "receptor.pdb", root / "receptor.pdbqt")
    if not ligand.success or not receptor.success:
        raise RuntimeError(f"Ligand: {ligand.errors}; receptor: {receptor.errors}")
    return {"ligand": ligand.log, "receptor": receptor.log, "meeko_templates": True}


def _reference(root, poses="ligand.pdbqt"):
    from vinalab_core.analysis.poses import validate_reference_poses

    records = validate_reference_poses(root / poses, root / "ligand.sdf")
    if not records or any(not r.comparable or r.rmsd is None or not math.isfinite(r.rmsd)
                          for r in records):
        raise RuntimeError(f"Reference mapping failed: {records}")
    if poses == "ligand.pdbqt" and any(r.rmsd > .002 for r in records):
        raise RuntimeError("Conversion changed reference heavy coordinates")
    return {"comparisons": [asdict(record) for record in records]}


def _docking(root, scoring):
    from vinalab_core.docking.docking_service import DockingService
    from vinalab_core.docking.search_box import SearchBox
    from vinalab_core.tools.tool_locator import ToolLocator

    executable = ToolLocator(resource_root()).find("vina")
    if executable is None:
        raise RuntimeError("Native Vina missing")
    output = root / f"{scoring}-poses.pdbqt"
    result = DockingService(executable).run(
        receptor=root / "receptor.pdbqt", ligand=root / "ligand.pdbqt", output=output,
        search_box=SearchBox((0., 0., 0.), (18., 18., 18.), "synthetic", 0., "user"),
        cpu_threads=1, exhaustiveness=1, seed=17, num_modes=2, scoring=scoring,
        timeout_seconds=120,
    )
    if not result.ok:
        raise RuntimeError(f"{result.errors}\n{result.process.stdout}\n{result.process.stderr}")
    return {"executable": str(executable), "command": result.process.command,
            "poses": [asdict(pose) for pose in result.poses],
            "stdout": result.process.stdout, "reference": _reference(root, output.name)}


def _xtb(root, method):
    from vinalab_core.scoring.xtb_scorer import XtbScorer

    receptor, ligand = root / f"water-a-{method}.xyz", root / f"water-b-{method}.xyz"
    receptor.write_text("3\nwater A\nO 0 0 0\nH .9572 0 0\nH -.239 .927 0\n", encoding="utf-8")
    ligand.write_text("3\nwater B\nO 0 0 3\nH .9572 0 3\nH -.239 .927 3\n", encoding="utf-8")
    result = XtbScorer(resource_root()).score_interaction(
        receptor, ligand, charge_receptor=0, charge_ligand=0,
        uhf_receptor=0, uhf_ligand=0, uhf_complex=0, hydrogen_complete=True,
        method=method, cpu_threads=1, timeout_seconds=120,
    )
    if not math.isfinite(result.interaction_kcal_per_mol):
        raise RuntimeError("Nonfinite xTB interaction energy")
    return asdict(result)


def _step(name, action):
    try:
        return {"name": name, "ok": True, "result": action()}
    except Exception as exc:  # noqa: BLE001 - retain diagnostics from native/library failures
        return {"name": name, "ok": False, "error": str(exc), "traceback": traceback.format_exc()}


def run_services(root):
    return [
        _step("conversion", lambda: _conversion(root)),
        _step("reference", lambda: _reference(root)),
        _step("vina", lambda: _docking(root, "vina")),
        _step("vinardo", lambda: _docking(root, "vinardo")),
        _step("xtb_gfn2", lambda: _xtb(root, "gfn2")),
        _step("xtb_gfnff", lambda: _xtb(root, "gfnff")),
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-test-output", required=True, type=Path)
    try:
        arguments = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    try:
        output = arguments.smoke_test_output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as report_file:
            with TemporaryDirectory(prefix="vinalab-smoke-") as directory:
                steps = run_services(Path(directory))
            report = {"ok": bool(steps) and all(step["ok"] for step in steps),
                      "frozen": bool(getattr(sys, "frozen", False)),
                      "platform": sys.platform, "executable": sys.executable,
                      "resource_root": str(resource_root()), "steps": steps}
            text = json.dumps(report, indent=2, allow_nan=False)
            report_file.write(text + "\n")
        if sys.stdout is not None:
            print(text)
        return 0 if report["ok"] else 1
    except (OSError, ValueError) as exc:
        if sys.stderr is not None:
            print(str(exc), file=sys.stderr)
        return 2
