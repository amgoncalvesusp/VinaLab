"""Package VinaLab release artifacts for the current operating system."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import platform
import tarfile
import zipfile


APP_NAME = "VinaLab"


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
        artifacts = [package_unix(args.version, dist_dir, output_dir, "linux")]
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

    write_zip(
        portable,
        [
            (exe_path, f"{APP_NAME}.exe"),
            (Path("README.md"), "README.md"),
            (release_notes_path(version), f"RELEASE_NOTES_{version}.md"),
            (Path("VERSION"), "VERSION"),
        ],
    )
    write_zip(
        installer,
        [
            (exe_path, f"{APP_NAME}.exe"),
            (Path("packaging/windows/Instalar_VinaLab.bat"), "Instalar_VinaLab.bat"),
            (Path("packaging/windows/install_windows.ps1"), "install_windows.ps1"),
            (Path("README.md"), "README.md"),
            (release_notes_path(version), f"RELEASE_NOTES_{version}.md"),
            (Path("VERSION"), "VERSION"),
        ],
    )
    return [portable, installer]


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
    with tarfile.open(archive, "w:gz") as handle:
        for source, arcname in entries:
            require_file(source)
            info = handle.gettarinfo(str(source), arcname=arcname)
            if source == executable:
                info.mode = 0o755
            with source.open("rb") as file_handle:
                handle.addfile(info, file_handle)
    return archive


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
