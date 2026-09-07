"""Bounded, invisible full-window QA; writes evidence into a unique output folder."""

import argparse
import json
import math
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Timer
from time import monotonic
from uuid import uuid4


def _write(output, report):
    pending = output / "result.json.tmp"
    pending.write_text(json.dumps(report, indent=2), encoding="utf-8")
    pending.replace(output / "result.json")


def _run(output, timeout):
    # Import the existing viewer before QApplication; never import it in showEvent.
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from vinalab_ui.mainwindow import MainWindow

    if QApplication.instance() is not None:
        raise RuntimeError("UI smoke must run in a fresh process")
    app = QApplication(["vinalab-ui-smoke", "-platform", "offscreen"])
    if app.platformName() != "offscreen":
        raise RuntimeError("UI smoke requires the offscreen platform")
    with TemporaryDirectory(prefix="vinalab-ui-smoke-") as project:
        window = MainWindow(project_root=Path(project))
        viewer = window.search_box_editor.viewer
        viewer.set_coordinates("receptor", [(x, x % 3, (x * 2) % 5) for x in range(-10, 11)])
        viewer.set_coordinates("reference", [(-2, 0, 0), (0, 1, 0), (2, 0, 1)])
        window.tabs.setCurrentWidget(window.search_box_editor)
        report = {"ok": False, "platform": app.platformName(), "project_root": project,
                  "webgl_ready": False, "error": "", "viewer_messages": [],
                  "ui_constructed": True, "renderer_gate": "separate_real_qt_required"}
        started, ready_at = monotonic(), None
        poll = QTimer(window)

        def finish():
            poll.stop()
            screenshot = output / "window.png"
            report["screenshot"] = str(screenshot)
            image = window.grab().toImage()
            colors = {image.pixelColor(x, y).name() for x in range(0, image.width(), 5)
                      for y in range(0, image.height(), 5)}
            saved = image.save(str(screenshot))
            report.update(png_saved=saved, window_sampled_colors=len(colors),
                          ok=saved and len(colors) > 10,
                          tab=window.tabs.tabText(window.tabs.currentIndex()))
            report["error"] = "" if report["ok"] else "Blank window or PNG write failed"
            if not report["webgl_ready"]:
                report["limitation"] = "Renderer not verified offscreen; use separate real Qt viewer gate"
            window.close()
            app.quit()

        def inspect():
            nonlocal ready_at
            message = viewer._status.text()
            if message and message not in report["viewer_messages"]:
                report["viewer_messages"].append(message)
            if monotonic() - started >= timeout or (message and not viewer._renderer_ready):
                report.update(viewer_status=viewer._status.text(),
                              viewer_created=viewer._web is not None,
                              tab=window.tabs.tabText(window.tabs.currentIndex()))
                finish()
                return
            if not viewer._renderer_ready:
                return
            ready_at = ready_at or monotonic()
            if monotonic() - ready_at < 0.5:
                return
            try:
                image = viewer.grab().toImage()
                colors = {image.pixelColor(x, y).name()
                          for x in range(0, image.width(), 3)
                          for y in range(0, image.height(), 3)}
                ok = len(colors) > 30
                report.update(webgl_ready=ok, sampled_colors=len(colors),
                              renderer_gate="passed" if ok else "separate_real_qt_required",
                              tab=window.tabs.tabText(window.tabs.currentIndex()),
                              error="" if ok else "Blank viewport")
            except Exception as error:  # noqa: BLE001 - report Qt capture failures at the QA boundary
                report["error"] = str(error)
            finish()

        poll.timeout.connect(inspect)
        poll.start(100)
        window.show()
        app.exec()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ui-smoke-output", type=Path, required=True)
    parser.add_argument("--ui-smoke-timeout", type=float, default=20)
    args = parser.parse_args(argv)
    if not math.isfinite(args.ui_smoke_timeout) or not 0 < args.ui_smoke_timeout <= 120:
        parser.error("timeout must be greater than zero and at most 120 seconds")
    output = args.ui_smoke_output.resolve() / f"ui-smoke-{uuid4().hex}"
    output.mkdir(parents=True)
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    def hard_timeout():
        try:
            _write(output, {"ok": False, "error": "Hard UI smoke timeout", "platform": "offscreen"})
        finally:
            os._exit(1)

    watchdog = Timer(args.ui_smoke_timeout + 5, hard_timeout)
    watchdog.daemon = True
    watchdog.start()
    try:
        try:
            report = _run(output, args.ui_smoke_timeout)
        except Exception as error:  # noqa: BLE001 - report startup failures without a modal dialog
            report = {"ok": False, "error": str(error), "platform": "offscreen"}
        _write(output, report)
        return 0 if report["ok"] else 1
    finally:
        watchdog.cancel()
