"""Editor for the canonical docking search box."""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout, QLabel, QWidget

from vinalab_core.docking.search_box import SearchBox


class SearchBoxEditor(QWidget):
    """Edits the same immutable `SearchBox` consumed by docking engines."""

    search_box_changed = Signal(object)

    def __init__(self, search_box: SearchBox, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.search_box = search_box
        self.validation_message = ""
        layout = QFormLayout(self)
        self._center_inputs = self._add_coordinate_inputs(layout, "Center", ("centerX", "centerY", "centerZ"))
        self._size_inputs = self._add_coordinate_inputs(layout, "Size", ("sizeX", "sizeY", "sizeZ"))
        self._status = QLabel(self)
        self._status.setObjectName("searchBoxValidation")
        layout.addRow("Validation", self._status)
        self._sync_inputs()
        for spin_box in (*self._center_inputs, *self._size_inputs):
            spin_box.valueChanged.connect(self._apply_values)

    @staticmethod
    def _add_coordinate_inputs(
        layout: QFormLayout, label: str, names: tuple[str, str, str]
    ) -> tuple[QDoubleSpinBox, QDoubleSpinBox, QDoubleSpinBox]:
        inputs = []
        for axis, name in zip(("X", "Y", "Z"), names, strict=True):
            spin_box = QDoubleSpinBox()
            spin_box.setObjectName(name)
            spin_box.setDecimals(3)
            spin_box.setRange(-9999.0, 9999.0)
            spin_box.setSingleStep(0.5)
            spin_box.setSuffix(" Å")
            layout.addRow(f"{label} {axis}", spin_box)
            inputs.append(spin_box)
        return tuple(inputs)  # type: ignore[return-value]

    def _sync_inputs(self) -> None:
        for value, spin_box in zip(self.search_box.center, self._center_inputs, strict=True):
            with QSignalBlocker(spin_box):
                spin_box.setValue(value)
        for value, spin_box in zip(self.search_box.size, self._size_inputs, strict=True):
            with QSignalBlocker(spin_box):
                spin_box.setValue(value)

    def _apply_values(self) -> None:
        center = tuple(spin_box.value() for spin_box in self._center_inputs)
        size = tuple(spin_box.value() for spin_box in self._size_inputs)
        try:
            updated = SearchBox(
                center=center,  # type: ignore[arg-type]
                size=size,  # type: ignore[arg-type]
                coordinate_frame=self.search_box.coordinate_frame,
                margin=self.search_box.margin,
                source="user",
            )
        except ValueError as error:
            self.validation_message = "Size values must be positive" if "size" in str(error) else str(error)
            self._status.setText(self.validation_message)
            self._sync_inputs()
            return
        self.search_box = updated
        self.validation_message = ""
        self._status.setText("Ready")
        self.search_box_changed.emit(updated)
