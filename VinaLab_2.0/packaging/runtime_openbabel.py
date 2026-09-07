"""Configure collected Open Babel plugins/data before any conversion is attempted."""

import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    root = Path(sys._MEIPASS)
    binary_directory = root / "openbabel" / "bin"
    sibling_libraries = root / "openbabel_wheel.libs"
    if os.name == "nt":
        sys._vinalab_dll_handles = tuple(
            os.add_dll_directory(str(path))
            for path in (binary_directory, sibling_libraries) if path.is_dir()
        )
    import openbabel  # noqa: F401 - initialize wheel paths before overriding them

    # The wheel initializer sets build-time lib/share paths; override after import.
    if os.name == "nt":
        os.environ["BABEL_LIBDIR"] = str(binary_directory)
        os.environ["BABEL_DATADIR"] = str(binary_directory / "data")
        os.environ["BABEL_DATA_DIR"] = str(binary_directory / "data")
