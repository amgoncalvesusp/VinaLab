"""Desktop entry point for VinaLab 2.0."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication

    from vinalab_ui.mainwindow import MainWindow


def create_application(argv: Sequence[str] | None = None) -> tuple[QApplication, MainWindow]:
    """Create the reusable Qt application/window pair used by the desktop launcher and tests."""
    from PySide6.QtWidgets import QApplication

    from vinalab_ui.mainwindow import MainWindow

    application = QApplication.instance() or QApplication(list(argv or []))
    window = MainWindow()
    return application, window


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv if argv is None else argv)
    if "--smoke-test-ui" in arguments:
        from vinalab_ui.runtime_ui_smoke import main as smoke_test_ui

        return smoke_test_ui(arguments[arguments.index("--smoke-test-ui") + 1:])
    if "--check-runtime" in arguments:
        from vinalab_core.runtime_check import main as check_runtime

        return check_runtime(arguments)
    if "--smoke-test" in arguments:
        from vinalab_core.runtime_smoke import main as smoke_test

        return smoke_test(arguments[arguments.index("--smoke-test") + 1:])
    application, window = create_application(argv)
    window.show()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
