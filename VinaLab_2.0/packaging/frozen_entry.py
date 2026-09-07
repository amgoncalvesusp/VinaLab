"""Frozen launcher with a headless dependency smoke-check exit path."""

import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build_support import check_dependencies


def main():
    if "--check-dependencies" in sys.argv[1:]:
        try:
            check_dependencies()
        except RuntimeError as exc:
            # Windowed PyInstaller executables have no stderr; avoid a modal error.
            if sys.stderr is not None:
                print(str(exc), file=sys.stderr)
            return 1
        return 0
    from vinalab_ui.main import main as ui_main
    return ui_main(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
