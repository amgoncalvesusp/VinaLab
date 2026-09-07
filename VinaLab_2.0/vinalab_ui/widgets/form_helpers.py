"""Shared native file fields and table export for workbench panels."""

import csv
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QStyle, QToolButton, QWidget


def file_field(parent, file_filter, *, save=False):
    row = QWidget(parent)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    entry = QLineEdit(row)
    button = QToolButton(row)
    button.setIcon(parent.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
    button.setToolTip("Choose output file" if save else "Choose file")
    layout.addWidget(entry)
    layout.addWidget(button)

    def browse():
        chooser = QFileDialog.getSaveFileName if save else QFileDialog.getOpenFileName
        path, _ = chooser(parent, button.toolTip(), entry.text(), file_filter)
        if path:
            entry.setText(path)
            entry.editingFinished.emit()

    button.clicked.connect(browse)
    return row, entry


def export_table(table, path):
    def cell(text):
        try:
            float(text)
            return text
        except ValueError:
            return "'" + text if text.startswith(("=", "+", "-", "@")) else text

    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow([table.horizontalHeaderItem(i).text() for i in range(table.columnCount())])
        for row in range(table.rowCount()):
            writer.writerow([cell(table.item(row, col).text()) if table.item(row, col) else ""
                             for col in range(table.columnCount())])
