# -*- coding: utf-8 -*-
"""Unit tests for release artifact packaging helpers."""

from pathlib import Path
import os
import tempfile
import unittest
from unittest import mock

from scripts.package_release import (
    macos_architecture,
    prepare_linux_deb_tree,
    require_macos_app_bundle,
)


class PackageReleaseTests(unittest.TestCase):
    """Cover installer layout without requiring platform-specific build tools."""

    def test_macos_architecture_uses_distribution_labels(self) -> None:
        with mock.patch("scripts.package_release.platform.machine", return_value="arm64"):
            self.assertEqual(macos_architecture(), "arm64")
        with mock.patch("scripts.package_release.platform.machine", return_value="x86_64"):
            self.assertEqual(macos_architecture(), "x64")

    @unittest.skipUnless(os.name == "posix", "Mac executable modes require POSIX")
    def test_macos_bundle_requires_info_plist_and_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle = Path(tmpdir) / "VinaLab.app"
            contents = bundle / "Contents"
            executable = contents / "MacOS" / "VinaLab"
            executable.parent.mkdir(parents=True)
            (contents / "Info.plist").write_text("plist", encoding="utf-8")
            executable.write_bytes(b"fake executable")
            executable.chmod(0o755)

            require_macos_app_bundle(bundle)

            (contents / "Info.plist").unlink()
            with self.assertRaises(FileNotFoundError):
                require_macos_app_bundle(bundle)

    def test_windows_pyinstaller_spec_has_no_gnina_bundle(self) -> None:
        """Windows PyInstaller builds should not include GNINA or libtorch DLLs."""
        spec_text = Path("VinaGUI.spec").read_text(encoding="utf-8")

        self.assertNotIn('("tools/gnina", "tools/gnina")', spec_text)
        self.assertNotIn("collect_windows_gnina_torch_dlls", spec_text)
        self.assertNotIn("torch_cuda.dll", spec_text)
        self.assertNotIn("torch_cpu.dll", spec_text)
        self.assertNotIn("c10.dll", spec_text)
        self.assertNotIn('("pontuacao", "pontuacao")', spec_text)

    def test_macos_spec_excludes_prody_linux_hpb_binary(self) -> None:
        spec_text = Path("VinaGUI.spec").read_text(encoding="utf-8")

        self.assertIn('sys.platform == "darwin" and _package == "prody"', spec_text)
        self.assertIn('Path(entry[0]).name != "hpb.so"', spec_text)

    def test_prepare_linux_deb_tree_installs_launcher_desktop_and_icon(self) -> None:
        """The Ubuntu installer tree should expose a runnable system command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            executable = tmp_path / "VinaLab"
            executable.write_bytes(b"fake executable")
            package_root = tmp_path / "pkg"

            prepare_linux_deb_tree("0.0.7", executable, package_root)

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
            launcher_text = launcher.read_text(encoding="ascii")
            self.assertIn('APP_ROOT="/opt/vinalab"', launcher_text)
            self.assertIn('exec "$APP_ROOT/VinaLab"', launcher_text)
            self.assertIn("QTWEBENGINE_DISABLE_SANDBOX", launcher_text)
            self.assertIn("LD_LIBRARY_PATH", launcher_text)
            self.assertNotIn("tools/gnina", launcher_text)

            control_text = control.read_text(encoding="utf-8")
            self.assertTrue(control_text.startswith("Package: vinalab\n"))
            self.assertIn("Package: vinalab", control_text)
            self.assertIn("Version: 0.0.7", control_text)
            self.assertIn("Architecture: amd64", control_text)
            self.assertIn("autodock-vina", control_text)
            self.assertIn("openbabel", control_text)
            self.assertIn("libxkbcommon-x11-0", control_text)
            self.assertIn("Depends: autodock-vina,\n openbabel,\n libc6,", control_text)

    def test_prepare_linux_deb_tree_has_no_gnina_payload(self) -> None:
        """VinaLab Light should not ship GNINA in the Ubuntu installer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            executable = tmp_path / "VinaLab"
            executable.write_bytes(b"fake executable")
            package_root = tmp_path / "pkg"

            prepare_linux_deb_tree("0.0.7", executable, package_root)

            installed_gnina = package_root / "opt" / "vinalab" / "tools" / "gnina"
            self.assertFalse(installed_gnina.exists())


if __name__ == "__main__":
    unittest.main()
