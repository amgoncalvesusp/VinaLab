"""Project selection and persisted docking history."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class ProjectPanel(QWidget):
    project_requested = Signal(object)
    run_selected = Signal(str)
    analysis_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.path_label = QLabel(self)
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)
        buttons = QHBoxLayout()
        self.new_button = QPushButton("New project", self)
        self.open_button = QPushButton("Open project", self)
        self.load_button = QPushButton("Open selected run", self)
        for button in (self.new_button, self.open_button, self.load_button):
            buttons.addWidget(button)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(["Created", "Ligand", "Scoring", "Status", "Run ID"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.history_tabs = QTabWidget(self)
        self.history_tabs.addTab(self.table, "Docking runs")
        self.analysis_table = QTableWidget(0, 4, self)
        self.analysis_table.setHorizontalHeaderLabels(["Created", "Analysis", "Source run", "Artifact"])
        self.analysis_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.analysis_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.analysis_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.analysis_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.analysis_table.horizontalHeader().setStretchLastSection(True)
        self.history_tabs.addTab(self.analysis_table, "Analyses")
        layout.addWidget(self.history_tabs)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.new_button.clicked.connect(self._new)
        self.open_button.clicked.connect(self._open)
        self.load_button.clicked.connect(self._load)
        self.table.cellDoubleClicked.connect(lambda *_: self._load())
        self.analysis_table.cellDoubleClicked.connect(lambda *_: self._load())
        self.history_tabs.currentChanged.connect(
            lambda index: self.load_button.setText("Open selected analysis" if index else "Open selected run"))

    def show_analyses(self, analyses):
        self.analysis_table.setRowCount(len(analyses))
        for row, (path, data) in enumerate(analyses):
            values = (data.get("created_at", ""), path.stem, data.get("source_run_id") or "External input", path.parent.name)
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, str(path))
                self.analysis_table.setItem(row, column, item)
        self.load_button.setEnabled(bool(analyses) or self.table.rowCount() > 0)

    def show_project(self, path, runs):
        self.path_label.setText(str(path))
        self.table.setRowCount(len(runs))
        for row, run in enumerate(runs):
            values = (run.created_at.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
                      Path(run.metadata.get("original_ligand", run.ligand_path)).name,
                      run.scoring, run.status, run.id)
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, run.id)
                self.table.setItem(row, column, item)
        self.load_button.setEnabled(bool(runs))

    def _new(self):
        path, _ = QFileDialog.getSaveFileName(self, "New project folder", "VinaLab project", "All files (*)")
        if path:
            self.project_requested.emit(Path(path))

    def _open(self):
        path = QFileDialog.getExistingDirectory(self, "Open project folder")
        if path:
            self.project_requested.emit(Path(path))

    def _load(self):
        if self.history_tabs.currentIndex() == 1:
            item = self.analysis_table.item(self.analysis_table.currentRow(), 0)
            if item is not None:
                self.analysis_selected.emit(Path(item.data(Qt.ItemDataRole.UserRole)))
            return
        item = self.table.item(self.table.currentRow(), 0)
        if item is not None:
            self.run_selected.emit(item.data(Qt.ItemDataRole.UserRole))
