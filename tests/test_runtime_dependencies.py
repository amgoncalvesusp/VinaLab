# -*- coding: utf-8 -*-
"""Runtime dependency checker tests."""

from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import check_runtime_dependencies


class RuntimeDependencyCheckTests(unittest.TestCase):
    """Cover packaged-runtime dependency validation without real wheels."""

    def test_openbabel_runtime_complete(self) -> None:
        """The checker should require CLI, plugins, data, wheel DLLs, and Vina CLI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            obabel = root / "obabel.exe"
            vina = root / "vina_1.2.7_win.exe"
            plugins = root / "openbabel" / "bin"
            data = plugins / "data"
            libs = root / "openbabel_wheel.libs"
            for path in (plugins, data, libs):
                path.mkdir(parents=True)
            obabel.write_text("", encoding="utf-8")
            vina.write_text("", encoding="utf-8")
            (plugins / "formats_common.obf").write_text("", encoding="utf-8")

            with (
                mock.patch.object(
                    check_runtime_dependencies.importlib,
                    "import_module",
                    return_value=object(),
                ),
                mock.patch.object(
                    check_runtime_dependencies,
                    "find_obabel_executable",
                    return_value=obabel,
                ),
                mock.patch.object(
                    check_runtime_dependencies,
                    "find_vina_executable",
                    return_value=vina,
                ),
                mock.patch.object(
                    check_runtime_dependencies,
                    "native_tool_env",
                    return_value={
                        "BABEL_LIBDIR": str(plugins),
                        "BABEL_DATADIR": str(data),
                    },
                ),
                mock.patch.object(
                    check_runtime_dependencies,
                    "_openbabel_wheel_libs",
                    return_value=libs,
                ),
                mock.patch.object(check_runtime_dependencies.sys, "platform", "win32"),
            ):
                self.assertEqual(check_runtime_dependencies.main(), 0)

    def test_openbabel_runtime_missing_plugins_fails(self) -> None:
        """Missing .obf plugins should fail the packaged runtime check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            obabel = root / "obabel.exe"
            vina = root / "vina_1.2.7_win.exe"
            plugins = root / "openbabel" / "bin"
            data = plugins / "data"
            libs = root / "openbabel_wheel.libs"
            for path in (plugins, data, libs):
                path.mkdir(parents=True)
            obabel.write_text("", encoding="utf-8")
            vina.write_text("", encoding="utf-8")

            with (
                mock.patch.object(
                    check_runtime_dependencies.importlib,
                    "import_module",
                    return_value=object(),
                ),
                mock.patch.object(
                    check_runtime_dependencies,
                    "find_obabel_executable",
                    return_value=obabel,
                ),
                mock.patch.object(
                    check_runtime_dependencies,
                    "find_vina_executable",
                    return_value=vina,
                ),
                mock.patch.object(
                    check_runtime_dependencies,
                    "native_tool_env",
                    return_value={
                        "BABEL_LIBDIR": str(plugins),
                        "BABEL_DATADIR": str(data),
                    },
                ),
                mock.patch.object(
                    check_runtime_dependencies,
                    "_openbabel_wheel_libs",
                    return_value=libs,
                ),
                mock.patch.object(check_runtime_dependencies.sys, "platform", "win32"),
            ):
                self.assertEqual(check_runtime_dependencies.main(), 1)

    def test_openbabel_runtime_accepts_linux_so_plugins(self) -> None:
        """Linux Open Babel packages expose plugins as shared objects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            obabel = root / "obabel"
            vina = root / "vina"
            plugins = root / "openbabel" / "3.1.1"
            data = root / "share" / "openbabel" / "3.1.1"
            for path in (plugins, data):
                path.mkdir(parents=True)
            obabel.write_text("", encoding="utf-8")
            vina.write_text("", encoding="utf-8")
            (plugins / "pdbqtformat.so").write_text("", encoding="utf-8")

            with (
                mock.patch.object(
                    check_runtime_dependencies.importlib,
                    "import_module",
                    return_value=object(),
                ),
                mock.patch.object(
                    check_runtime_dependencies,
                    "find_obabel_executable",
                    return_value=obabel,
                ),
                mock.patch.object(
                    check_runtime_dependencies,
                    "find_vina_executable",
                    return_value=vina,
                ),
                mock.patch.object(
                    check_runtime_dependencies,
                    "native_tool_env",
                    return_value={
                        "BABEL_LIBDIR": str(plugins),
                        "BABEL_DATADIR": str(data),
                    },
                ),
                mock.patch.object(check_runtime_dependencies.sys, "platform", "linux"),
            ):
                self.assertEqual(check_runtime_dependencies.main(), 0)


if __name__ == "__main__":
    unittest.main()
