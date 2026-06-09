# -*- coding: utf-8 -*-
"""Application entry point for VinaLab."""

from pathlib import Path
import subprocess
import traceback
import sys

NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0


def resource_path(relative_path: str) -> Path:
    """Return a resource path that works both from source and PyInstaller."""
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / relative_path


def main() -> int:
    """Launch the VinaLab desktop application."""
    try:
        from core.environment_manager import EnvironmentManager

        manager = EnvironmentManager()
        if getattr(sys, "frozen", False):
            manager.full_status_report()
            missing = []
            vina_status = {"ok": True}
        else:
            missing = manager.check_missing()
            vina_status = (
                manager.verify_autodock_vina() if not missing else {"ok": False}
            )
        if missing or not vina_status.get("ok"):
            launcher_path = Path(__file__).resolve().parent / "launcher.py"
            if launcher_path.exists():
                subprocess.Popen(
                    [str(sys.executable), str(launcher_path)],
                    cwd=launcher_path.parent,
                    creationflags=NO_WINDOW,
                )
                return 0
            missing_names = ", ".join(package["pip_name"] for package in missing)
            raise RuntimeError(
                "O ambiente do VinaLab está incompleto e launcher.py não foi encontrado. "
                f"Ausente: {missing_names or 'AutoDock Vina'}"
            )

        from PySide6.QtGui import QFont, QIcon
        from PySide6.QtWidgets import QApplication

        from core.responsive import ResponsiveManager
        from core.scrolling import WheelGuard
        from mainwindow import MainWindow

        app = QApplication(sys.argv)
        app.setApplicationName("VinaLab")
        app.setStartDragTime(500)
        app.setFont(QFont("Segoe UI", 9))

        # Keep a reference on the app so the guard is not garbage-collected.
        app._wheel_guard = WheelGuard()
        app.installEventFilter(app._wheel_guard)

        style_path = resource_path("ui/style.qss")
        if style_path.exists():
            app.setStyleSheet(style_path.read_text(encoding="utf-8"))
        icon_path = resource_path("ui/icon.ico")
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))

        window = MainWindow()
        ResponsiveManager.connect_screen_change(app, window)
        window.show()
        return app.exec()
    except Exception:  # noqa: BLE001 - write startup failures for non-console launches
        try:
            from core.environment_manager import EnvironmentManager

            logs_dir = EnvironmentManager().logs_dir
        except Exception:  # noqa: BLE001 - fallback for very early import failures
            logs_dir = Path(__file__).resolve().parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "error.log").write_text(traceback.format_exc(), encoding="utf-8")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
