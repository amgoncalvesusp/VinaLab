"""Desktop entry point for VinaLab 2.0."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from vinalab_ui.mainwindow import MainWindow


def create_application(argv: Sequence[str] | None = None) -> tuple[QApplication, MainWindow]:
    """Create the reusable Qt application/window pair used by the desktop launcher and tests."""
    application = QApplication.instance() or QApplication(list(argv or []))
    window = MainWindow()
    return application, window


def main(argv: Sequence[str] | None = None) -> int:
    application, window = create_application(argv)
    window.show()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
