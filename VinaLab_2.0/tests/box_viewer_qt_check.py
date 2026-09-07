"""Opt-in real Qt/WebGL smoke check: python tests/box_viewer_qt_check.py."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from vinalab_core.docking.search_box import SearchBox
from vinalab_ui.widgets.search_box_editor import SearchBoxEditor


def main():
    app = QApplication([])
    editor = SearchBoxEditor(SearchBox((0, 0, 0), (12, 14, 16), "qa", 4, "user"))
    assert editor.viewer._web is None
    editor.viewer.set_coordinates("receptor", [(x, x % 3, (x * 2) % 5) for x in range(-10, 11)])
    editor.viewer.set_coordinates("reference", [(-2, 0, 0), (0, 1, 0), (2, 0, 1)])
    editor.resize(900, 800)
    editor.show()
    result = {"ok": False}

    def finish(ready):
        if ready:
            output = Path(tempfile.gettempdir()) / "vinalab-box-viewer-qt.png"
            image = editor.viewer.grab().toImage()
            colors = {image.pixelColor(x, y).name() for x in range(0, image.width(), 3)
                      for y in range(0, image.height(), 3)}
            result["ok"] = len(colors) > 30
            image.save(str(output))
            print({"webgl_ready": ready, "sampled_colors": len(colors), "screenshot": str(output)})
        else:
            print("Qt WebGL did not initialize")
        editor.close()
        app.quit()

    def inspect():
        finish(editor.viewer._renderer_ready)

    QTimer.singleShot(5000, inspect)
    QTimer.singleShot(20000, lambda: finish(False))
    app.exec()
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
