"""Open Babel format plugins are dlopen modules, not Python extensions."""

from pathlib import Path


def plugin_binaries(package_dir: Path) -> list[tuple[str, str]]:
    # PyInstaller's default dynamic-library patterns match lib*.so, but not
    # pdbformat.so / mol2format.so. Keep the layout used by openbabel.__init__.
    plugins = sorted(set(package_dir.rglob("*.obf")) | set((package_dir / "lib" / "openbabel").rglob("*.so")))
    return [(str(plugin), plugin.parent.relative_to(package_dir.parent).as_posix()) for plugin in plugins]
