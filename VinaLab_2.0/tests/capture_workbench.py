"""Capture the actual Qt workbench at desktop and compact sizes."""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from vinalab_ui.mainwindow import MainWindow


def main():
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    with TemporaryDirectory() as directory:
        window = MainWindow(project_root=Path(directory))
        window.search_box_editor.viewer.set_coordinates("receptor", [(x, x % 4, x % 3) for x in range(-12, 13)])
        window.search_box_editor.viewer.set_coordinates("reference", [(-1, 0, 0), (1, 0, 0), (2, 1, 0)])
        scenes = [(size, index) for size in ((1280, 800), (900, 640)) for index in range(9)]
        window.show()

        def capture():
            if not scenes:
                window.close()
                app.quit()
                return
            size, index = scenes.pop(0)
            window.resize(*size)
            window.tabs.setCurrentIndex(index)
            def save():
                path = output / f"{size[0]}-{index}-{window.TAB_NAMES[index].replace(' ', '-')}.png"
                window.grab().save(str(path))
                print(str(path), flush=True)
                capture()
            QTimer.singleShot(2000 if index == 3 else 120, save)

        QTimer.singleShot(100, capture)
        app.exec()


if __name__ == "__main__":
    main()
