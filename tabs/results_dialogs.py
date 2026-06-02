# -*- coding: utf-8 -*-
"""Comparison, validation, and export dialogs for the results tab.

Extracted from results_tab.py. These dialogs reach back into the ResultsTab
parent only through duck-typed helpers (``_pose_text``, ``_docking_score``,
``_pose_identity``, ``_selected_result_row``), so the parent type is referenced
only under TYPE_CHECKING and there is no runtime import cycle.
"""

from __future__ import annotations

import itertools
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import TYPE_CHECKING

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:  # pragma: no cover - installer should provide PySide6-WebEngine
    QWebEngineView = None

from core.docking_engine import extract_pose_model, find_obabel_executable
from core.file_utils import clean_pdbqt_text
from core.i18n import I18n
from core.rmsd import symmetry_corrected_rmsd
from tabs.results_view import (
    build_comparison_html,
    pdbqt_text_to_view_pdb,
    prepare_pose_view_files,
    safe_export_name,
)

if TYPE_CHECKING:
    from tabs.results_tab import ResultsTab

NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0


class ComparisonDialog(QDialog):
    """Compare docked poses, crystal references, and scoring values."""

    def __init__(
        self, results: list[dict], parent: ResultsTab, lang: str = "pt"
    ) -> None:
        """Create comparison controls."""
        super().__init__(parent)
        self.results = list(results)
        self.results_tab = parent
        self.lang = lang
        self.view_dir = Path(tempfile.mkdtemp(prefix="vinalab_compare_"))
        self.setWindowTitle(I18n.get("rd_compare_title", self.lang))
        self.resize(1250, 850)
        self.pose_pair_radio = QRadioButton("Pose A vs Pose B")
        self.crystal_radio = QRadioButton(I18n.get("rd_mode_crystal", self.lang))
        self.scoring_radio = QRadioButton(I18n.get("rd_mode_scoring", self.lang))
        self.mode_group = QButtonGroup(self)
        self.pose_a_combo = QComboBox()
        self.pose_b_combo = QComboBox()
        self.reference_edit = QLineEdit()
        self.top_n_spin = QSpinBox()
        self.run_button = QPushButton(I18n.get("rd_run_compare", self.lang))
        self.status_label = QLabel("RMSD: N/A")
        self.table = QTableWidget(0, 0)
        self.web_view = QWebEngineView() if QWebEngineView is not None else None
        self.figure = Figure(figsize=(5, 2.6), tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self._build_ui()
        self._populate_pose_combos()

    def _build_ui(self) -> None:
        """Build comparison dialog controls."""
        layout = QVBoxLayout(self)
        mode_row = QHBoxLayout()
        for button in (self.pose_pair_radio, self.crystal_radio, self.scoring_radio):
            self.mode_group.addButton(button)
            mode_row.addWidget(button)
        self.pose_pair_radio.setChecked(True)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Pose A"))
        selector_row.addWidget(self.pose_a_combo)
        selector_row.addWidget(QLabel("Pose B"))
        selector_row.addWidget(self.pose_b_combo)
        selector_row.addWidget(QLabel(I18n.get("rd_reference", self.lang)))
        self.reference_edit.setReadOnly(True)
        selector_row.addWidget(self.reference_edit)
        browse_button = QPushButton(I18n.get("browse_button", self.lang))
        browse_button.clicked.connect(self._pick_reference)
        selector_row.addWidget(browse_button)
        selector_row.addWidget(QLabel("Top N"))
        self.top_n_spin.setRange(1, 100)
        self.top_n_spin.setValue(10)
        selector_row.addWidget(self.top_n_spin)
        self.run_button.clicked.connect(self._run)
        selector_row.addWidget(self.run_button)
        layout.addLayout(selector_row)

        self.status_label.setObjectName("label_muted")
        layout.addWidget(self.status_label)
        if self.web_view is not None:
            layout.addWidget(self.web_view, stretch=3)
        else:
            layout.addWidget(
                QLabel(I18n.get("rd_webengine_missing", self.lang)), stretch=3
            )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(self.canvas, stretch=1)

    def _populate_pose_combos(self) -> None:
        """Fill pose selectors from result rows."""
        for index, row in enumerate(self.results):
            label = self._row_label(row)
            self.pose_a_combo.addItem(label, index)
            self.pose_b_combo.addItem(label, index)
        if self.pose_b_combo.count() > 1:
            self.pose_b_combo.setCurrentIndex(1)

    def _pick_reference(self) -> None:
        """Pick a crystal/reference PDBQT file."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            I18n.get("rd_reference_pose_title", self.lang),
            "",
            f"{I18n.get('pdbqt_filter', self.lang)};;{I18n.get('all_files', self.lang)}",
        )
        if file_name:
            self.reference_edit.setText(file_name)

    def _run(self) -> None:
        """Run the selected comparison mode."""
        if self.pose_pair_radio.isChecked():
            self._compare_pose_pair()
        elif self.crystal_radio.isChecked():
            self._compare_to_crystal()
        else:
            self._compare_scoring_values()

    def _compare_pose_pair(self) -> None:
        """Compare two docked poses by symmetry-corrected heavy-atom RMSD."""
        row_a = self._selected_row(self.pose_a_combo)
        row_b = self._selected_row(self.pose_b_combo)
        if row_a is None or row_b is None:
            return
        result = symmetry_corrected_rmsd(
            self.results_tab._pose_text(row_a), self.results_tab._pose_text(row_b)
        )
        if not result.comparable:
            self.status_label.setText(
                I18n.get("rd_rmsd_not_comparable_status", self.lang)
            )
            QMessageBox.information(
                self, I18n.get("rd_pose_comparison_title", self.lang), result.reason
            )
            self._populate_table(
                ["Pose A", "Pose B", "RMSD Å"],
                [
                    [
                        self._row_label(row_a),
                        self._row_label(row_b),
                        I18n.get("rd_not_comparable", self.lang),
                    ]
                ],
            )
            return
        rmsd = result.value
        self.status_label.setText(
            I18n.get("rd_rmsd_value", self.lang).format(rmsd=rmsd)
        )
        self._populate_table(
            ["Pose A", "Pose B", "RMSD Å"],
            [[self._row_label(row_a), self._row_label(row_b), f"{rmsd:.3f}"]],
        )
        self._render_pose_pair(
            row_a, row_b, I18n.get("rd_title_pose_pair", self.lang).format(rmsd=rmsd)
        )
        self.figure.clear()
        self.canvas.draw_idle()

    def _compare_to_crystal(self) -> None:
        """Rank top-N poses by symmetry-corrected RMSD to a reference crystal pose."""
        reference_path = Path(self.reference_edit.text().strip())
        if not reference_path.exists():
            QMessageBox.warning(
                self,
                I18n.get("rd_mode_crystal", self.lang),
                I18n.get("rd_choose_reference_pdbqt", self.lang),
            )
            return
        reference_text = clean_pdbqt_text(
            reference_path.read_text(encoding="utf-8", errors="replace")
        )
        rows = sorted(self.results, key=self.results_tab._docking_score)[
            : self.top_n_spin.value()
        ]
        table_rows = []
        best_row = None
        best_rmsd = float("inf")
        incomparable_reason = ""
        for row in rows:
            result = symmetry_corrected_rmsd(
                self.results_tab._pose_text(row), reference_text
            )
            if not result.comparable:
                incomparable_reason = result.reason
                table_rows.append(
                    [
                        int(row.get("pose_rank", row.get("mode", 0))),
                        f"{self.results_tab._docking_score(row):.3f}",
                        I18n.get("rd_not_comparable", self.lang),
                    ]
                )
                continue
            rmsd = result.value
            if rmsd < best_rmsd:
                best_rmsd = rmsd
                best_row = row
            table_rows.append(
                [
                    int(row.get("pose_rank", row.get("mode", 0))),
                    f"{self.results_tab._docking_score(row):.3f}",
                    f"{rmsd:.3f}",
                ]
            )
        if best_row is None:
            self.status_label.setText(
                I18n.get("rd_best_rmsd_not_comparable", self.lang)
            )
            if incomparable_reason:
                QMessageBox.information(
                    self, I18n.get("rd_mode_crystal", self.lang), incomparable_reason
                )
            self._populate_table(
                ["Pose rank", "Score", "RMSD to crystal Å"], table_rows
            )
            return
        self.status_label.setText(
            I18n.get("rd_best_rmsd_value", self.lang).format(rmsd=best_rmsd)
        )
        self._populate_table(["Pose rank", "Score", "RMSD to crystal Å"], table_rows)
        self._render_pose_vs_reference(
            best_row,
            reference_path,
            I18n.get("rd_title_pose_vs_crystal_best", self.lang).format(rmsd=best_rmsd),
        )
        self.figure.clear()
        self.canvas.draw_idle()

    def _compare_scoring_values(self) -> None:
        """Plot scoring values for the selected pose identity."""
        selected = self._selected_row(self.pose_a_combo)
        if selected is None:
            return
        pose_key = self.results_tab._pose_identity(selected)
        rows = [
            row
            for row in self.results
            if self.results_tab._pose_identity(row) == pose_key
        ]
        labels = [
            row.get("scoring_function", row.get("scoring_key", "")) for row in rows
        ]
        values = [float(row.get("affinity", 0.0)) for row in rows]
        self.status_label.setText(I18n.get("rd_scoring_compare_status", self.lang))
        self._populate_table(
            [I18n.get("rd_scoring_func_col", self.lang), "Score"],
            [
                [label, f"{value:.3f}"]
                for label, value in zip(labels, values, strict=False)
            ],
        )
        self.figure.clear()
        axis = self.figure.add_subplot(111)
        axis.bar(range(len(values)), values, color="#C8922A")
        axis.set_xticks(range(len(labels)))
        axis.set_xticklabels(labels, rotation=30, ha="right")
        axis.set_ylabel("Score")
        self.canvas.draw_idle()

    def _render_pose_pair(self, row_a: dict, row_b: dict, title: str) -> None:
        """Render two docked poses in different colors."""
        if self.web_view is None:
            return
        dir_a = self.view_dir / "pose_a"
        dir_b = self.view_dir / "pose_b"
        dir_a.mkdir(exist_ok=True)
        dir_b.mkdir(exist_ok=True)
        receptor_pdb, pose_a_pdb = prepare_pose_view_files(row_a, dir_a)
        _receptor_b, pose_b_pdb = prepare_pose_view_files(row_b, dir_b)
        html_path = self.view_dir / "comparison.html"
        html_path.write_text(
            build_comparison_html(title, receptor_pdb, pose_a_pdb, pose_b_pdb),
            encoding="utf-8",
        )
        self.web_view.setUrl(QUrl.fromLocalFile(str(html_path)))

    def _render_pose_vs_reference(
        self, row: dict, reference_path: Path, title: str
    ) -> None:
        """Render one docked pose against a crystal reference pose."""
        if self.web_view is None:
            return
        receptor_pdb, pose_pdb = prepare_pose_view_files(row, self.view_dir)
        reference_pdb = self.view_dir / "reference.pdb"
        reference_pdb.write_text(
            pdbqt_text_to_view_pdb(
                reference_path.read_text(encoding="utf-8", errors="replace"),
                include_conect=True,
            ),
            encoding="utf-8",
        )
        html_path = self.view_dir / "comparison.html"
        html_path.write_text(
            build_comparison_html(title, receptor_pdb, pose_pdb, reference_pdb),
            encoding="utf-8",
        )
        self.web_view.setUrl(QUrl.fromLocalFile(str(html_path)))

    def _populate_table(self, headers: list[str], rows: list[list[str]]) -> None:
        """Populate the comparison result table."""
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))
        for row_index, row_values in enumerate(rows):
            for column_index, value in enumerate(row_values):
                self.table.setItem(
                    row_index, column_index, QTableWidgetItem(str(value))
                )

    def _selected_row(self, combo: QComboBox) -> dict | None:
        """Return the result row selected in a combo box."""
        index = combo.currentData()
        if index is None:
            return None
        return self.results[int(index)]

    @staticmethod
    def _row_label(row: dict) -> str:
        """Return compact pose label."""
        return (
            f"{row['ligand_name']} | {row.get('scoring_function', row.get('scoring_key', ''))} | "
            f"pose {int(row.get('pose_rank', row.get('mode', 0)))} | {float(row.get('affinity', 0.0)):.3f}"
        )


class ProtocolValidationDialog(QDialog):
    """Display redocking validation metrics against a crystallographic pose."""

    def __init__(
        self,
        rows: list[dict],
        reference_path: Path,
        top_n: int,
        parent: QWidget | None = None,
        lang: str = "pt",
    ) -> None:
        """Build validation report dialog."""
        super().__init__(parent)
        self.lang = lang
        self.rows = sorted(rows, key=lambda row: float(row.get("affinity", 0.0)))
        self.reference_path = reference_path
        self.top_n = top_n
        self.validation_rows = self._compute_rows()
        self.setWindowTitle(I18n.get("validate_protocol", self.lang))
        self.resize(900, 620)
        self.summary_label = QLabel()
        self.table = QTableWidget(0, 4)
        self.export_button = QPushButton(I18n.get("rd_export_validation", self.lang))
        self._build_ui()

    def _build_ui(self) -> None:
        """Build validation report UI."""
        layout = QVBoxLayout(self)
        self.summary_label.setWordWrap(True)
        self.summary_label.setText(self._summary_text())
        layout.addWidget(self.summary_label)
        self.table.setHorizontalHeaderLabels(
            [
                I18n.get("rd_col_pose_rank", self.lang),
                I18n.get("rd_col_score", self.lang),
                I18n.get("rd_col_rmsd_crystal", self.lang),
                I18n.get("rd_col_within_2a", self.lang),
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setRowCount(len(self.validation_rows))
        for row_index, row in enumerate(self.validation_rows):
            values = [
                row["pose_rank"],
                f"{row['score']:.3f}",
                self._format_rmsd_cell(row),
                row["within_2A"],
            ]
            for column_index, value in enumerate(values):
                self.table.setItem(
                    row_index, column_index, QTableWidgetItem(str(value))
                )
        layout.addWidget(self.table, stretch=1)
        self.export_button.clicked.connect(self._export_csv)
        layout.addWidget(self.export_button)

    def _compute_rows(self) -> list[dict]:
        """Compute symmetry-corrected RMSD rows for validation output poses."""
        reference_text = clean_pdbqt_text(
            self.reference_path.read_text(encoding="utf-8", errors="replace")
        )
        output_rows: list[dict] = []
        for row in self.rows:
            pose_text = extract_pose_model(
                Path(row["output_file"]), int(row["mode"]), include_model=False
            )
            result = symmetry_corrected_rmsd(pose_text, reference_text)
            output_rows.append(
                {
                    "pose_rank": int(row.get("pose_rank", row.get("mode", 0))),
                    "score": float(row.get("affinity", 0.0)),
                    "comparable": result.comparable,
                    "reason": result.reason,
                    "rmsd_to_crystal": result.value,
                    "within_2A": (
                        (
                            I18n.get("rd_within_yes", self.lang)
                            if result.value <= 2.0
                            else I18n.get("rd_within_no", self.lang)
                        )
                        if result.comparable
                        else I18n.get("rd_within_na", self.lang)
                    ),
                }
            )
        return output_rows

    def _format_rmsd_cell(self, row: dict) -> str:
        """Return the RMSD column text, marking non-comparable poses explicitly."""
        if not row.get("comparable", False):
            return I18n.get("rd_not_comparable", self.lang)
        return f"{row['rmsd_to_crystal']:.3f}"

    def _summary_text(self) -> str:
        """Return top-1/top-3/top-N success summary over comparable poses only."""
        if not self.validation_rows:
            return I18n.get("rd_no_validation_poses", self.lang)
        comparable = [row for row in self.validation_rows if row.get("comparable")]
        incomparable = len(self.validation_rows) - len(comparable)
        if not comparable:
            return I18n.get("rd_no_comparable_summary", self.lang).format(
                count=incomparable
            )
        top1_rmsd = comparable[0]["rmsd_to_crystal"]
        top3_success = any(row["rmsd_to_crystal"] <= 2.0 for row in comparable[:3])
        topn_success = any(
            row["rmsd_to_crystal"] <= 2.0 for row in comparable[: self.top_n]
        )
        suffix = (
            I18n.get("rd_incomparable_suffix", self.lang).format(count=incomparable)
            if incomparable
            else ""
        )
        return (
            f"Top-1 RMSD: {top1_rmsd:.3f} Å | "
            f"Top-3 success within 2 Å: {'yes' if top3_success else 'no'} | "
            f"Top-{self.top_n} success within 2 Å: {'yes' if topn_success else 'no'}"
            f"{suffix}"
        )

    def _export_csv(self) -> None:
        """Export validation report to CSV."""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            I18n.get("rd_export_validation", self.lang),
            "",
            I18n.get("rd_csv_filter", self.lang),
        )
        if not file_name:
            return
        pd.DataFrame(self.validation_rows).to_csv(Path(file_name), index=False)


class ExportComplexDialog(QDialog):
    """Dialog for exporting selected or multiple docked poses."""

    def __init__(
        self, results: list[dict], parent: QWidget | None = None, lang: str = "pt"
    ) -> None:
        """Initialize export controls."""
        super().__init__(parent)
        self.results = list(results)
        self.lang = lang
        self.setWindowTitle(I18n.get("export_complex", self.lang))
        self.selected_radio = QRadioButton(I18n.get("rd_export_selected", self.lang))
        self.all_radio = QRadioButton(I18n.get("rd_export_all", self.lang))
        self.selected_radio.setChecked(True)
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.selected_radio)
        self.mode_group.addButton(self.all_radio)
        self.top_n_spin = QSpinBox()
        self.top_n_spin.setRange(1, 999)
        self.top_n_spin.setValue(1)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["pdbqt", "pdb", "mol2"])
        self.folder_edit = QLineEdit()
        self.progress_bar = QProgressBar()
        self.export_button = QPushButton(I18n.get("rd_export_btn", self.lang))
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the dialog layout."""
        layout = QVBoxLayout(self)
        layout.addWidget(self.selected_radio)
        layout.addWidget(self.all_radio)

        top_n_row = QHBoxLayout()
        top_n_row.addWidget(QLabel(I18n.get("rd_topn_per_ligand", self.lang)))
        top_n_row.addWidget(self.top_n_spin)
        layout.addLayout(top_n_row)

        format_row = QHBoxLayout()
        format_row.addWidget(QLabel(I18n.get("rd_format_label", self.lang)))
        format_row.addWidget(self.format_combo)
        layout.addLayout(format_row)

        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder_edit)
        browse_button = QPushButton(I18n.get("browse_button", self.lang))
        browse_button.clicked.connect(self._pick_folder)
        folder_row.addWidget(browse_button)
        layout.addLayout(folder_row)

        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        button_box = QDialogButtonBox(Qt.Horizontal)
        button_box.addButton(self.export_button, QDialogButtonBox.AcceptRole)
        button_box.addButton(QDialogButtonBox.Cancel)
        button_box.rejected.connect(self.reject)
        self.export_button.clicked.connect(self._export)
        layout.addWidget(button_box)

        self.all_radio.toggled.connect(self.top_n_spin.setVisible)
        self.top_n_spin.setVisible(False)

    def _pick_folder(self) -> None:
        """Select an output folder."""
        folder = QFileDialog.getExistingDirectory(
            self, I18n.get("select_output_dir", self.lang)
        )
        if folder:
            self.folder_edit.setText(folder)

    def _export(self) -> None:
        """Run the export workflow."""
        output_folder = self.folder_edit.text().strip()
        title = I18n.get("export_complex", self.lang)
        if not output_folder:
            QMessageBox.warning(
                self, title, I18n.get("rd_choose_output_folder", self.lang)
            )
            return
        output_dir = Path(output_folder)
        output_dir.mkdir(parents=True, exist_ok=True)
        export_format = self.format_combo.currentText()
        rows = self._rows_to_export()
        if not rows:
            QMessageBox.warning(self, title, I18n.get("rd_no_pose_selected", self.lang))
            return
        if export_format in {"pdb", "mol2"} and find_obabel_executable() is None:
            QMessageBox.critical(
                self, title, I18n.get("rd_obabel_missing_export", self.lang)
            )
            return

        exported = 0
        for index, row in enumerate(rows, start=1):
            self._export_row(row, output_dir, export_format)
            exported += 1
            self.progress_bar.setValue(int(index / len(rows) * 100))
            QApplication.processEvents()

        QMessageBox.information(
            self,
            title,
            I18n.get("rd_exported_count", self.lang).format(
                count=exported, directory=output_dir
            ),
        )
        self.accept()

    def _rows_to_export(self) -> list[dict]:
        """Resolve the pose rows to export."""
        if self.selected_radio.isChecked():
            parent = self.parent()
            if not hasattr(parent, "_selected_result_row"):
                return []
            selected = parent._selected_result_row()
            return [selected] if selected is not None else []

        top_n = self.top_n_spin.value()
        rows: list[dict] = []
        grouped = itertools.groupby(
            sorted(
                self.results,
                key=lambda row: (
                    row["ligand_name"],
                    row.get("scoring_function", row.get("scoring_key", "")),
                    float(row["affinity"]),
                    int(row["mode"]),
                ),
            ),
            key=lambda row: (
                row["ligand_name"],
                row.get("scoring_function", row.get("scoring_key", "")),
            ),
        )
        for _, group_rows in grouped:
            rows.extend(list(group_rows)[:top_n])
        return rows

    def _export_row(self, row: dict, output_dir: Path, export_format: str) -> None:
        """Export a single pose row."""
        pose_basename = f"{safe_export_name(row['ligand_name'])}_pose{int(row['mode'])}"
        pose_pdbqt = output_dir / f"{pose_basename}.pdbqt"
        pose_pdbqt.write_text(
            extract_pose_model(
                Path(row["output_file"]), int(row["mode"]), include_model=False
            ),
            encoding="utf-8",
        )
        if export_format == "pdbqt":
            return

        output_path = output_dir / f"{pose_basename}.{export_format}"
        completed = subprocess.run(
            [find_obabel_executable(), str(pose_pdbqt), "-O", str(output_path)],
            capture_output=True,
            text=True,
            check=False,
            creationflags=NO_WINDOW,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                completed.stderr.strip()
                or completed.stdout.strip()
                or I18n.get("rd_obabel_conv_fail", self.lang)
            )
        pose_pdbqt.unlink(missing_ok=True)
