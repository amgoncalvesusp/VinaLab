# -*- coding: utf-8 -*-
"""Report generation and summary tab."""

from collections import Counter
from datetime import datetime
from pathlib import Path
import tempfile

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core.i18n import I18n
from core.scrolling import ScrollManager


class ReportTab(QWidget):
    """Show docking summary statistics and generate PDF reports."""

    def __init__(self) -> None:
        """Create summary labels and report buttons."""
        super().__init__()
        self.lang = "pt"
        self.results: list[dict] = []
        self.parameters: dict = {}
        self.analysis_provider = None
        self.output_directory: Path | None = None
        self.chart_path: Path | None = None
        self.best_label = QLabel("N/A")
        self.mean_label = QLabel("N/A")
        self.ligands_label = QLabel("0")
        self.poses_label = QLabel("N/A")
        self.summary_group = QGroupBox()
        self.form_labels = {
            key: QLabel()
            for key in (
                "best_affinity",
                "mean_affinity",
                "ligands_docked",
                "poses_per_ligand",
            )
        }
        self.pdf_button = QPushButton()
        self.open_button = QPushButton()
        self._build_ui()
        self.retranslate_ui(self.lang)

    def set_results(self, results: list[dict]) -> None:
        """Update report statistics from current results."""
        self.results = list(results)
        self._refresh_summary()

    def set_parameters(self, parameters: dict) -> None:
        """Store the latest docking parameters for report generation."""
        self.parameters = dict(parameters)

    def set_output_directory(self, output_directory: Path) -> None:
        """Store the active output directory."""
        self.output_directory = output_directory

    def set_analysis_provider(self, provider) -> None:
        """Store a provider for consensus, clustering, and interaction report sections."""
        self.analysis_provider = provider

    def set_chart_path(self, chart_path: Path) -> None:
        """Store the latest chart image path for PDF embedding."""
        self.chart_path = chart_path

    def generate_pdf_report(self) -> None:
        """Generate a PDF report with parameters, summary, results, and chart."""
        if not self.results:
            QMessageBox.warning(
                self,
                I18n.get("warning_title", self.lang),
                I18n.get("no_results", self.lang),
            )
            return
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            I18n.get("generate_pdf", self.lang),
            "",
            I18n.get("rp_pdf_filter", self.lang),
        )
        if not file_name:
            return

        doc = SimpleDocTemplate(str(Path(file_name)), pagesize=letter)
        styles = getSampleStyleSheet()
        story = [
            Paragraph(I18n.get("rp_report_title", self.lang), styles["Title"]),
            Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), styles["Normal"]),
            Spacer(1, 12),
            Paragraph(I18n.get("rp_section_params", self.lang), styles["Heading2"]),
        ]
        for key, value in self.parameters.items():
            story.append(Paragraph(f"{key}: {value}", styles["Normal"]))
        story.extend(
            [
                Spacer(1, 12),
                Paragraph(
                    I18n.get("rp_section_results", self.lang), styles["Heading2"]
                ),
            ]
        )
        story.append(self._dynamic_results_table())
        story.extend(
            [
                Spacer(1, 12),
                Paragraph(
                    I18n.get("rp_section_consensus", self.lang), styles["Heading2"]
                ),
            ]
        )
        story.append(self._consensus_table())
        story.extend(
            [
                Spacer(1, 12),
                Paragraph(
                    I18n.get("rp_section_clusters", self.lang), styles["Heading2"]
                ),
            ]
        )
        story.append(self._cluster_summary_table())
        story.extend(
            [
                Spacer(1, 12),
                Paragraph(
                    I18n.get("rp_section_interactions", self.lang), styles["Heading2"]
                ),
            ]
        )
        story.append(self._interaction_summary_table())
        story.extend(
            [
                Spacer(1, 12),
                Paragraph(I18n.get("rp_section_errors", self.lang), styles["Heading2"]),
            ]
        )
        story.append(self._warnings_table())
        if self.chart_path and self.chart_path.exists():
            story.extend(
                [
                    Spacer(1, 12),
                    Paragraph(
                        I18n.get("affinity_chart", self.lang), styles["Heading2"]
                    ),
                ]
            )
            story.append(Image(str(self.chart_path), width=500, height=220))
        doc.build(story, onFirstPage=self._draw_footer, onLaterPages=self._draw_footer)

    def open_output_folder(self) -> None:
        """Open the selected output folder using the OS default file manager."""
        if not self.output_directory or not self.output_directory.exists():
            QMessageBox.warning(
                self,
                I18n.get("warning_title", self.lang),
                I18n.get("missing_output_folder", self.lang),
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_directory)))

    def retranslate_ui(self, lang: str) -> None:
        """Retranslate report tab controls."""
        self.lang = lang
        self.summary_group.setTitle(I18n.get("summary_stats", lang))
        for key, label in self.form_labels.items():
            label.setText(I18n.get(key, lang))
        self.pdf_button.setText(I18n.get("generate_pdf", lang))
        self.open_button.setText(I18n.get("open_folder", lang))
        self.pdf_button.setToolTip(I18n.get("generate_pdf", lang))
        self.open_button.setToolTip(I18n.get("open_folder", lang))

    def _build_ui(self) -> None:
        """Build the report tab layout."""
        outer_layout = QVBoxLayout(self)
        content = QWidget()
        layout = QVBoxLayout(content)
        form = QFormLayout(self.summary_group)
        form.addRow(self.form_labels["best_affinity"], self.best_label)
        form.addRow(self.form_labels["mean_affinity"], self.mean_label)
        form.addRow(self.form_labels["ligands_docked"], self.ligands_label)
        form.addRow(self.form_labels["poses_per_ligand"], self.poses_label)
        layout.addWidget(self.summary_group)

        self.pdf_button.clicked.connect(self.generate_pdf_report)
        self.open_button.clicked.connect(self.open_output_folder)
        layout.addWidget(self.pdf_button)
        layout.addWidget(self.open_button)
        layout.addStretch()
        outer_layout.addWidget(ScrollManager.wrap(content))

    def _refresh_summary(self) -> None:
        """Refresh summary labels from stored results."""
        if not self.results:
            self.best_label.setText("N/A")
            self.mean_label.setText("N/A")
            self.ligands_label.setText("0")
            self.poses_label.setText("N/A")
            return
        affinities = [float(row["affinity"]) for row in self.results]
        counts = Counter(row["ligand_name"] for row in self.results)
        self.best_label.setText(f"{min(affinities):.3f} kcal/mol")
        self.mean_label.setText(f"{sum(affinities) / len(affinities):.3f} kcal/mol")
        self.ligands_label.setText(str(len(counts)))
        self.poses_label.setText(
            ", ".join(f"{ligand}: {count}" for ligand, count in counts.items())
        )

    def _dynamic_results_table(self) -> Table:
        """Create top-results report table with dynamic scoring columns."""
        scoring_labels = sorted(
            {
                row.get("scoring_function", row.get("scoring_key", ""))
                for row in self.results
            }
        )
        data = [
            [
                I18n.get("rp_col_ligand", self.lang),
                I18n.get("rp_col_pose", self.lang),
                I18n.get("rp_col_docking_score", self.lang),
                *scoring_labels,
            ]
        ]
        grouped: dict[str, list[dict]] = {}
        for row in self.results:
            grouped.setdefault(row["ligand_name"], []).append(row)
        for ligand, rows in sorted(grouped.items()):
            for row in sorted(rows, key=lambda item: float(item.get("affinity", 0.0)))[
                :10
            ]:
                label = row.get("scoring_function", row.get("scoring_key", ""))
                data.append(
                    [
                        ligand,
                        str(row.get("pose_rank", row.get("mode", ""))),
                        f"{float(row.get('vina_affinity', row.get('affinity', 0.0))):.3f}",
                        *[
                            f"{float(row.get('affinity', 0.0)):.3f}"
                            if scoring == label
                            else ""
                            for scoring in scoring_labels
                        ],
                    ]
                )
        return self._styled_table(data)

    def _consensus_table(self) -> Table | Paragraph:
        """Create consensus ranking report table."""
        provider = self.analysis_provider
        if provider is None or len(provider._scoring_headers()) < 2:
            return Paragraph(
                I18n.get("rp_consensus_need_two", self.lang),
                getSampleStyleSheet()["Normal"],
            )
        rows = provider._build_consensus_rows(provider._scoring_headers())[:20]
        data = [
            [
                I18n.get("rp_col_ligand", self.lang),
                I18n.get("rp_col_pose", self.lang),
                I18n.get("rp_col_mean_rank", self.lang),
                I18n.get("rp_col_borda", self.lang),
                I18n.get("rp_col_zscore", self.lang),
                I18n.get("rp_col_divergence", self.lang),
            ]
        ]
        for row in rows:
            data.append(
                [
                    row["ligand"],
                    str(row["pose_rank"]),
                    str(row["mean_rank"]),
                    str(row["borda_count"]),
                    str(row["zscore_consensus"]),
                    row["divergence_flag"],
                ]
            )
        return self._styled_table(data)

    def _cluster_summary_table(self) -> Table | Paragraph:
        """Create cluster summary report table from ResultsTab clustering."""
        provider = self.analysis_provider
        if provider is None or not getattr(provider, "current_clusters", None):
            return Paragraph(
                I18n.get("rp_no_clusters", self.lang),
                getSampleStyleSheet()["Normal"],
            )
        data = [
            [
                I18n.get("rp_col_ligand", self.lang),
                I18n.get("rp_col_cluster_id", self.lang),
                I18n.get("rp_col_size", self.lang),
                I18n.get("rp_col_representative", self.lang),
                I18n.get("rp_col_best_score", self.lang),
            ]
        ]
        for cluster in provider.current_clusters:
            representative = cluster["representative"]
            data.append(
                [
                    cluster["ligand"],
                    str(cluster["cluster_id"]),
                    str(cluster["size"]),
                    str(
                        representative.get("pose_rank", representative.get("mode", ""))
                    ),
                    f"{float(cluster['best_score']):.3f}",
                ]
            )
        return self._styled_table(data)

    def _interaction_summary_table(self) -> Table | Paragraph:
        """Create top-residue interaction summary for the best pose per ligand."""
        provider = self.analysis_provider
        if provider is None:
            return Paragraph(
                I18n.get("rp_interactions_provider_missing", self.lang),
                getSampleStyleSheet()["Normal"],
            )
        try:
            from tabs.results_view import prepare_pose_view_files
        except ImportError:
            return Paragraph(
                I18n.get("rp_interaction_helpers_missing", self.lang),
                getSampleStyleSheet()["Normal"],
            )
        data = [
            [
                I18n.get("rp_col_ligand", self.lang),
                I18n.get("rp_col_top_residues", self.lang),
            ]
        ]
        grouped: dict[str, list[dict]] = {}
        for row in self.results:
            grouped.setdefault(row["ligand_name"], []).append(row)
        for ligand, rows in sorted(grouped.items()):
            best = min(rows, key=lambda item: float(item.get("affinity", 0.0)))
            try:
                view_dir = Path(tempfile.mkdtemp(prefix="vinalab_report_interactions_"))
                receptor_pdb, pose_pdb = prepare_pose_view_files(best, view_dir)
                interactions = provider._compute_pose_interactions(
                    best, receptor_pdb, pose_pdb
                )
                residues = Counter(
                    f"{item['residue_name']}{item['residue_number']}"
                    for item in interactions
                )
                summary = ", ".join(
                    f"{residue} ({count})" for residue, count in residues.most_common(5)
                ) or I18n.get("rp_no_contacts", self.lang)
            except Exception as exc:  # noqa: BLE001 - report should still be generated
                summary = I18n.get("rp_skipped", self.lang).format(exc=exc)
            data.append([ligand, summary])
        return self._styled_table(data)

    def _warnings_table(self) -> Table:
        """Create warnings/errors report table."""
        warnings = [
            row.get("scoring_error", "")
            for row in self.results
            if row.get("scoring_error")
        ]
        data = [
            [I18n.get("rp_col_type", self.lang), I18n.get("rp_col_message", self.lang)]
        ]
        if warnings:
            for message in warnings:
                data.append([I18n.get("rp_scoring", self.lang), message])
        else:
            data.append(
                [
                    I18n.get("rp_none", self.lang),
                    I18n.get("rp_no_scoring_errors", self.lang),
                ]
            )
        return self._styled_table(data)

    def _results_table(self) -> Table:
        """Create a reportlab table for current docking results."""
        data = [
            [
                I18n.get("ligand_col", self.lang),
                I18n.get("mode_col", self.lang),
                I18n.get("affinity_col", self.lang),
                I18n.get("rmsd_lb_col", self.lang),
                I18n.get("rmsd_ub_col", self.lang),
            ]
        ]
        for row in self.results:
            data.append(
                [
                    row["ligand_name"],
                    str(row["mode"]),
                    f"{float(row['affinity']):.3f}",
                    f"{float(row['rmsd_lb']):.3f}",
                    f"{float(row['rmsd_ub']):.3f}",
                ]
            )
        table = Table(data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4c3a75")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ]
            )
        )
        return table

    def _styled_table(self, data: list[list[str]]) -> Table:
        """Create a reportlab table with consistent styling."""
        table = Table(data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#C8922A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return table

    def _draw_footer(self, canvas, doc) -> None:
        """Draw the authorship footer on every PDF page."""
        canvas.saveState()
        footer = I18n.get("pdf_footer", self.lang).format(
            date=datetime.now().strftime("%Y-%m-%d")
        )
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(letter[0] / 2, 24, footer)
        canvas.restoreState()
