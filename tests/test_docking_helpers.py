# -*- coding: utf-8 -*-
"""Unit tests for docking helper utilities."""

from pathlib import Path
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

qtcore = types.ModuleType("PySide6.QtCore")


class _DummyQThread:
    pass


class _DummySignal:
    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs


qtcore.QThread = _DummyQThread
qtcore.Signal = _DummySignal
sys.modules.setdefault("PySide6", types.ModuleType("PySide6"))
sys.modules["PySide6.QtCore"] = qtcore

from core.docking_engine import (
    DockingWorker,
    discover_external_scoring_functions,
    extract_pose_model,
)
from core.native_tools import (
    find_gnina_executable,
    find_native_executable,
    find_smina_executable,
    find_vina_executable,
    native_tool_env,
    native_tool_missing_dlls,
    native_tool_starts,
)
from core.file_utils import pdbqt_receptor_atoms, validate_ligand_pdbqt


class DockingHelperTests(unittest.TestCase):
    """Cover helper behavior that does not require heavy docking dependencies."""

    def test_discover_external_scoring_functions_is_empty_in_light_build(self) -> None:
        """VinaLab Light should not expose bundled external rescoring archives."""
        self.assertEqual(discover_external_scoring_functions(), [])

    def test_native_tool_env_adds_tool_directory_for_dlls_and_plugins(self) -> None:
        """Bundled GNINA must find sibling DLLs and OpenBabel plugin modules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool_dir = Path(tmpdir) / "gnina"
            tool_dir.mkdir()
            tool_path = tool_dir / "gnina.exe"
            tool_path.write_text("", encoding="utf-8")
            (tool_dir / "formats_common.obf").write_text("", encoding="utf-8")

            env = native_tool_env(tool_path, {"PATH": "C:\\Windows\\System32"})

        resolved_tool_dir = str(tool_dir.resolve())
        self.assertTrue(env["PATH"].startswith(resolved_tool_dir))
        self.assertEqual(env["BABEL_LIBDIR"], resolved_tool_dir)

    def test_native_tool_env_adds_openbabel_and_torch_runtime_paths(self) -> None:
        """Frozen tools should see Open Babel plugins/data and libtorch DLLs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bundle_dir = root / "_MEI"
            openbabel_bin = bundle_dir / "openbabel" / "bin"
            openbabel_data = openbabel_bin / "data"
            torch_lib = bundle_dir / "torch" / "lib"
            for path in (openbabel_bin, openbabel_data, torch_lib):
                path.mkdir(parents=True)
            (openbabel_bin / "formats_common.obf").write_text("", encoding="utf-8")
            (torch_lib / "c10.dll").write_text("", encoding="utf-8")
            tool_path = root / "gnina.exe"
            tool_path.write_text("", encoding="utf-8")

            with mock.patch.object(sys, "_MEIPASS", str(bundle_dir), create=True):
                env = native_tool_env(
                    tool_path,
                    {"PATH": "C:\\Windows\\System32", "LD_LIBRARY_PATH": "/usr/lib"},
                )

        path_entries = env["PATH"].split(os.pathsep)
        self.assertIn(str(openbabel_bin.resolve()), path_entries)
        self.assertIn(str(torch_lib.resolve()), path_entries)
        self.assertEqual(env["BABEL_LIBDIR"], str(openbabel_bin.resolve()))
        self.assertEqual(env["BABEL_DATADIR"], str(openbabel_data.resolve()))

    def test_native_tool_env_finds_nested_openbabel_plugins(self) -> None:
        """openbabel-wheel can keep .obf plugins below a versioned package subdir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            executable_dir = root / "Scripts"
            package_root = root / "Lib" / "site-packages" / "openbabel"
            plugin_dir = package_root / "share" / "openbabel" / "3.1.0"
            data_dir = package_root / "data"
            for path in (executable_dir, plugin_dir, data_dir):
                path.mkdir(parents=True)
            (plugin_dir / "formats_common.obf").write_text("", encoding="utf-8")
            tool_path = executable_dir / "obabel.exe"
            tool_path.write_text("", encoding="utf-8")

            with mock.patch("sys.executable", str(executable_dir / "python.exe")):
                env = native_tool_env(tool_path, {"PATH": ""})

            self.assertTrue(Path(env["BABEL_LIBDIR"]).samefile(plugin_dir))

    def test_native_tool_env_finds_posix_site_packages_openbabel(self) -> None:
        """Linux Python installs keep site-packages beside bin, not below it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            executable_dir = root / "bin"
            package_root = (
                root
                / "lib"
                / f"python{sys.version_info.major}.{sys.version_info.minor}"
                / "site-packages"
                / "openbabel"
            )
            plugin_dir = package_root / "plugins" / "3.1.0"
            data_dir = package_root / "share" / "openbabel" / "3.1.0"
            for path in (executable_dir, plugin_dir, data_dir):
                path.mkdir(parents=True)
            (plugin_dir / "formats_common.obf").write_text("", encoding="utf-8")
            tool_path = executable_dir / "obabel"
            tool_path.write_text("", encoding="utf-8")

            with (
                mock.patch("sys.executable", str(executable_dir / "python")),
                mock.patch("sys.platform", "linux"),
            ):
                env = native_tool_env(tool_path, {"PATH": ""})

            self.assertTrue(Path(env["BABEL_LIBDIR"]).samefile(plugin_dir))
            self.assertEqual(env["BABEL_DATADIR"], str(data_dir.resolve()))

    def test_native_tool_env_accepts_linux_openbabel_so_plugins(self) -> None:
        """Ubuntu Open Babel packages ship format plugins as .so modules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            executable_dir = root / "bin"
            plugin_dir = root / "lib" / "openbabel" / "3.1.1"
            data_dir = root / "share" / "openbabel" / "3.1.1"
            for path in (executable_dir, plugin_dir, data_dir):
                path.mkdir(parents=True)
            (plugin_dir / "pdbqtformat.so").write_text("", encoding="utf-8")
            tool_path = executable_dir / "obabel"
            tool_path.write_text("", encoding="utf-8")

            with (
                mock.patch("sys.executable", str(executable_dir / "python")),
                mock.patch("sys.platform", "linux"),
                mock.patch(
                    "core.native_tools._openbabel_roots",
                    return_value=[plugin_dir.parent, data_dir.parent],
                ),
            ):
                env = native_tool_env(tool_path, {"PATH": ""})

            self.assertTrue(Path(env["BABEL_LIBDIR"]).samefile(plugin_dir))

    def test_native_tool_env_overrides_invalid_openbabel_env(self) -> None:
        """Bundled tools should not inherit stale Open Babel plugin/data paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            executable_dir = root / "Scripts"
            openbabel_bin = root / "Lib" / "site-packages" / "openbabel" / "bin"
            openbabel_data = openbabel_bin / "data"
            for path in (executable_dir, openbabel_bin, openbabel_data):
                path.mkdir(parents=True)
            (openbabel_bin / "formats_common.obf").write_text("", encoding="utf-8")
            tool_path = executable_dir / "obabel.exe"
            tool_path.write_text("", encoding="utf-8")

            with mock.patch("sys.executable", str(executable_dir / "python.exe")):
                env = native_tool_env(
                    tool_path,
                    {
                        "PATH": "",
                        "BABEL_LIBDIR": str(root / "missing-plugins"),
                        "BABEL_DATADIR": str(root / "missing-data"),
                    },
                )

        self.assertEqual(env["BABEL_LIBDIR"], str(openbabel_bin.resolve()))
        self.assertEqual(env["BABEL_DATADIR"], str(openbabel_data.resolve()))

    def test_find_native_executable_prefers_python_scripts_before_path(self) -> None:
        """Bundled CLI discovery should not accidentally prefer unrelated PATH tools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scripts_dir = Path(tmpdir) / "Scripts"
            scripts_dir.mkdir()
            tool_path = scripts_dir / "obabel.exe"
            tool_path.write_text("", encoding="utf-8")
            with mock.patch("sys.executable", str(scripts_dir / "python.exe")):
                found = find_native_executable(("obabel.exe",), "openbabel")
        self.assertEqual(found, tool_path.resolve())

    def test_find_vina_executable_supports_linux_cli_name(self) -> None:
        """Ubuntu builds should discover a native vina CLI without a Windows suffix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scripts_dir = Path(tmpdir) / "bin"
            scripts_dir.mkdir()
            tool_path = scripts_dir / "vina"
            tool_path.write_text("", encoding="utf-8")
            with (
                mock.patch("sys.executable", str(scripts_dir / "python")),
                mock.patch("sys.platform", "linux"),
            ):
                found = find_vina_executable()
        self.assertEqual(found, tool_path.resolve())

    def test_find_smina_executable_supports_tools_directory(self) -> None:
        """Optional smina should be discoverable from tools/smina without being required."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tool_path = root / "tools" / "smina" / "smina.exe"
            tool_path.parent.mkdir(parents=True)
            tool_path.write_text("", encoding="utf-8")
            with (
                mock.patch("sys.executable", str(root / "VinaLab.exe")),
                mock.patch("sys.platform", "win32"),
                mock.patch("core.native_tools.native_tool_missing_dlls", return_value=()),
            ):
                found = find_smina_executable()
        self.assertEqual(found, tool_path.resolve())

    def test_native_tool_starts_rejects_non_executable_payload(self) -> None:
        """A discovered native tool must actually launch before it is advertised."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool_path = Path(tmpdir) / "gnina.exe"
            tool_path.write_text("", encoding="utf-8")
            self.assertFalse(native_tool_starts(tool_path, timeout=1))

    def test_native_tool_starts_skips_launch_when_dlls_are_missing(self) -> None:
        """Missing DLL preflight should prevent Windows system error dialogs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool_path = Path(tmpdir) / "gnina.exe"
            tool_path.write_text("", encoding="utf-8")
            with (
                mock.patch(
                    "core.native_tools.native_tool_missing_dlls",
                    return_value=("torch_cuda.dll",),
                ),
                mock.patch("core.native_tools.subprocess.run") as run_mock,
            ):
                self.assertFalse(native_tool_starts(tool_path, timeout=1))
            run_mock.assert_not_called()

    @unittest.skipUnless(sys.platform.startswith("win"), "Windows PE DLL check")
    def test_windows_gnina_is_not_discovered(self) -> None:
        """Windows builds should not advertise GNINA from PATH or tools/gnina."""
        self.assertIsNone(find_gnina_executable())

    def test_vina_cli_docking_uses_native_tool_env(self) -> None:
        """The bundled Vina CLI fallback must inherit native DLL/plugin paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            receptor = tmp_path / "receptor.pdbqt"
            ligand = tmp_path / "ligand.pdbqt"
            vina = tmp_path / "vina.exe"
            receptor.write_text("", encoding="utf-8")
            ligand.write_text("", encoding="utf-8")
            vina.write_text("", encoding="utf-8")
            worker = DockingWorker(
                receptor,
                None,
                None,
                [ligand],
                tmp_path,
                {
                    "scoring_function": "vina",
                    "vina_sf_name": "vina",
                    "center_x": 0,
                    "center_y": 0,
                    "center_z": 0,
                    "size_x": 10,
                    "size_y": 10,
                    "size_z": 10,
                    "exhaustiveness": 1,
                    "num_modes": 1,
                    "energy_range": 3,
                    "min_rmsd": 1,
                    "cpu": 1,
                    "seed": 0,
                },
            )
            worker.log_signal = types.SimpleNamespace(emit=lambda _message: None)

            def fake_run(command, **_kwargs):
                output = Path(command[command.index("--out") + 1])
                output.write_text(
                    "MODEL 1\nREMARK VINA RESULT: -1.0 0.0 0.0\nENDMDL\n",
                    encoding="utf-8",
                )
                return types.SimpleNamespace(returncode=0, stdout="", stderr="")

            with (
                mock.patch(
                    "core.docking_engine.native_tool_env",
                    return_value={"PATH": "native"},
                ) as env_mock,
                mock.patch("core.docking_engine.subprocess.run", side_effect=fake_run) as run_mock,
            ):
                rows = worker._dock_single_ligand_cli(ligand, vina)

        env_mock.assert_called_once_with(vina)
        self.assertEqual(run_mock.call_args.kwargs["env"], {"PATH": "native"})
        self.assertEqual(rows[0]["affinity"], -1.0)

    def test_light_scoring_selection_filters_unsupported_backends(self) -> None:
        """Saved GNINA/SMINA preferences should fall back to native Vina scoring."""
        worker = DockingWorker(
            Path("receptor.pdbqt"),
            None,
            None,
            [Path("ligand.pdbqt")],
            Path("."),
            {
                "scoring_function": "gnina",
                "scoring_functions": ["gnina", "smina", "vinardo"],
            },
        )
        self.assertEqual(worker._selected_scoring_functions(), ["vinardo"])

    def test_reference_ligand_rmsd_annotation(self) -> None:
        """Docked poses should carry RMSD against the selected reference ligand."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            receptor = tmp_path / "receptor.pdbqt"
            ligand = tmp_path / "ligand.pdbqt"
            output = tmp_path / "ligand_vina_out.pdbqt"
            reference = tmp_path / "reference.pdbqt"
            reference.write_text(
                "ATOM      1  C   LIG A   1       0.000   0.000   0.000  0.00  0.00     0.000 C\n",
                encoding="utf-8",
            )
            output.write_text(
                "MODEL 1\n"
                "REMARK VINA RESULT: -2.0 0.0 0.0\n"
                "ATOM      1  C   LIG A   1       1.000   0.000   0.000  0.00  0.00     0.000 C\n"
                "ENDMDL\n",
                encoding="utf-8",
            )
            worker = DockingWorker(
                receptor,
                None,
                None,
                [ligand],
                tmp_path,
                {
                    "scoring_function": "vina",
                    "reference_ligand": str(reference),
                    "reference_rmsd_cutoff": 2.0,
                },
            )
            worker._reference_ligand_text = worker._load_reference_ligand_text()
            rows = worker.parse_output_pdbqt(output, "ligand.pdbqt")
            worker._annotate_reference_rmsd(rows)

        self.assertEqual(rows[0]["reference_ligand"], str(reference))
        self.assertEqual(rows[0]["reference_rmsd_status"], "OK")
        self.assertEqual(rows[0]["reference_validation"], "Pass")
        self.assertEqual(rows[0]["reference_rmsd_cutoff"], 2.0)
        self.assertAlmostEqual(rows[0]["reference_rmsd"], 1.0)

    def test_extract_pose_model_returns_requested_block(self) -> None:
        """Only the requested MODEL block should be returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "poses.pdbqt"
            output_file.write_text(
                "\n".join(
                    [
                        "MODEL 1",
                        "REMARK VINA RESULT: -7.1 0.0 0.0",
                        "ENDMDL",
                        "MODEL 2",
                        "REMARK VINA RESULT: -6.5 0.0 0.0",
                        "ENDMDL",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            pose_block = extract_pose_model(output_file, 2)
        self.assertIn("MODEL 2", pose_block)
        self.assertNotIn("MODEL 1", pose_block)

    def test_extract_pose_model_can_strip_model_wrappers_and_null_bytes(self) -> None:
        """Single-pose exports should not carry multi-model wrappers or NUL padding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "poses.pdbqt"
            output_file.write_text(
                "\n".join(
                    [
                        "MODEL 1",
                        "REMARK VINA RESULT: -7.1 0.0 0.0",
                        "ATOM      1  C   UNL     1       1.000   1.000   1.000  1.00  0.00     0.000 C",
                        "\x00\x00",
                        "ENDMDL",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            pose_block = extract_pose_model(output_file, 1, include_model=False)
        self.assertNotIn("MODEL", pose_block)
        self.assertNotIn("ENDMDL", pose_block)
        self.assertNotIn("\x00", pose_block)
        self.assertIn("ATOM", pose_block)

    def test_pdbqt_receptor_atoms_includes_one_letter_residue_code(self) -> None:
        """Receptor atoms should expose residue identity and coordinates for the center picker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_file = Path(tmpdir) / "receptor.pdbqt"
            receptor_file.write_text(
                "ATOM      1  CA  ALA A  42      11.000  12.000  13.000  0.00  0.00      C\n",
                encoding="utf-8",
            )
            atoms = pdbqt_receptor_atoms(receptor_file)
        self.assertEqual(atoms[0]["one_letter"], "A")
        self.assertEqual(atoms[0]["residue_number"], "42")
        self.assertEqual(atoms[0]["atom_name"], "CA")
        self.assertEqual((atoms[0]["x"], atoms[0]["y"], atoms[0]["z"]), (11.0, 12.0, 13.0))

    def test_validate_ligand_pdbqt_rejects_multi_model_input(self) -> None:
        """A Vina output with multiple MODEL blocks must not be reused as one ligand input."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ligand_file = Path(tmpdir) / "multi_pose_ligand.pdbqt"
            ligand_file.write_text(
                "\n".join(
                    [
                        "MODEL 1",
                        "ATOM      1  C   UNL     1       1.000   1.000   1.000  1.00  0.00     0.000 C",
                        "ENDMDL",
                        "MODEL 2",
                        "ATOM      1  C   UNL     1       2.000   2.000   2.000  1.00  0.00     0.000 C",
                        "ENDMDL",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                validate_ligand_pdbqt(ligand_file)

    def test_validate_ligand_pdbqt_rejects_disconnected_components(self) -> None:
        """Disconnected ligand fragments should be blocked before Vina can dock them separately."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ligand_file = Path(tmpdir) / "fragmented_ligand.pdbqt"
            ligand_file.write_text(
                "\n".join(
                    [
                        "ROOT",
                        "ATOM      1  C   UNL     1       1.000   1.000   1.000  1.00  0.00     0.000 C",
                        "ATOM      2  C   UNL     1      20.000  20.000  20.000  1.00  0.00     0.000 C",
                        "ENDROOT",
                        "TORSDOF 0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                validate_ligand_pdbqt(ligand_file)


if __name__ == "__main__":
    unittest.main()
