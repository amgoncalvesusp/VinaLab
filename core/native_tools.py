# -*- coding: utf-8 -*-
"""Discovery and launch helpers for bundled native command-line tools."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import struct
import sys

NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0


def find_native_executable(
    names: Sequence[str], tool_subdir: str | None = None
) -> Path | None:
    """Return a native executable from the app, PyInstaller bundle, or PATH."""
    for candidate in iter_native_executable_candidates(names, tool_subdir):
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def find_obabel_executable() -> Path | None:
    """Return the Open Babel CLI bundled with the app or available on PATH."""
    names = ("obabel.exe", "obabel") if sys.platform.startswith("win") else ("obabel",)
    return find_native_executable(names, "openbabel")


def find_gnina_executable() -> Path | None:
    """Return GNINA only on Linux/WSL when the executable can start."""
    if sys.platform.startswith("win"):
        return None
    names = ("gnina.exe", "gnina") if sys.platform.startswith("win") else ("gnina",)
    for candidate in iter_native_executable_candidates(names, "gnina"):
        if candidate.exists() and candidate.is_file() and native_tool_starts(candidate):
            return candidate
    return None


def find_smina_executable() -> Path | None:
    """Return a bundled or PATH smina CLI when its direct DLLs are resolvable."""
    names = ("smina.exe", "smina") if sys.platform.startswith("win") else ("smina",)
    for candidate in iter_native_executable_candidates(names, "smina"):
        if candidate.exists() and candidate.is_file() and not native_tool_missing_dlls(candidate):
            return candidate
    return None


def find_vina_executable() -> Path | None:
    """Return an AutoDock Vina CLI bundled with the app or available on PATH."""
    names = (
        ("vina_1.2.7_win.exe", "vina.exe", "vina")
        if sys.platform.startswith("win")
        else ("vina",)
    )
    return find_native_executable(names, "vina")


def native_tool_starts(
    tool_path: Path, args: Sequence[str] = ("--help",), timeout: int = 10
) -> bool:
    """Return True when a native executable can start without missing-DLL errors."""
    if native_tool_missing_dlls(tool_path):
        return False
    try:
        result = subprocess.run(
            [str(tool_path), *args],
            cwd=tool_path.resolve().parent,
            env=native_tool_env(tool_path),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            creationflags=NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def native_tool_missing_dlls(
    tool_path: Path, base_env: Mapping[str, str] | None = None
) -> tuple[str, ...]:
    """Return direct Windows DLL imports that are not resolvable before launch.

    Missing imports such as torch_cuda.dll make Windows show a modal system error
    before Python can capture stderr. A static PE import check lets VinaLab mark
    that tool unavailable without opening the OS dialog.
    """
    if not sys.platform.startswith("win"):
        return ()
    imported = _pe_imported_dlls(tool_path)
    if not imported:
        return ()
    search_dirs = _windows_dll_search_dirs(tool_path, base_env)
    missing = []
    for dll_name in imported:
        normalized = dll_name.lower()
        if normalized.startswith(("api-ms-win-", "ext-ms-win-")):
            continue
        if not any((directory / dll_name).is_file() for directory in search_dirs):
            missing.append(dll_name)
    return tuple(sorted(set(missing), key=str.lower))


def native_tool_env(
    tool_path: Path, base_env: Mapping[str, str] | None = None
) -> dict[str, str]:
    """Return an environment that lets bundled native tools find local DLLs/plugins."""
    env = dict(os.environ if base_env is None else base_env)
    tool_dir = tool_path.resolve().parent
    extra_paths = [tool_dir]
    bundle_dir = Path(getattr(sys, "_MEIPASS", ""))
    if bundle_dir.exists():
        extra_paths.append(bundle_dir)
    extra_paths.extend(_openbabel_library_paths())
    extra_paths.extend(_torch_library_paths())
    existing_path = env.get("PATH", "")
    if existing_path:
        path_entries = [str(path) for path in _dedupe_existing_paths(extra_paths)]
        path_entries.append(existing_path)
    else:
        path_entries = [str(path) for path in _dedupe_existing_paths(extra_paths)]
    env["PATH"] = os.pathsep.join(path_entries)

    openbabel_plugins = _first_plugin_dir(_openbabel_plugin_candidates(tool_dir))
    if openbabel_plugins is not None:
        env["BABEL_LIBDIR"] = str(openbabel_plugins)
    openbabel_data = _first_existing_path(*_openbabel_data_candidates(tool_dir))
    if openbabel_data is not None:
        env["BABEL_DATADIR"] = str(openbabel_data)
    if not sys.platform.startswith("win"):
        _prepend_env_path(env, "LD_LIBRARY_PATH", *_openbabel_library_paths())
    return env


def iter_native_executable_candidates(
    names: Sequence[str], tool_subdir: str | None
) -> list[Path]:
    """Return app/bundle candidates followed by PATH candidates."""
    candidates = _candidate_paths(names, tool_subdir)
    for name in names:
        path_value = shutil.which(name)
        if path_value:
            candidates.append(Path(path_value))
    return candidates


def _candidate_paths(names: Sequence[str], tool_subdir: str | None) -> list[Path]:
    project_root = Path(__file__).resolve().parents[1]
    bundle_dir = Path(getattr(sys, "_MEIPASS", project_root))
    executable_dir = Path(sys.executable).resolve().parent
    roots = [
        executable_dir,
        bundle_dir,
        bundle_dir / "Scripts",
        Path.cwd(),
        project_root,
    ]
    candidates: list[Path] = []
    for root in roots:
        for name in names:
            candidates.append(root / name)
        if tool_subdir:
            for name in names:
                candidates.append(root / "tools" / tool_subdir / name)
                candidates.append(root / tool_subdir / name)
                candidates.append(root / tool_subdir / "bin" / name)
                candidates.append(root / "Lib" / "site-packages" / tool_subdir / name)
                candidates.append(
                    root / "Lib" / "site-packages" / tool_subdir / "bin" / name
                )
                candidates.append(
                    root.parent / "Lib" / "site-packages" / tool_subdir / name
                )
                candidates.append(
                    root.parent / "Lib" / "site-packages" / tool_subdir / "bin" / name
                )
    return candidates


def _pe_imported_dlls(path: Path) -> tuple[str, ...]:
    """Return direct DLL imports from a PE executable without loading it."""
    try:
        data = path.read_bytes()
    except OSError:
        return ()
    try:
        if data[:2] != b"MZ":
            return ()
        pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe_offset : pe_offset + 4] != b"PE\0\0":
            return ()
        number_of_sections = struct.unpack_from("<H", data, pe_offset + 6)[0]
        optional_header_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
        optional_header = pe_offset + 24
        magic = struct.unpack_from("<H", data, optional_header)[0]
        data_directory = optional_header + (112 if magic == 0x20B else 96)
        if magic not in {0x10B, 0x20B}:
            return ()
        import_rva = struct.unpack_from("<I", data, data_directory + 8)[0]
        if import_rva == 0:
            return ()
        sections_offset = optional_header + optional_header_size
        sections = []
        for index in range(number_of_sections):
            section_offset = sections_offset + index * 40
            virtual_size = struct.unpack_from("<I", data, section_offset + 8)[0]
            virtual_address = struct.unpack_from("<I", data, section_offset + 12)[0]
            raw_size = struct.unpack_from("<I", data, section_offset + 16)[0]
            raw_pointer = struct.unpack_from("<I", data, section_offset + 20)[0]
            sections.append(
                (virtual_address, max(virtual_size, raw_size), raw_pointer)
            )

        def rva_to_offset(rva: int) -> int:
            for virtual_address, size, raw_pointer in sections:
                if virtual_address <= rva < virtual_address + size:
                    return raw_pointer + (rva - virtual_address)
            raise ValueError

        def read_c_string(offset: int) -> str:
            end = data.index(b"\0", offset)
            return data[offset:end].decode("ascii", errors="replace")

        imports = []
        descriptor_offset = rva_to_offset(import_rva)
        while True:
            descriptor = struct.unpack_from("<IIIII", data, descriptor_offset)
            if not any(descriptor):
                break
            name_rva = descriptor[3]
            imports.append(read_c_string(rva_to_offset(name_rva)))
            descriptor_offset += 20
        return tuple(imports)
    except (IndexError, struct.error, ValueError):
        return ()


def _windows_dll_search_dirs(
    tool_path: Path, base_env: Mapping[str, str] | None = None
) -> list[Path]:
    env = native_tool_env(tool_path, base_env)
    directories = [tool_path.resolve().parent]
    system_root = Path(env.get("SystemRoot") or os.environ.get("SystemRoot", r"C:\Windows"))
    directories.extend([system_root / "System32", system_root / "System", system_root])
    directories.extend(
        Path(entry)
        for entry in env.get("PATH", "").split(os.pathsep)
        if entry.strip()
    )
    return _dedupe_existing_paths(directories)


def _openbabel_roots() -> list[Path]:
    project_root = Path(__file__).resolve().parents[1]
    bundle_dir = Path(getattr(sys, "_MEIPASS", project_root))
    executable_dir = Path(sys.executable).resolve().parent
    roots = [
        bundle_dir / "openbabel",
        executable_dir / "openbabel",
        executable_dir / "Lib" / "site-packages" / "openbabel",
        executable_dir.parent / "Lib" / "site-packages" / "openbabel",
        executable_dir.parent
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
        / "openbabel",
        project_root / ".venv" / "Lib" / "site-packages" / "openbabel",
        project_root
        / ".venv"
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
        / "openbabel",
        project_root / "openbabel",
        project_root / "vendor" / "openbabel",
    ]
    if not sys.platform.startswith("win"):
        roots.extend(
            [
                Path("/usr/lib/openbabel"),
                Path("/usr/lib/x86_64-linux-gnu/openbabel"),
                Path("/usr/local/lib/openbabel"),
                Path("/usr/share/openbabel"),
                Path("/usr/local/share/openbabel"),
            ]
        )
    spec = importlib.util.find_spec("openbabel")
    if spec is not None and spec.origin:
        roots.append(Path(spec.origin).resolve().parent)
    return _dedupe_existing_paths(roots)


def _openbabel_plugin_candidates(tool_dir: Path) -> list[Path]:
    candidates = [tool_dir]
    for root in _openbabel_roots():
        candidates.extend([root / "plugins", root / "bin", root])
    return candidates


def _openbabel_data_candidates(tool_dir: Path) -> list[Path]:
    candidates = [tool_dir / "data"]
    for root in _openbabel_roots():
        share_openbabel = root / "share" / "openbabel"
        candidates.extend(_child_directories(share_openbabel))
        candidates.extend(
            [
                root / "data",
                root / "bin" / "data",
                share_openbabel,
                root / "share",
            ]
        )
    if not sys.platform.startswith("win"):
        candidates.extend(_child_directories(Path("/usr/share/openbabel")))
        candidates.extend(_child_directories(Path("/usr/local/share/openbabel")))
        candidates.extend(
            [
                Path("/usr/share/openbabel"),
                Path("/usr/local/share/openbabel"),
            ]
        )
    return candidates


def _openbabel_library_paths() -> list[Path]:
    paths = []
    for root in _openbabel_roots():
        paths.extend([root / "bin", root / "lib", root])
    return _dedupe_existing_paths(paths)


def _torch_library_paths() -> list[Path]:
    project_root = Path(__file__).resolve().parents[1]
    bundle_dir = Path(getattr(sys, "_MEIPASS", project_root))
    executable_dir = Path(sys.executable).resolve().parent
    candidates = [
        bundle_dir / "torch" / "lib",
        bundle_dir / "torch",
        executable_dir / "torch" / "lib",
        executable_dir.parent / "Lib" / "site-packages" / "torch" / "lib",
        project_root / ".venv" / "Lib" / "site-packages" / "torch" / "lib",
    ]
    return _dedupe_existing_paths(candidates)


def _first_existing_path(*candidates: Path) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _child_directories(path: Path) -> list[Path]:
    if not path.exists() or not path.is_dir():
        return []
    return sorted(child for child in path.iterdir() if child.is_dir())


def _first_plugin_dir(candidates: Sequence[Path]) -> Path | None:
    for candidate in candidates:
        if not candidate.exists():
            continue
        if _contains_openbabel_plugin(candidate):
            return candidate
        nested = next(_iter_openbabel_plugin_files(candidate), None)
        if nested is not None:
            return nested.parent
    return None


def _contains_openbabel_plugin(directory: Path) -> bool:
    return any(_iter_openbabel_plugin_files(directory, recursive=False))


def _iter_openbabel_plugin_files(path: Path, recursive: bool = True):
    patterns = ("*.obf",)
    if not sys.platform.startswith("win"):
        patterns = (*patterns, "*format.so", "plugin_*.so")
    for pattern in patterns:
        yield from (path.rglob(pattern) if recursive else path.glob(pattern))


def _dedupe_existing_paths(paths: Sequence[Path]) -> list[Path]:
    seen: set[str] = set()
    existing = []
    for path in paths:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        key = str(resolved).lower() if sys.platform.startswith("win") else str(resolved)
        if key in seen or not resolved.exists():
            continue
        seen.add(key)
        existing.append(resolved)
    return existing


def _prepend_env_path(env: dict[str, str], key: str, *paths: Path) -> None:
    path_entries = [str(path) for path in _dedupe_existing_paths(paths)]
    if not path_entries:
        return
    existing = env.get(key, "")
    env[key] = os.pathsep.join([*path_entries, existing]) if existing else os.pathsep.join(path_entries)
