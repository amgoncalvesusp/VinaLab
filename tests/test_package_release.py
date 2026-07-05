# -*- coding: utf-8 -*-
"""Unit tests for release artifact packaging helpers."""

from pathlib import Path
import tempfile
import unittest

from scripts.package_release import prepare_linux_deb_tree


class PackageReleaseTests(unittest.TestCase):
    """Cover installer layout without requiring platform-specific build tools."""

    def test_prepare_linux_deb_tree_installs_launcher_desktop_and_icon(self) -> None:
        """The Ubuntu installer tree should expose a runnable system command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            executable = tmp_path / "VinaLab"
            executable.write_bytes(b"fake executable")
            package_root = tmp_path / "pkg"

            prepare_linux_deb_tree("0.0.7", executable, package_root, include_gnina=False)

            installed_app = package_root / "opt" / "vinalab" / "VinaLab"
            launcher = package_root / "usr" / "bin" / "vinalab"
            desktop_entry = (
                package_root / "usr" / "share" / "applications" / "vinalab.desktop"
            )
            icon = (
                package_root
                / "usr"
                / "share"
                / "icons"
                / "hicolor"
                / "256x256"
                / "apps"
                / "vinalab.png"
            )
            control = package_root / "DEBIAN" / "control"

            self.assertTrue(installed_app.exists())
            self.assertTrue(launcher.exists())
            self.assertTrue(desktop_entry.exists())
            self.assertTrue(icon.exists())
            self.assertEqual(installed_app.read_bytes(), b"fake executable")
            self.assertIn("/opt/vinalab/VinaLab", launcher.read_text(encoding="ascii"))

            control_text = control.read_text(encoding="utf-8")
            self.assertTrue(control_text.startswith("Package: vinalab\n"))
            self.assertIn("Package: vinalab", control_text)
            self.assertIn("Version: 0.0.7", control_text)
            self.assertIn("Architecture: amd64", control_text)
            self.assertIn("autodock-vina", control_text)
            self.assertIn("libxkbcommon-x11-0", control_text)
            self.assertIn("Depends: autodock-vina,\n libc6,", control_text)

    def test_prepare_linux_deb_tree_installs_gnina_when_provided(self) -> None:
        """The Ubuntu installer should ship the Linux GNINA scoring executable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            executable = tmp_path / "VinaLab"
            executable.write_bytes(b"fake executable")
            gnina = tmp_path / "gnina"
            gnina.write_bytes(b"fake gnina")
            package_root = tmp_path / "pkg"

            prepare_linux_deb_tree(
                "0.0.7",
                executable,
                package_root,
                include_gnina=True,
                gnina_path=gnina,
            )

            installed_gnina = package_root / "opt" / "vinalab" / "tools" / "gnina" / "gnina"
            self.assertTrue(installed_gnina.exists())
            self.assertEqual(installed_gnina.read_bytes(), b"fake gnina")


if __name__ == "__main__":
    unittest.main()
