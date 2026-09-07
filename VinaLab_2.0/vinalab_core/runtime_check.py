"""Import-only runtime diagnostics shared by installed and frozen entry points."""

import json
import sys
from importlib import import_module
from pathlib import Path

REQUIRED_MODULES = (
    "PySide6.QtWidgets", "PySide6.QtWebEngineWidgets", "PySide6.QtWebChannel",
    "rdkit.Chem", "meeko", "meeko.cli.mk_prepare_receptor", "gemmi",
    "openbabel.openbabel", "scipy", "numpy",
)


def check_dependencies(importer=import_module):
    failures = []
    for name in REQUIRED_MODULES:
        try:
            importer(name)
        except Exception as exc:  # noqa: BLE001 - report every third-party import failure
            failures.append(f"{name}: {exc}")
    if failures:
        raise RuntimeError("Required build dependencies unavailable:\n" + "\n".join(failures))


def main(argv=None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    error = ""
    try:
        check_dependencies()
    except RuntimeError as exc:
        error = str(exc)
        if sys.stderr is not None:
            print(error, file=sys.stderr)
    if "--runtime-check-output" in arguments:
        try:
            path = Path(arguments[arguments.index("--runtime-check-output") + 1])
            with path.open("x", encoding="utf-8") as stream:
                json.dump({"ok": not error, "error": error, "modules": REQUIRED_MODULES}, stream, indent=2)
        except (OSError, IndexError):
            return 2
    if not error and sys.stdout is not None:
        print("Mandatory runtime dependencies available.")
    return 1 if error else 0


if __name__ == "__main__":
    sys.exit(main())
