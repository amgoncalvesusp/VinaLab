# -*- coding: utf-8 -*-
"""Optional smoke tests for conversion and bundled Vina CLI docking."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from core.converter import FileConverter
from core.file_utils import validate_ligand_pdbqt, validate_pdbqt_charges
from core.native_tools import find_vina_executable, native_tool_env


NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0


class SmokeWorkflowTests(unittest.TestCase):
    """Run real minimal workflows when the native/runtime dependencies exist."""

    def test_smoke_convert_ligand_sdf_to_pdbqt(self) -> None:
        """Convert a minimal SDF ligand to a validated PDBQT."""
        deps = FileConverter.check_dependencies()
        if not (deps["rdkit"] and deps["meeko"]):
            self.skipTest("RDKit/Meeko not installed")
        with tempfile.TemporaryDirectory() as tmpdir:
            ligand = Path(tmpdir) / "ethanol.sdf"
            ligand.write_text(_ETHANOL_SDF, encoding="utf-8")
            result = FileConverter.auto_convert(ligand, "ligand")

            self.assertTrue(result.success, result.errors)
            validate_ligand_pdbqt(result.output_path)
            self.assertTrue(validate_pdbqt_charges(result.output_path))

    def test_smoke_convert_receptor_pdb_to_pdbqt(self) -> None:
        """Convert a minimal receptor PDB to a charged PDBQT."""
        deps = FileConverter.check_dependencies()
        if not (deps["mk_prepare_receptor"] or deps["openbabel_py"] or deps["obabel_cli"]):
            self.skipTest("No receptor converter runtime installed")
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor = Path(tmpdir) / "receptor.pdb"
            receptor.write_text(_RECEPTOR_PDB, encoding="utf-8")
            result = FileConverter.auto_convert(receptor, "receptor")

            self.assertTrue(result.success, result.errors)
            self.assertTrue(validate_pdbqt_charges(result.output_path))

    def test_smoke_vina_cli_docking(self) -> None:
        """Run the bundled Vina CLI on a minimal receptor/ligand pair."""
        vina = find_vina_executable()
        if vina is None:
            self.skipTest("Vina CLI not available")
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            receptor = root / "receptor.pdbqt"
            ligand = root / "ligand.pdbqt"
            output = root / "ligand_vina_out.pdbqt"
            receptor.write_text(_RECEPTOR_PDBQT, encoding="utf-8")
            ligand.write_text(_LIGAND_PDBQT, encoding="utf-8")

            completed = subprocess.run(
                [
                    str(vina),
                    "--receptor",
                    str(receptor),
                    "--ligand",
                    str(ligand),
                    "--center_x",
                    "0",
                    "--center_y",
                    "0",
                    "--center_z",
                    "0",
                    "--size_x",
                    "20",
                    "--size_y",
                    "20",
                    "--size_z",
                    "20",
                    "--exhaustiveness",
                    "1",
                    "--num_modes",
                    "1",
                    "--scoring",
                    "vina",
                    "--out",
                    str(output),
                ],
                cwd=root,
                env=native_tool_env(vina),
                capture_output=True,
                text=True,
                check=False,
                creationflags=NO_WINDOW,
                timeout=30,
            )

            self.assertEqual(
                completed.returncode,
                0,
                completed.stderr or completed.stdout,
            )
            self.assertTrue(output.exists())
            self.assertIn("REMARK VINA RESULT:", output.read_text(encoding="utf-8"))


_ETHANOL_SDF = """ethanol
  VinaLab

  3  2  0  0  0  0            999 V2000
    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.5000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    2.1000    1.2000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0  0  0  0
  2  3  1  0  0  0  0
M  END
$$$$
"""

_RECEPTOR_PDB = """ATOM      1  N   ALA A   1      -1.000   0.000   0.000  1.00  0.00           N
ATOM      2  CA  ALA A   1       0.000   0.000   0.000  1.00  0.00           C
ATOM      3  C   ALA A   1       1.400   0.000   0.000  1.00  0.00           C
ATOM      4  O   ALA A   1       2.000   1.000   0.000  1.00  0.00           O
TER
END
"""

_RECEPTOR_PDBQT = """ATOM      1  C   REC A   1       0.000   0.000   0.000  1.00  0.00     0.000 C
END
"""

_LIGAND_PDBQT = """ROOT
ATOM      1  C   LIG     1       1.500   0.000   0.000  1.00  0.00     0.000 C
ENDROOT
TORSDOF 0
"""


if __name__ == "__main__":
    unittest.main()
