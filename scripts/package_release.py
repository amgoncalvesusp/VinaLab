# -*- coding: utf-8 -*-
"""Package VinaLab release artifacts for the current operating system."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
import zipfile


APP_NAME = "VinaLab"
DEB_PACKAGE_NAME = "vinalab"
LINUX_ARCH = "amd64"
LINUX_GNINA_PATH = Path("tools/gnina/gnina")
LINUX_DEB_DEPENDS = (
    "autodock-vina, libc6, libstdc++6, libgcc-s1, zlib1g, libgl1, libegl1, "
    "libxkbcommon-x11-0, libxcb-cursor0, libxcb-icccm4, libxcb-image0, "
    "libxcb-keysyms1, libxcb-randr0, libxcb-render-util0, libxcb-shape0, "
    "libxcb-xinerama0, libxcb-xfixes0, libnss3, libxcomposite1, "
    "libxdamage1, libxrandr2, libgbm1, libasound2 | libasound2t64, xdg-utils"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Package VinaLab release artifacts.")
    parser.add_argument("--version", default=Path("VERSION").read_text(encoding="utf-8").strip())
    parser.add_argument("--dist-dir", default="dist")
    parser.add_argument("--output-dir", default="artifacts")
    args = parser.parse_args()

    dist_dir = Path(args.dist_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    system = platform.system().lower()
    if system == "windows":
        artifacts = package_windows(args.version, dist_dir, output_dir)
    elif system == "darwin":
        artifacts = [package_unix(args.version, dist_dir, output_dir, "macos")]
    elif system == "linux":
        artifacts = package_linux(args.version, dist_dir, output_dir)
    else:
        raise SystemExit(f"Sistema operacional não suportado para empacotamento: {platform.system()}")

    checksum_path = output_dir / f"SHA256SUMS-{system}.txt"
    checksum_path.write_text("\n".join(checksum_lines(artifacts)) + "\n", encoding="ascii")
    return 0


def package_windows(version: str, dist_dir: Path, output_dir: Path) -> list[Path]:
    exe_path = dist_dir / f"{APP_NAME}.exe"
    require_file(exe_path)

    portable = output_dir / f"{APP_NAME}-{version}-windows-x64-portable.zip"
    installer = output_dir / f"{APP_NAME}-{version}-windows-x64-installer.zip"
    setup = output_dir / f"{APP_NAME}-{version}-windows-x64-setup.exe"

    write_zip(
        portable,
        [
            (exe_path, f"{APP_NAME}.exe"),
            (Path("README.md"), "README.md"),
            (release_notes_path(version), f"RELEASE_NOTES_{version}.md"),
            (Path("VERSION"), "VERSION"),
        ],
    )
    artifacts = [portable]
    if setup.exists():
        artifacts.append(setup)
    else:
        write_zip(
            installer,
            [
                (exe_path, f"{APP_NAME}.exe"),
                (
                    Path("packaging/windows/Instalar_VinaLab.bat"),
                    "Instalar_VinaLab.bat",
                ),
                (Path("packaging/windows/install_windows.ps1"), "install_windows.ps1"),
                (Path("README.md"), "README.md"),
                (release_notes_path(version), f"RELEASE_NOTES_{version}.md"),
                (Path("VERSION"), "VERSION"),
            ],
        )
        artifacts.append(installer)
    return artifacts


def package_unix(version: str, dist_dir: Path, output_dir: Path, target: str) -> Path:
    executable = dist_dir / APP_NAME
    require_file(executable)
    archive = output_dir / f"{APP_NAME}-{version}-{target}-x64.tar.gz"
    entries = [
        (executable, APP_NAME),
        (Path("README.md"), "README.md"),
        (release_notes_path(version), f"RELEASE_NOTES_{version}.md"),
        (Path("VERSION"), "VERSION"),
    ]
    if target == "linux":
        entries.append((Path("packaging/linux/vinalab.desktop"), "vinalab.desktop"))
        entries.append((Path("packaging/linux/run_vinalab.sh"), "run_vinalab.sh"))
        gnina = optional_linux_gnina_path()
        if gnina is not None:
            entries.append((gnina, "tools/gnina/gnina"))
    with tarfile.open(archive, "w:gz") as handle:
        for source, arcname in entries:
            require_file(source)
            info = handle.gettarinfo(str(source), arcname=arcname)
            if source == executable or arcname in {
                "tools/gnina/gnina",
                "run_vinalab.sh",
            }:
                info.mode = 0o755
            with source.open("rb") as file_handle:
                handle.addfile(info, file_handle)
    return archive


def package_linux(version: str, dist_dir: Path, output_dir: Path) -> list[Path]:
    """Return Linux portable and Ubuntu installer artifacts."""
    executable = dist_dir / APP_NAME
    require_file(executable)
    return [
        package_unix(version, dist_dir, output_dir, "linux"),
        package_linux_deb(version, executable, output_dir),
    ]


def package_linux_deb(version: str, executable: Path, output_dir: Path) -> Path:
    """Build an Ubuntu-compatible Debian package using dpkg-deb."""
    dpkg_deb = shutil.which("dpkg-deb")
    if dpkg_deb is None:
        raise FileNotFoundError(
            "dpkg-deb not found; build the Linux installer on Ubuntu/Debian."
        )
    deb_path = output_dir / f"{APP_NAME}-{version}-ubuntu-x64.deb"
    if deb_path.exists():
        deb_path.unlink()
    with tempfile.TemporaryDirectory(prefix="vinalab-deb-") as tmpdir:
        package_root = Path(tmpdir) / DEB_PACKAGE_NAME
        prepare_linux_deb_tree(version, executable, package_root)
        subprocess.run(
            [
                dpkg_deb,
                "--build",
                "--root-owner-group",
                str(package_root),
                str(deb_path),
            ],
            check=True,
        )
    return deb_path


def prepare_linux_deb_tree(
    version: str,
    executable: Path,
    package_root: Path,
    include_gnina: bool = True,
    gnina_path: Path | None = None,
) -> None:
    """Create the Debian package filesystem tree without invoking dpkg-deb."""
    require_file(executable)
    app_dir = package_root / "opt" / DEB_PACKAGE_NAME
    bin_dir = package_root / "usr" / "bin"
    apps_dir = package_root / "usr" / "share" / "applications"
    icon_dir = package_root / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps"
    doc_dir = package_root / "usr" / "share" / "doc" / DEB_PACKAGE_NAME
    control_dir = package_root / "DEBIAN"

    for directory in (app_dir, bin_dir, apps_dir, icon_dir, doc_dir, control_dir):
        directory.mkdir(parents=True, exist_ok=True)

    shutil.copy2(executable, app_dir / APP_NAME)
    (app_dir / APP_NAME).chmod(0o755)
    shutil.copy2(Path("README.md"), doc_dir / "README.md")
    shutil.copy2(release_notes_path(version), doc_dir / f"RELEASE_NOTES_{version}.md")
    shutil.copy2(Path("LICENSE"), doc_dir / "copyright")
    shutil.copy2(Path("packaging/linux/vinalab.desktop"), apps_dir / "vinalab.desktop")
    shutil.copy2(Path("ui/icon.png"), icon_dir / "vinalab.png")
    if include_gnina:
        install_linux_gnina(app_dir, gnina_path)

    launcher = bin_dir / "vinalab"
    launcher.write_text(
        linux_installed_launcher_script("/opt/vinalab"),
        encoding="ascii",
    )
    launcher.chmod(0o755)

    (control_dir / "control").write_text(
        linux_deb_control(version, package_root),
        encoding="utf-8",
    )


def linux_deb_control(version: str, package_root: Path) -> str:
    """Return Debian control metadata for the Ubuntu installer."""
    depends_parts = LINUX_DEB_DEPENDS.split(", ")
    depends = depends_parts[0] + "".join(f",\n {part}" for part in depends_parts[1:])
    installed_size = max(1, package_installed_size_kb(package_root))
    return (
        f"Package: {DEB_PACKAGE_NAME}\n"
        f"Version: {version}\n"
        "Section: science\n"
        "Priority: optional\n"
        f"Architecture: {LINUX_ARCH}\n"
        "Maintainer: Adriano Marques Goncalves <adriano@example.invalid>\n"
        f"Installed-Size: {installed_size}\n"
        f"Depends: {depends}\n"
        "Description: Desktop interface for AutoDock Vina and GNINA molecular docking\n"
        " VinaLab helps prepare PDBQT inputs, run Vina or GNINA CNN docking jobs,\n"
        " inspect results, visualize poses, and generate reports.\n"
    )


def linux_installed_launcher_script(app_root: str) -> str:
    """Return the installed Linux launcher with native runtime paths."""
    return f"""#!/usr/bin/env sh
APP_ROOT="{app_root}"
export QTWEBENGINE_DISABLE_SANDBOX="${{QTWEBENGINE_DISABLE_SANDBOX:-1}}"
if [ -z "${{QTWEBENGINE_CHROMIUM_FLAGS:-}}" ]; then
  export QTWEBENGINE_CHROMIUM_FLAGS="--single-process --no-sandbox --disable-gpu"
fi
export PATH="$APP_ROOT/tools/gnina:$APP_ROOT/tools/vina:$APP_ROOT/openbabel/bin:$APP_ROOT/openbabel:${{PATH:-}}"
export LD_LIBRARY_PATH="$APP_ROOT:$APP_ROOT/tools/gnina:$APP_ROOT/tools/vina:$APP_ROOT/openbabel/lib:$APP_ROOT/openbabel/bin:$APP_ROOT/openbabel:${{LD_LIBRARY_PATH:-}}"
cd "$APP_ROOT"
exec "$APP_ROOT/VinaLab" "$@"
"""


def optional_linux_gnina_path() -> Path | None:
    """Return the optional bundled Linux GNINA CLI when available."""
    if LINUX_GNINA_PATH.exists() and LINUX_GNINA_PATH.is_file():
        return LINUX_GNINA_PATH
    return None


def install_linux_gnina(app_dir: Path, gnina_path: Path | None = None) -> None:
    """Install the optional GNINA scoring executable beside the Linux app."""
    source = gnina_path or optional_linux_gnina_path()
    if source is None:
        return
    require_file(source)
    destination = app_dir / "tools" / "gnina" / "gnina"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    destination.chmod(0o755)


def package_installed_size_kb(package_root: Path) -> int:
    """Return the installed size expected by Debian control files."""
    total = 0
    for path in package_root.rglob("*"):
        if path.is_file():
            total += path.stat().st_size
    return (total + 1023) // 1024


def write_zip(destination: Path, entries: list[tuple[Path, str]]) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as handle:
        for source, arcname in entries:
            require_file(source)
            handle.write(source, arcname)


def checksum_lines(paths: list[Path]) -> list[str]:
    lines = []
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        lines.append(f"{digest}  {path.name}")
    return lines


def release_notes_path(version: str) -> Path:
    return Path(f"RELEASE_NOTES_{version}.md")


def require_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Arquivo obrigatório ausente: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
