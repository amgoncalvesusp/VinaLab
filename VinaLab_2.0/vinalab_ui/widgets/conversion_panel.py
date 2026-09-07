"""Explicit molecule preparation controls embedded beside input selection."""

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QLabel, QPushButton, QWidget

from vinalab_ui.widgets.form_helpers import file_field


class ConversionPanel(QWidget):
    convert_requested = Signal(object, object, str)

    def __init__(self, role, parent=None):
        super().__init__(parent)
        self.role = role
        layout = QFormLayout(self)
        row, self.source_input = file_field(self, "Molecules (*.pdb *.mol2 *.sdf *.mol)")
        layout.addRow("Source molecule", row)
        row, self.output_input = file_field(self, "PDBQT (*.pdbqt)", save=True)
        layout.addRow("Prepared PDBQT", row)
        self.convert_button = QPushButton(f"Prepare {role}", self)
        layout.addRow(self.convert_button)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        layout.addRow(self.status)
        self.convert_button.clicked.connect(self._request)

    def _request(self):
        source = Path(self.source_input.text())
        output = Path(self.output_input.text())
        if not source.is_file():
            self.status.setText("Select an existing source molecule.")
        elif not self.output_input.text().strip() or output.suffix.lower() != ".pdbqt":
            self.status.setText("Choose an output file with the .pdbqt extension.")
        elif output.exists():
            self.status.setText("Output already exists. Choose a new name to preserve the existing file.")
        else:
            self.convert_requested.emit(source, output, self.role)
