"""Bundle native Open Babel, not its pip Python console-script launcher."""

from unittest.mock import patch
from core import native_tools


def test_package_cli_precedes_python_launcher(tmp_path):
    package = tmp_path / "openbabel"
    binary = package / "bin" / ("obabel.exe" if native_tools.sys.platform.startswith("win") else "obabel")
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"native")
    with patch.object(native_tools, "_openbabel_roots", return_value=[package]), \
         patch.object(native_tools, "find_native_executable", return_value=tmp_path / "launcher"):
        assert native_tools.find_obabel_executable() == binary


def test_linux_plugins_keep_wheel_layout(tmp_path):
    from scripts.openbabel_bundle import plugin_binaries
    package = tmp_path / "openbabel"
    plugin = package / "lib" / "openbabel" / "3.1.0" / "pdbqtformat.so"
    plugin.parent.mkdir(parents=True)
    plugin.write_bytes(b"plugin")
    assert plugin_binaries(package) == [(str(plugin), "openbabel/lib/openbabel/3.1.0")]
