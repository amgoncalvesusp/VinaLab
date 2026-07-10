"""Command-line entry point for VinaLab 2.0."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from vinalab_core.tools.tool_locator import ToolLocator


def main(argv: Sequence[str] | None = None) -> int:
    """Run a headless VinaLab command."""
    parser = argparse.ArgumentParser(prog="vinalab-cli", description="VinaLab 2.0 headless tools")
    subcommands = parser.add_subparsers(dest="command", required=True)
    diagnostics = subcommands.add_parser("diagnostics", help="report configured native tools")
    diagnostics.add_argument("--project-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args(argv)
    if arguments.command == "diagnostics":
        vina = ToolLocator(arguments.project_root).find("vina")
        print(f"Vina: {vina if vina else 'not found'}")
        return 0 if vina else 1
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
