"""Editor for the canonical docking search box."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from vinalab_core.docking.search_box import SearchBox
from vinalab_ui.widgets.box_viewer import BoxViewer, box_payload, validate_coordinates


class SearchBoxEditor(QWidget):
    """Edits the same immutable `SearchBox` consumed by docking engines."""

    search_box_changed = Signal(object)
    reference_selected = Signal(object)

    def __init__(
        self, search_box: SearchBox, parent: QWidget | None = None,
        *, coordinate_reader: Callable | None = None,
    ) -> None:
        super().__init__(parent)
        box_payload(search_box)
        self.search_box = search_box
        self._coordinate_reader = coordinate_reader
        self._reference_coordinates = None
        self.reference_path: Path | None = None
        self.structure_path: Path | None = None
        self.validation_message = ""
        root = QVBoxLayout(self)
        layout = QFormLayout()
        root.addLayout(layout)
        self._center_inputs = self._add_coordinate_inputs(layout, "Center", ("centerX", "centerY", "centerZ"))
        self._size_inputs = self._add_coordinate_inputs(layout, "Size", ("sizeX", "sizeY", "sizeZ"))
        self.margin_input = QDoubleSpinBox(self)
        self.margin_input.setObjectName("referenceMargin")
        self.margin_input.setRange(0, 9999)
        self.margin_input.setDecimals(3)
        self.margin_input.setValue(search_box.margin)
        self.margin_input.setSuffix(" Å")
        layout.addRow("Reference margin", self.margin_input)
        toolbar = QHBoxLayout()
        self.reference_button = QPushButton("Load reference", self)
        self.reference_button.setObjectName("loadBoxReference")
        self.reference_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        self.reference_button.clicked.connect(self._browse_reference)
        toolbar.addWidget(self.reference_button)
        self.fit_button = QPushButton("Fit reference", self)
        self.fit_button.setObjectName("fitReferenceBox")
        self.fit_button.setEnabled(False)
        self.fit_button.clicked.connect(self.fit_reference)
        toolbar.addWidget(self.fit_button)
        toolbar.addStretch()
        reset = QToolButton(self)
        reset.setObjectName("resetBoxView")
        reset.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        reset.setToolTip("Reset camera")
        reset.setAccessibleName("Reset camera")
        toolbar.addWidget(reset)
        root.addLayout(toolbar)
        self.viewer = BoxViewer(self)
        self.viewer.set_box(search_box)
        reset.clicked.connect(self.viewer.reset_view)
        root.addWidget(self.viewer, 1)
        self._status = QLabel(self)
        self._status.setObjectName("searchBoxValidation")
        self._status.setWordWrap(True)
        root.addWidget(self._status)
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
                spin_box.setRange(min(-9999.0, value), max(9999.0, value))
                spin_box.setValue(value)
        for value, spin_box in zip(self.search_box.size, self._size_inputs, strict=True):
            with QSignalBlocker(spin_box):
                spin_box.setRange(min(-9999.0, value), max(9999.0, value))
                spin_box.setValue(value)

    def set_search_box(self, search_box: SearchBox) -> None:
        """Adopt parent state without echoing a change signal back to the parent."""
        box_payload(search_box)
        self.search_box = search_box
        self._sync_inputs()
        with QSignalBlocker(self.margin_input):
            self.margin_input.setMaximum(max(9999.0, search_box.margin))
            self.margin_input.setValue(search_box.margin)
        self.viewer.set_box(search_box)
        self.validation_message = ""
        self._status.setText("Ready")

    def _read_coordinates(self, path: str | Path, coordinates: Iterable | None):
        resolved = Path(path).expanduser().resolve()
        if not resolved.is_file():
            raise ValueError(f"Structure file does not exist: {resolved.name}")
        if coordinates is None:
            reader = self._coordinate_reader
            if reader is None:
                from vinalab_core.prepare.molecule import read_coordinates
                reader = read_coordinates
            coordinates = reader(resolved)
        return resolved, validate_coordinates(coordinates)

    def set_structure(self, path: str | Path, *, coordinates: Iterable | None = None) -> None:
        """Display receptor coordinates without guessing/changing its frame ID."""
        resolved, points = self._read_coordinates(path, coordinates)
        self.viewer.set_coordinates("receptor", points)
        self.structure_path = resolved

    def set_reference(self, path: str | Path, *, coordinates: Iterable | None = None) -> None:
        """Atomically load a same-frame reference and fit a canonical search box.

        The caller owns receptor/reference alignment. This widget never aligns or
        optimizes molecular coordinates. Invalid loads raise without emitting.
        """
        resolved, points = self._read_coordinates(path, coordinates)
        box = self._reference_box(points)
        self.viewer.set_coordinates("reference", points)
        self._reference_coordinates = points
        self.reference_path = resolved
        self.fit_button.setEnabled(True)
        self.set_search_box(box)
        self.reference_selected.emit(resolved)
        self.search_box_changed.emit(box)

    def clear_reference(self) -> None:
        """Discard the cached reference without emitting or changing the box."""
        self.reference_path = None
        self._reference_coordinates = None
        self.fit_button.setEnabled(False)
        self.viewer.clear_coordinates("reference")

    def clear_structure(self) -> None:
        """Discard the receptor preview; parent owns reference and box resets."""
        self.structure_path = None
        self.viewer.clear_coordinates("receptor")

    def _reference_box(self, points) -> SearchBox:
        return SearchBox.fit_to_coordinates(
            points, self.search_box.coordinate_frame, self.margin_input.value(),
        )

    def fit_reference(self) -> None:
        if self._reference_coordinates is None:
            return
        try:
            box = self._reference_box(self._reference_coordinates)
            self.set_search_box(box)
        except ValueError as error:
            self.validation_message = str(error)
            self._status.setText(str(error))
            return
        self.search_box_changed.emit(box)

    def _browse_reference(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select reference ligand", str(self.reference_path or ""),
            "Molecules (*.pdb *.pdbqt *.sdf *.mol *.mol2 *.xyz)",
        )
        if path:
            try:
                self.set_reference(path)
            except (ValueError, OSError, ImportError) as error:
                self.validation_message = str(error)
                self._status.setText(str(error))

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
        self.set_search_box(updated)
        self.search_box_changed.emit(updated)
