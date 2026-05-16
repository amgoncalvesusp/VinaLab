"""Results table, chart, exports, and live log tab."""

import base64
import html
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import statistics
import sys
import tempfile

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from openpyxl.styles import Font, PatternFill
from PySide6.QtCore import QPoint, QUrl, Signal, Qt
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSplitter,
    QSlider,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:  # pragma: no cover - installer should provide PySide6-WebEngine
    QWebEngineView = None

from core.docking_engine import convert_with_obabel, extract_pose_model, find_obabel_executable
from core.file_utils import clean_pdbqt_text
from core.i18n import I18n
from core.scrolling import ScrollManager

NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0

HEADER_TOOLTIPS = {
    "Ligante": "Nome do arquivo do ligante submetido ao docking",
    "Rank da pose": "Classificação da pose pelo score de docking (1 = melhor)",
    "Energia de docking (kcal/mol)": "Energia de ligação estimada. Valores mais negativos indicam maior afinidade",
    "Score de docking (kcal/mol)": "Energia de ligação estimada. Valores mais negativos indicam maior afinidade",
    "Afinidade (kcal/mol)": "Energia de ligação estimada. Valores mais negativos indicam maior afinidade",
    "ItaVinaXGB-Lig": "Score de afinidade previsto pelo modelo ItaVinaXGB para o ligante",
    "RTMScore": "Score de docking por aprendizado de máquina (RTMScore). Mais negativo = melhor",
    "Vinardo": "Score de docking Vinardo. Mais negativo = melhor afinidade estimada",
    "D para melhor (RMSD)": "Desvio quadrático médio em relação à melhor pose. Valores baixos indicam poses similares",
    "RMSD para melhor pose": "Desvio quadrático médio em relação à melhor pose. Valores baixos indicam poses similares",
    "Fixada": "Indica se a pose foi fixada/marcada pelo usuário",
    "Notas": "Anotações manuais do usuário para esta pose",
    "Rank médio": "Média dos ranks atribuídos por todas as funções de pontuação",
    "Pontuação Borda": "Pontuação combinada pelo método Borda Count",
    "Contagem Borda": "Pontuação combinada pelo método Borda Count",
    "Consenso Z-score": "Z-score do consenso entre múltiplas funções de pontuação",
    "DP dos ranks": "Desvio padrão dos ranks entre as funções de pontuação. Valores baixos = maior concordância",
    "Divergência": "Classificação qualitativa da concordância entre os scores (ex: Robust = alta concordância)",
    "Resíduo": "Resíduo do receptor envolvido na interação com a pose selecionada",
    "Tipo de interação": "Categoria da interação receptor-ligante estimada para a pose selecionada",
    "Doador": "Átomo doador identificado na interação",
    "Aceptor": "Átomo aceptor identificado na interação",
    "Distância (Å)": "Distância estimada entre os átomos envolvidos na interação",
    "Ângulo": "Ângulo estimado da interação quando aplicável",
    "Frequência Top 10": "Frequência da interação entre as 10 melhores poses do ligante",
    "ID do cluster": "Identificador do cluster de poses por RMSD",
    "Tamanho": "Número de poses agrupadas neste cluster",
    "Melhor score": "Melhor score de docking entre as poses do cluster",
    "Pose representante": "Pose escolhida para representar o cluster",
    "Membros": "Ranks das poses agrupadas neste cluster",
    "Erro de pontuação": "Mensagem de erro retornada por uma função de pontuação, se houver",
}


def apply_header_tooltips(table: QTableWidget) -> None:
    """Apply pt-BR tooltips to every visible column header in a table."""
    for column in range(table.columnCount()):
        item = table.horizontalHeaderItem(column)
        if item is None:
            continue
        header = item.text()
        item.setToolTip(HEADER_TOOLTIPS.get(header, _generic_header_tooltip(header)))


def _generic_header_tooltip(header: str) -> str:
    """Return a pt-BR fallback tooltip for dynamic or secondary table columns."""
    normalized = header.lower()
    if "itavina" in normalized:
        return HEADER_TOOLTIPS["ItaVinaXGB-Lig"]
    if "rtmscore" in normalized:
        return HEADER_TOOLTIPS["RTMScore"]
    if "vinardo" in normalized:
        return HEADER_TOOLTIPS["Vinardo"]
    if "score" in normalized or "vina" in normalized or "affinity" in normalized:
        return "Score de docking desta função de pontuação. Valores mais negativos indicam maior afinidade"
    if "cluster" in normalized:
        return "Informação do agrupamento de poses por RMSD"
    return f"Coluna {header} da tabela"


class ResultsTab(QWidget):
    """Display docking results and live docking logs."""

    results_changed = Signal(list)
    chart_updated = Signal(object)

    def __init__(self) -> None:
        """Create the results table, chart, export buttons, and log console."""
        super().__init__()
        self.lang = "pt"
        self.results: list[dict] = []
        self.filtered_results: list[dict] = []
        self.table_state: dict = {"pins": {}, "notes": {}, "filters": {}}
        self.state_path: Path | None = None
        self._state_loaded_for: Path | None = None
        self._rendering_table = False
        self._sort_criteria: list[tuple[str, bool]] = []
        self.chart_path: Path | None = None
        self.table = QTableWidget(0, 0)
        self.log_console = QTextEdit()
        self.figure = Figure(figsize=(8, 3), tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.excel_button = QPushButton()
        self.csv_button = QPushButton()
        self.filtered_export_button = QPushButton()
        self.view_button = QPushButton()
        self.compare_button = QPushButton()
        self.export_complex_button = QPushButton()
        self.ligand_filter = QLineEdit()
        self.scoring_filter_button = QToolButton()
        self.scoring_filter_menu = QMenu(self)
        self.scoring_filter_actions: dict[str, QAction] = {}
        self.affinity_min = self._range_spin(-9999.0)
        self.affinity_max = self._range_spin(9999.0)
        self.rmsd_min = self._range_spin(0.0)
        self.rmsd_max = self._range_spin(9999.0)
        self.pinned_only = QCheckBox()
        self.preview_status = QLabel()
        self.pose_detail_label = QLabel()
        self.preview_view = QWebEngineView() if QWebEngineView is not None else None
        self.preview_tabs = QTabWidget()
        self.interaction_cutoff = QComboBox()
        self.interaction_table = QTableWidget(0, 7)
        self.export_interactions_button = QPushButton()
        self.current_interactions: list[dict] = []
        self.current_interaction_row: dict | None = None
        self.current_box: dict | None = None
        self.current_preview_row: dict | None = None
        self.current_receptor_pdb: Path | None = None
        self.current_pose_pdb: Path | None = None
        self.current_receptor_path: Path | None = None
        self.consensus_widget = QWidget()
        self.consensus_table = QTableWidget(0, 0)
        self.consensus_tab_index = -1
        self.clusters_widget = QWidget()
        self.cluster_table = QTableWidget(0, 6)
        self.cluster_cutoff_slider = QSlider(Qt.Horizontal)
        self.cluster_cutoff_label = QLabel()
        self.cluster_export_button = QPushButton()
        self.cluster_figure = Figure(figsize=(4, 2), tight_layout=True)
        self.cluster_canvas = FigureCanvasQTAgg(self.cluster_figure)
        self.cluster_tab_index = -1
        self.current_clusters: list[dict] = []
        self.column_keys: list[str] = []
        self._build_ui()
        self.retranslate_ui(self.lang)

    def clear_results(self) -> None:
        """Clear existing table rows, chart, logs, and stored results."""
        self.results = []
        self.filtered_results = []
        self.table.setRowCount(0)
        self.consensus_table.setRowCount(0)
        self._set_consensus_tab_visible(False)
        self.cluster_table.setRowCount(0)
        self._set_clusters_tab_visible(False)
        self.current_clusters = []
        self.log_console.clear()
        self.figure.clear()
        self.canvas.draw_idle()
        self.results_changed.emit([])

    def add_results(self, rows: list[dict]) -> None:
        """Append result rows to the table and refresh the chart."""
        self.results.extend(rows)
        self._sync_state_path()
        self._refresh_scoring_filter_options()
        self._apply_filters()
        self._update_consensus_tab()
        self._update_clusters_tab()
        self._update_chart()
        self.results_changed.emit(list(self.results))

    def append_log(self, message: str) -> None:
        """Append a log message from the docking worker."""
        self.log_console.append(message.rstrip())

    def open_export_dialog(self) -> None:
        """Open the complex-export dialog."""
        if not self.results:
            QMessageBox.information(self, "Exportar complexo", "Não há poses de docking disponíveis para exportar.")
            return
        dialog = ExportComplexDialog(self.results, self)
        dialog.exec()

    def export_to_csv(self) -> None:
        """Export the full results table to CSV."""
        if not self.results:
            return
        file_name, _ = QFileDialog.getSaveFileName(self, I18n.get("export_csv_dialog", self.lang), "", "Arquivos CSV (*.csv)")
        if file_name:
            self._dataframe().to_csv(Path(file_name), index=False)

    def export_to_excel(self) -> None:
        """Export the full results table to Excel with basic formatting."""
        if not self.results:
            return
        file_name, _ = QFileDialog.getSaveFileName(self, I18n.get("export_excel_dialog", self.lang), "", "Excel Files (*.xlsx)")
        if not file_name:
            return
        output_path = Path(file_name)
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            self._dataframe().to_excel(writer, sheet_name="Results", index=False)
            worksheet = writer.book["Results"]
            for cell in worksheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="4C3A75")
            for row in range(2, worksheet.max_row + 1):
                affinity = worksheet.cell(row=row, column=4).value
                fill = self._excel_fill_for_affinity(float(affinity))
                for column in range(1, worksheet.max_column + 1):
                    worksheet.cell(row=row, column=column).fill = fill
            for column_cells in worksheet.columns:
                max_length = max(len(str(cell.value or "")) for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = max_length + 2

    def retranslate_ui(self, lang: str) -> None:
        """Retranslate results tab controls."""
        self.lang = lang
        self.excel_button.setText(I18n.get("export_excel", lang))
        self.csv_button.setText(I18n.get("export_csv", lang))
        self.filtered_export_button.setText(I18n.get("export_filtered_subset", lang))
        self.view_button.setText(I18n.get("view_selected_pose", lang))
        self.compare_button.setText(I18n.get("compare_button", lang))
        self.export_complex_button.setText(I18n.get("export_complex", lang))
        self.pinned_only.setText(I18n.get("pinned_only", lang))
        self.ligand_filter.setPlaceholderText(I18n.get("ligand_name_filter", lang))
        self.scoring_filter_button.setText(I18n.get("scoring_all", lang))
        self.preview_status.setText(I18n.get("select_pose_preview", lang))
        self.export_interactions_button.setText(I18n.get("export_interaction_table", lang))
        self.cluster_export_button.setText(I18n.get("export_best_cluster", lang))
        self.preview_tabs.setTabText(0, I18n.get("results_table", lang))
        if self.preview_tabs.count() > 1:
            self.preview_tabs.setTabText(1, I18n.get("interactions", lang))
        consensus_index = self._side_tab_index(self.consensus_widget)
        if consensus_index >= 0:
            self.preview_tabs.setTabText(consensus_index, I18n.get("consensus", lang))
        clusters_index = self._side_tab_index(self.clusters_widget)
        if clusters_index >= 0:
            self.preview_tabs.setTabText(clusters_index, I18n.get("clusters", lang))
        self.excel_button.setToolTip(I18n.get("export_excel", lang))
        self.csv_button.setToolTip(I18n.get("export_csv", lang))
        self.filtered_export_button.setToolTip("Exporta apenas as linhas visíveis no momento.")
        self.view_button.setToolTip("Abre o complexo receptor-pose selecionado no PyMOL.")
        self.compare_button.setToolTip("Compara poses, referências cristalográficas ou funções de pontuação.")
        self.export_complex_button.setToolTip("Exporta complexos de docking selecionados ou filtrados.")
        self.export_interactions_button.setToolTip("Exporta as interações da pose selecionada como CSV.")
        self.cluster_export_button.setToolTip("Exporta poses representativas de cada cluster por RMSD.")
        self._refresh_scoring_filter_button()
        self._update_chart()

    def _build_ui(self) -> None:
        """Build the results tab layout."""
        layout = QVBoxLayout(self)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSortingEnabled(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.cellClicked.connect(lambda _row, _column: self.load_selected_pose_preview())
        self.table.cellDoubleClicked.connect(lambda _row, _column: self.view_selected_pose())
        self.table.itemChanged.connect(self._table_item_changed)
        self.table.horizontalHeader().sectionClicked.connect(self._header_clicked)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._open_context_menu)
        ScrollManager.optimize(self.table)
        self.log_console.setReadOnly(True)
        self.log_console.setObjectName("log_console")
        ScrollManager.optimize(self.log_console)

        filter_row = QHBoxLayout()
        self.ligand_filter.textChanged.connect(self._apply_filters)
        self.scoring_filter_button.setMenu(self.scoring_filter_menu)
        self.scoring_filter_button.setPopupMode(QToolButton.InstantPopup)
        self.affinity_min.valueChanged.connect(self._apply_filters)
        self.affinity_max.valueChanged.connect(self._apply_filters)
        self.rmsd_min.valueChanged.connect(self._apply_filters)
        self.rmsd_max.valueChanged.connect(self._apply_filters)
        self.pinned_only.toggled.connect(self._apply_filters)
        filter_row.addWidget(QLabel(I18n.get("ligand_col", self.lang)))
        filter_row.addWidget(self.ligand_filter, stretch=2)
        filter_row.addWidget(self.scoring_filter_button)
        filter_row.addWidget(QLabel(I18n.get("affinity_col", self.lang)))
        filter_row.addWidget(self.affinity_min)
        filter_row.addWidget(self.affinity_max)
        filter_row.addWidget(QLabel("RMSD"))
        filter_row.addWidget(self.rmsd_min)
        filter_row.addWidget(self.rmsd_max)
        filter_row.addWidget(self.pinned_only)

        results_panel = QWidget()
        results_layout = QVBoxLayout(results_panel)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.addLayout(filter_row)
        results_layout.addWidget(self.table)

        button_row = QHBoxLayout()
        self.excel_button.clicked.connect(self.export_to_excel)
        self.csv_button.clicked.connect(self.export_to_csv)
        self.filtered_export_button.clicked.connect(self.export_filtered_subset)
        self.view_button.clicked.connect(self.view_selected_pose)
        self.compare_button.clicked.connect(self.open_comparison_dialog)
        button_row.addWidget(self.view_button)
        button_row.addWidget(self.compare_button)
        button_row.addWidget(self.filtered_export_button)
        button_row.addWidget(self.excel_button)
        button_row.addWidget(self.csv_button)
        button_row.addStretch()
        results_layout.addWidget(self.canvas, stretch=1)
        results_layout.addLayout(button_row)
        results_layout.addWidget(self.log_console, stretch=1)

        interaction_widget = QWidget()
        interaction_layout = QVBoxLayout(interaction_widget)
        interaction_layout.setContentsMargins(0, 0, 0, 0)
        interaction_controls = QHBoxLayout()
        self.interaction_cutoff.addItems(["4", "5", "6"])
        self.interaction_cutoff.setCurrentText("4")
        self.interaction_cutoff.currentTextChanged.connect(lambda _value: self._refresh_interactions_for_selected_pose())
        self.export_interactions_button.clicked.connect(self.export_interaction_table)
        interaction_controls.addWidget(QLabel(I18n.get("contact_cutoff", self.lang)))
        interaction_controls.addWidget(self.interaction_cutoff)
        interaction_controls.addWidget(self.export_interactions_button)
        interaction_controls.addStretch()
        self.interaction_table.setHorizontalHeaderLabels(
            [
                I18n.get("residue", self.lang),
                I18n.get("interaction_type", self.lang),
                I18n.get("donor", self.lang),
                I18n.get("acceptor", self.lang),
                I18n.get("distance_a", self.lang),
                I18n.get("angle", self.lang),
                I18n.get("frequency_top10", self.lang),
            ]
        )
        apply_header_tooltips(self.interaction_table)
        self.interaction_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.interaction_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        ScrollManager.optimize(self.interaction_table)
        interaction_layout.addLayout(interaction_controls)
        interaction_layout.addWidget(self.interaction_table, stretch=1)

        consensus_layout = QVBoxLayout(self.consensus_widget)
        consensus_layout.setContentsMargins(0, 0, 0, 0)
        consensus_hint = QLabel("O ranking de consenso fica disponível após a conclusão de 2 ou mais funções de pontuação.")
        consensus_hint.setObjectName("label_muted")
        self.consensus_table.setSortingEnabled(True)
        self.consensus_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.consensus_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        ScrollManager.optimize(self.consensus_table)
        consensus_layout.addWidget(consensus_hint)
        consensus_layout.addWidget(self.consensus_table, stretch=1)

        clusters_layout = QVBoxLayout(self.clusters_widget)
        clusters_layout.setContentsMargins(0, 0, 0, 0)
        cluster_controls = QHBoxLayout()
        self.cluster_cutoff_slider.setRange(50, 500)
        self.cluster_cutoff_slider.setValue(200)
        self.cluster_cutoff_slider.valueChanged.connect(self._cluster_cutoff_changed)
        self.cluster_export_button.clicked.connect(self.export_cluster_representatives)
        self.cluster_cutoff_label.setText("RMSD cutoff: 2.0 Å")
        cluster_controls.addWidget(self.cluster_cutoff_label)
        cluster_controls.addWidget(self.cluster_cutoff_slider, stretch=1)
        cluster_controls.addWidget(self.cluster_export_button)
        self.cluster_table.setHorizontalHeaderLabels(
            [
                I18n.get("ligand_col", self.lang),
                I18n.get("cluster_id", self.lang),
                I18n.get("cluster_size", self.lang),
                I18n.get("best_score", self.lang),
                I18n.get("representative_pose", self.lang),
                I18n.get("members", self.lang),
            ]
        )
        apply_header_tooltips(self.cluster_table)
        self.cluster_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cluster_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.cluster_table.cellClicked.connect(self._cluster_row_clicked)
        ScrollManager.optimize(self.cluster_table)
        clusters_layout.addLayout(cluster_controls)
        clusters_layout.addWidget(self.cluster_table, stretch=2)
        clusters_layout.addWidget(self.cluster_canvas, stretch=1)

        self.preview_tabs.addTab(results_panel, I18n.get("results_table", self.lang))
        self.preview_tabs.addTab(interaction_widget, I18n.get("interactions", self.lang))

        analysis_panel = QWidget()
        analysis_layout = QVBoxLayout(analysis_panel)
        analysis_layout.setContentsMargins(0, 0, 0, 0)
        self.pose_detail_label.setObjectName("label_muted")
        self.pose_detail_label.setWordWrap(True)
        self.pose_detail_label.setText("Nenhuma pose selecionada.")
        self.export_complex_button.clicked.connect(self.open_export_dialog)
        analysis_layout.addWidget(self.preview_tabs, stretch=1)
        analysis_layout.addWidget(self.pose_detail_label)
        analysis_layout.addWidget(self.export_complex_button)

        layout.addWidget(analysis_panel, stretch=1)

    def _populate_table(self) -> None:
        """Render stored result rows into the QTableWidget."""
        scoring_headers = self._scoring_headers()
        headers = [
            I18n.get("ligand_col", self.lang),
            I18n.get("pose_rank", self.lang),
            I18n.get("docking_score", self.lang),
            *scoring_headers,
            I18n.get("rmsd_best_pose", self.lang),
            I18n.get("pinned", self.lang),
            I18n.get("notes", self.lang),
            I18n.get("scoring_error", self.lang),
        ]
        self.column_keys = [
            "ligand_name",
            "pose_rank",
            "docking_score",
            *[f"score::{header}" for header in scoring_headers],
            "rmsd_lb",
            "pinned",
            "notes",
            "scoring_error",
        ]
        self._rendering_table = True
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        apply_header_tooltips(self.table)
        self.table.setRowCount(len(self.filtered_results))
        for row_index, row in enumerate(self.filtered_results):
            values = self._table_values(row, scoring_headers)
            background = self._color_for_affinity(float(row.get("affinity", 0.0)))
            row_id = self._row_id(row)
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, row_id)
                key = self.column_keys[column_index]
                if key == "pinned":
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    item.setCheckState(Qt.Checked if self._row_pinned(row) else Qt.Unchecked)
                    item.setText("")
                elif key == "notes":
                    item.setFlags(item.flags() | Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                else:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if self._numeric_column(key) and value != "":
                    item.setData(Qt.DisplayRole, float(value) if key != "pose_rank" else int(value))
                item.setBackground(background)
                self.table.setItem(row_index, column_index, item)
        self._rendering_table = False

    def _update_chart(self) -> None:
        """Refresh the embedded affinity distribution bar chart."""
        self.figure.clear()
        axis = self.figure.add_subplot(111)
        rows = self.filtered_results if self.filtered_results else self.results
        if rows:
            labels = [
                f"{row['ligand_name']} {row.get('scoring_function', row.get('scoring_key', ''))} #{row['mode']}"
                for row in rows
            ]
            affinities = [float(row["affinity"]) for row in rows]
            axis.bar(range(len(affinities)), affinities, color="#7c5cbf")
            axis.set_xticks(range(len(labels)))
            axis.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
            axis.set_ylabel(I18n.get("affinity_col", self.lang))
            axis.set_title(I18n.get("chart_title", self.lang))
        self.canvas.draw_idle()
        self.chart_path = Path(tempfile.gettempdir()) / "vinalab_affinity_chart.png"
        self.figure.savefig(self.chart_path, dpi=160, bbox_inches="tight")
        self.chart_updated.emit(self.chart_path)

    def _dataframe(self, rows: list[dict] | None = None) -> pd.DataFrame:
        """Return results as a pandas DataFrame."""
        rows = self.results if rows is None else rows
        return pd.DataFrame(
            [
                ({
                    "Ligand name": row["ligand_name"],
                    "Scoring": row.get("scoring_function", row.get("scoring_key", "")),
                    "Mode #": row["mode"],
                    "Affinity (kcal/mol)": row["affinity"],
                    "Vina affinity (kcal/mol)": row.get("vina_affinity", ""),
                    "RMSD l.b.": row["rmsd_lb"],
                    "RMSD u.b.": row["rmsd_ub"],
                    "Scoring error": row.get("scoring_error", ""),
                    "Pinned": self._row_pinned(row),
                    "Notes": self._row_note(row),
                    "CNNscore": row.get("cnn_score", ""),
                    "CNNaffinity": row.get("cnn_affinity", ""),
                    "Output file": row.get("output_file", ""),
                } | {
                    header: row.get("affinity", "") if row.get("scoring_function", row.get("scoring_key", "")) == header else ""
                    for header in self._scoring_headers()
                })
                for row in rows
            ]
        )

    def _update_gnina_columns(self) -> None:
        """Show GNINA CNN columns only when GNINA values are present."""
        has_gnina = any("cnn_score" in row or "cnn_affinity" in row for row in self.results)
        self.table.setColumnHidden(8, not has_gnina)
        self.table.setColumnHidden(9, not has_gnina)

    def _update_headers(self) -> None:
        """Set headers, including dynamic post-scoring columns."""
        dynamic_headers = self._scoring_headers()
        self.table.setHorizontalHeaderLabels(
            [
                I18n.get("ligand_col", self.lang),
                "Scoring",
                I18n.get("mode_col", self.lang),
                I18n.get("affinity_col", self.lang),
                "Vina affinity",
                I18n.get("rmsd_lb_col", self.lang),
                I18n.get("rmsd_ub_col", self.lang),
                "Scoring error",
                I18n.get("col_cnn_score", self.lang),
                I18n.get("col_cnn_affinity", self.lang),
                *dynamic_headers,
            ]
        )

    def view_selected_pose(self) -> None:
        """Open the selected receptor-pose complex in PyMOL."""
        row = self._selected_result_row()
        if row is None:
            QMessageBox.information(self, "Visualizar pose", "Selecione uma pose de docking na tabela de resultados.")
            return
        pymol_exe = shutil.which("pymol")
        if pymol_exe is None:
            QMessageBox.warning(
                self,
                "PyMOL",
                "PyMOL não foi encontrado no PATH do sistema.\n"
                "Instale o PyMOL e certifique-se de que está acessível via linha de comando.",
            )
            return
        try:
            output_file = Path(row.get("output_file", ""))
            receptor_file = Path(row.get("receptor_file", ""))
            if not output_file.is_absolute():
                output_file = output_file.resolve()
            if not receptor_file.is_absolute():
                receptor_file = receptor_file.resolve()
            if not output_file.exists():
                raise FileNotFoundError(f"Arquivo de saída não encontrado: {output_file}")
            view_dir = Path(tempfile.mkdtemp(prefix="vinalab_pymol_"))
            pose_name = f"{safe_export_name(row['ligand_name'])}_pose{int(row['mode'])}.pdbqt"
            pose_file = view_dir / pose_name
            pose_text = extract_pose_model(output_file, int(row["mode"]), include_model=False)
            pose_file.write_text(pose_text, encoding="utf-8")
            cmd_args = [pymol_exe]
            if receptor_file.exists():
                cmd_args.append(str(receptor_file))
            cmd_args.append(str(pose_file))
            subprocess.Popen(cmd_args, creationflags=NO_WINDOW)
        except Exception as exc:  # noqa: BLE001 - surface file/pose extraction errors to the user
            QMessageBox.critical(self, "PyMOL", f"Erro ao abrir pose no PyMOL.\n{exc}")

    def open_comparison_dialog(self) -> None:
        """Open pose/scoring comparison tools."""
        if not self.results:
            QMessageBox.information(self, "Comparar", "Não há poses de docking disponíveis para comparar.")
            return
        ComparisonDialog(self.results, self).exec()

    def show_validation_report(self, rows: list[dict], reference_path: Path, top_n: int) -> None:
        """Open the protocol-validation report dialog."""
        if not rows:
            QMessageBox.warning(self, "Validar protocolo", "O docking de validação não produziu poses.")
            return
        ProtocolValidationDialog(rows, reference_path, top_n, self).exec()

    def update_box_preview(self, box: dict) -> None:
        """Store the current box parameters (viewer removed in v1.1)."""
        self.current_box = dict(box)

    def update_receptor_preview(self, receptor_path: "Path | None") -> None:
        """Store the receptor path for PyMOL visualization."""
        self.current_receptor_path = receptor_path if receptor_path and receptor_path.exists() else None

    def _selected_result_row(self) -> dict | None:
        """Return the stored result row matching the current table selection."""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            return None
        item = self.table.item(selected_row, 0)
        if item is None:
            return None
        row_id = item.data(Qt.UserRole)
        return next((row for row in self.results if self._row_id(row) == row_id), None)

    def load_selected_pose_preview(self) -> None:
        """Load the selected pose into the Py3Dmol preview and interaction panel."""
        row = self._selected_result_row()
        if row is None:
            return
        self._load_pose_preview(row)

    def _load_pose_preview(self, row: dict) -> None:
        """Load one result row into the interactions table."""
        try:
            view_dir = Path(tempfile.mkdtemp(prefix="vinalab_preview_"))
            receptor_pdb, pose_pdb = prepare_pose_view_files(row, view_dir)
            interactions = self._compute_pose_interactions(row, receptor_pdb, pose_pdb)
            self._populate_interaction_table(interactions)
            self.current_preview_row = dict(row)
            self.current_receptor_pdb = receptor_pdb
            self.current_pose_pdb = pose_pdb
            note = self._row_note(row)
            self.pose_detail_label.setText(
                f"Ligante: {row['ligand_name']} | Score: {float(row.get('affinity', 0.0)):.3f} kcal/mol | "
                f"Rank: {int(row.get('pose_rank', row.get('mode', 0)))} | Notas: {note or '-'}"
            )
        except Exception as exc:  # noqa: BLE001 - preview errors should not interrupt result browsing
            self.preview_status.setText(f"Erro ao carregar visualização 3D. Verifique os arquivos de entrada. {exc}")

    def export_filtered_subset(self) -> None:
        """Export currently visible result rows to CSV."""
        if not self.filtered_results:
            QMessageBox.information(self, "Exportar subconjunto filtrado", "Não há linhas visíveis para exportar.")
            return
        file_name, _ = QFileDialog.getSaveFileName(self, "Exportar subconjunto filtrado", "", "Arquivos CSV (*.csv)")
        if file_name:
            self._dataframe(self.filtered_results).to_csv(Path(file_name), index=False)

    def export_interaction_table(self) -> None:
        """Export interactions for the selected pose to CSV."""
        if not self.current_interactions:
            QMessageBox.information(self, "Exportar tabela de interações", "Não há interações disponíveis para a pose selecionada.")
            return
        file_name, _ = QFileDialog.getSaveFileName(self, "Exportar tabela de interações", "", "Arquivos CSV (*.csv)")
        if not file_name:
            return
        rows = [
            {
                "ligand": item["ligand"],
                "pose_rank": item["pose_rank"],
                "residue_name": item["residue_name"],
                "residue_number": item["residue_number"],
                "interaction_type": item["interaction_type"],
                "distance_Å": item["distance_A"],
                "frequency_top10": item["frequency_top10"],
            }
            for item in self.current_interactions
        ]
        pd.DataFrame(rows).to_csv(Path(file_name), index=False)

    def _refresh_interactions_for_selected_pose(self) -> None:
        """Recompute interaction analysis when the cutoff selector changes."""
        if self._selected_result_row() is not None:
            self.load_selected_pose_preview()

    def _populate_interaction_table(self, interactions: list[dict]) -> None:
        """Render the selected pose interaction rows."""
        self.current_interactions = interactions
        self.current_interaction_row = self._selected_result_row()
        self.interaction_table.setRowCount(len(interactions))
        for row_index, item in enumerate(interactions):
            values = [
                f"{item['residue_name']} {item['residue_number']}",
                item["interaction_type"],
                item.get("donor", ""),
                item.get("acceptor", ""),
                f"{float(item['distance_A']):.2f}" if item.get("distance_A") != "" else "",
                item.get("angle", ""),
                f"{float(item['frequency_top10']):.2f}",
            ]
            for column_index, value in enumerate(values):
                self.interaction_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))

    def _compute_pose_interactions(self, row: dict, receptor_pdb: Path, pose_pdb: Path) -> list[dict]:
        """Compute receptor-ligand interactions for a selected pose using MDAnalysis."""
        try:
            import MDAnalysis as mda
            import numpy as np
            from MDAnalysis.lib.distances import distance_array
        except ImportError as exc:
            self.preview_status.setText(f"MDAnalysis está indisponível; interações ignoradas: {exc}")
            return []

        cutoff = float(self.interaction_cutoff.currentText() or 4.0)
        receptor = mda.Universe(str(receptor_pdb))
        ligand = mda.Universe(str(pose_pdb))
        receptor_atoms = receptor.select_atoms("not name H*")
        ligand_atoms = ligand.select_atoms("not name H*")
        if len(receptor_atoms) == 0 or len(ligand_atoms) == 0:
            return []

        distances = distance_array(receptor_atoms.positions, ligand_atoms.positions)
        interactions_by_key: dict[tuple[str, str, str], dict] = {}
        frequency_by_residue = self._contact_frequency_top10(row, cutoff)

        def add_interaction(rec_atom, lig_atom, interaction_type: str, distance: float, donor: str = "", acceptor: str = "", angle: str = "") -> None:
            residue_key = self._residue_key(rec_atom)
            key = (residue_key[0], residue_key[1], interaction_type)
            previous = interactions_by_key.get(key)
            if previous is not None and float(previous["distance_A"]) <= float(distance):
                return
            interactions_by_key[key] = {
                "ligand": row["ligand_name"],
                "pose_rank": int(row.get("pose_rank", row.get("mode", 0))),
                "residue_name": residue_key[0],
                "residue_number": residue_key[1],
                "interaction_type": interaction_type,
                "distance_A": round(float(distance), 3),
                "frequency_top10": round(float(frequency_by_residue.get((residue_key[0], residue_key[1]), 0.0)), 3),
                "donor": donor,
                "acceptor": acceptor,
                "angle": angle,
            }

        for rec_index, lig_index in np.argwhere(distances <= cutoff):
            rec_atom = receptor_atoms[int(rec_index)]
            lig_atom = ligand_atoms[int(lig_index)]
            add_interaction(rec_atom, lig_atom, "Contact", float(distances[rec_index, lig_index]))

        for rec_index, lig_index in np.argwhere(distances <= 4.0):
            rec_atom = receptor_atoms[int(rec_index)]
            lig_atom = ligand_atoms[int(lig_index)]
            if self._atom_element(rec_atom) == "C" and self._atom_element(lig_atom) == "C":
                add_interaction(rec_atom, lig_atom, "Hydrophobic", float(distances[rec_index, lig_index]))

        polar_elements = {"N", "O", "S"}
        for rec_index, lig_index in np.argwhere(distances <= 3.5):
            rec_atom = receptor_atoms[int(rec_index)]
            lig_atom = ligand_atoms[int(lig_index)]
            if self._atom_element(rec_atom) not in polar_elements or self._atom_element(lig_atom) not in polar_elements:
                continue
            angle = self._estimate_hbond_angle(rec_atom, lig_atom)
            add_interaction(
                rec_atom,
                lig_atom,
                "H-bond",
                float(distances[rec_index, lig_index]),
                donor=self._atom_label(lig_atom),
                acceptor=self._atom_label(rec_atom),
                angle=angle,
            )

        return sorted(
            interactions_by_key.values(),
            key=lambda item: (item["residue_number"], item["interaction_type"], float(item["distance_A"])),
        )

    def _contact_frequency_top10(self, row: dict, cutoff: float) -> dict[tuple[str, str], float]:
        """Return residue contact frequency across the top 10 poses of the same ligand."""
        same_ligand = [item for item in self.results if item.get("ligand_name") == row.get("ligand_name")]
        top_rows = sorted(same_ligand, key=self._docking_score)[:10]
        if not top_rows:
            return {}
        counts: dict[tuple[str, str], int] = {}
        attempted = 0
        for top_row in top_rows:
            try:
                view_dir = Path(tempfile.mkdtemp(prefix="vinalab_contacts_"))
                receptor_pdb, pose_pdb = prepare_pose_view_files(top_row, view_dir)
                for residue_key in self._contact_residue_keys(receptor_pdb, pose_pdb, cutoff):
                    counts[residue_key] = counts.get(residue_key, 0) + 1
                attempted += 1
            except Exception:
                continue
        if attempted == 0:
            return {}
        return {key: value / attempted for key, value in counts.items()}

    def _contact_residue_keys(self, receptor_pdb: Path, pose_pdb: Path, cutoff: float) -> set[tuple[str, str]]:
        """Return receptor residues within cutoff of a ligand pose."""
        import MDAnalysis as mda
        import numpy as np
        from MDAnalysis.lib.distances import distance_array

        receptor = mda.Universe(str(receptor_pdb))
        ligand = mda.Universe(str(pose_pdb))
        receptor_atoms = receptor.select_atoms("not name H*")
        ligand_atoms = ligand.select_atoms("not name H*")
        if len(receptor_atoms) == 0 or len(ligand_atoms) == 0:
            return set()
        distances = distance_array(receptor_atoms.positions, ligand_atoms.positions)
        return {self._residue_key(receptor_atoms[int(rec_index)]) for rec_index, _lig_index in np.argwhere(distances <= cutoff)}

    def _estimate_hbond_angle(self, donor_atom, acceptor_atom) -> str:
        """Estimate a D-H-A angle when explicit hydrogens are present."""
        try:
            import numpy as np
        except ImportError:
            return "N/A"
        hydrogens = [atom for atom in donor_atom.residue.atoms if self._atom_element(atom) == "H"]
        best_angle: float | None = None
        for hydrogen in hydrogens:
            donor_distance = float(np.linalg.norm(hydrogen.position - donor_atom.position))
            if donor_distance > 1.25:
                continue
            vector_donor = donor_atom.position - hydrogen.position
            vector_acceptor = acceptor_atom.position - hydrogen.position
            denominator = float(np.linalg.norm(vector_donor) * np.linalg.norm(vector_acceptor))
            if denominator == 0:
                continue
            cosine = float(np.clip(np.dot(vector_donor, vector_acceptor) / denominator, -1.0, 1.0))
            angle = float(np.degrees(np.arccos(cosine)))
            best_angle = angle if best_angle is None else max(best_angle, angle)
        return f"{best_angle:.1f}" if best_angle is not None else "N/A"

    @staticmethod
    def _atom_element(atom) -> str:
        """Best-effort atom element extraction for PDB/PDBQT-derived files."""
        element = str(getattr(atom, "element", "") or "").strip()
        if element:
            return element.upper()[:1]
        name = str(getattr(atom, "name", "") or "").strip()
        letters = "".join(char for char in name if char.isalpha())
        return letters.upper()[:1] if letters else ""

    @staticmethod
    def _atom_label(atom) -> str:
        """Return a readable atom label."""
        resname = str(getattr(atom, "resname", "") or "").strip()
        resid = str(getattr(atom, "resid", "") or "").strip()
        name = str(getattr(atom, "name", "") or "").strip()
        return f"{resname}{resid}:{name}" if resname or resid else name

    @staticmethod
    def _residue_key(atom) -> tuple[str, str]:
        """Return residue name/number for a receptor atom."""
        return (
            str(getattr(atom, "resname", "") or "").strip(),
            str(getattr(atom, "resid", "") or "").strip(),
        )

    def _set_consensus_tab_visible(self, visible: bool) -> None:
        """Add or remove the consensus tab from the preview/result side panel."""
        current_index = self._side_tab_index(self.consensus_widget)
        if visible and current_index < 0:
            self.consensus_tab_index = self.preview_tabs.addTab(self.consensus_widget, I18n.get("consensus", self.lang))
        elif not visible and current_index >= 0:
            self.preview_tabs.removeTab(current_index)
            self.consensus_tab_index = -1
        else:
            self.consensus_tab_index = current_index

    def _set_clusters_tab_visible(self, visible: bool) -> None:
        """Add or remove the clusters tab from the preview/result side panel."""
        current_index = self._side_tab_index(self.clusters_widget)
        if visible and current_index < 0:
            self.cluster_tab_index = self.preview_tabs.addTab(self.clusters_widget, I18n.get("clusters", self.lang))
        elif not visible and current_index >= 0:
            self.preview_tabs.removeTab(current_index)
            self.cluster_tab_index = -1
        else:
            self.cluster_tab_index = current_index

    def _side_tab_index(self, widget: QWidget) -> int:
        """Return the current index of a side-panel tab widget."""
        for index in range(self.preview_tabs.count()):
            if self.preview_tabs.widget(index) is widget:
                return index
        return -1

    def _update_consensus_tab(self) -> None:
        """Compute consensus ranking when two or more scoring functions are present."""
        scoring_labels = self._scoring_headers()
        if len(scoring_labels) < 2:
            self._set_consensus_tab_visible(False)
            return

        self._set_consensus_tab_visible(True)
        consensus_rows = self._build_consensus_rows(scoring_labels)
        headers = [
            I18n.get("ligand_col", self.lang),
            I18n.get("pose_rank", self.lang),
            *scoring_labels,
            I18n.get("mean_rank", self.lang),
            I18n.get("borda_count", self.lang),
            I18n.get("zscore_consensus", self.lang),
            I18n.get("rank_sd", self.lang),
            I18n.get("divergence_flag", self.lang),
        ]
        self.consensus_table.setSortingEnabled(False)
        self.consensus_table.clear()
        self.consensus_table.setColumnCount(len(headers))
        self.consensus_table.setHorizontalHeaderLabels(headers)
        apply_header_tooltips(self.consensus_table)
        self.consensus_table.setRowCount(len(consensus_rows))
        for row_index, item in enumerate(consensus_rows):
            background = self._consensus_color(row_index, len(consensus_rows))
            values = [
                item["ligand"],
                item["pose_rank"],
                *[item["scores"].get(label, "") for label in scoring_labels],
                item["mean_rank"],
                item["borda_count"],
                item["zscore_consensus"],
                item["rank_sd"],
                item["divergence_flag"],
            ]
            for column_index, value in enumerate(values):
                table_item = QTableWidgetItem(str(value))
                if isinstance(value, (int, float)):
                    table_item.setData(Qt.DisplayRole, round(float(value), 3))
                table_item.setBackground(background)
                self.consensus_table.setItem(row_index, column_index, table_item)
        self.consensus_table.setSortingEnabled(True)

    def _build_consensus_rows(self, scoring_labels: list[str]) -> list[dict]:
        """Build consensus metrics across active scoring functions."""
        pose_scores: dict[tuple[str, int], dict] = {}
        for row in self.results:
            scoring_label = row.get("scoring_function", row.get("scoring_key", ""))
            if scoring_label not in scoring_labels:
                continue
            pose_key = self._pose_identity(row)
            entry = pose_scores.setdefault(
                pose_key,
                {"ligand": pose_key[0], "pose_rank": pose_key[1], "scores": {}},
            )
            score = float(row.get("affinity", 0.0))
            previous_score = entry["scores"].get(scoring_label)
            if previous_score is None or score < float(previous_score):
                entry["scores"][scoring_label] = score

        rank_by_label: dict[str, dict[tuple[str, int], int]] = {}
        zscore_by_label: dict[str, dict[tuple[str, int], float]] = {}
        pose_count = len(pose_scores)
        for label in scoring_labels:
            score_rows = [(pose_key, data["scores"][label]) for pose_key, data in pose_scores.items() if label in data["scores"]]
            score_rows.sort(key=lambda item: float(item[1]))
            rank_by_label[label] = {pose_key: rank for rank, (pose_key, _score) in enumerate(score_rows, start=1)}
            values = [float(score) for _pose_key, score in score_rows]
            mean_value = statistics.mean(values) if values else 0.0
            stdev_value = statistics.pstdev(values) if len(values) > 1 else 1.0
            if stdev_value == 0:
                stdev_value = 1.0
            zscore_by_label[label] = {
                pose_key: (float(score) - mean_value) / stdev_value
                for pose_key, score in score_rows
            }

        consensus_rows: list[dict] = []
        for pose_key, data in pose_scores.items():
            available_labels = [label for label in scoring_labels if pose_key in rank_by_label[label]]
            if len(available_labels) < 2:
                continue
            ranks = [rank_by_label[label][pose_key] for label in available_labels]
            mean_rank = statistics.mean(ranks)
            borda_count = sum(pose_count - rank for rank in ranks)
            zscore_consensus = sum(zscore_by_label[label][pose_key] for label in available_labels)
            rank_sd = statistics.pstdev(ranks) if len(ranks) > 1 else 0.0
            consensus_rows.append(
                {
                    "ligand": data["ligand"],
                    "pose_rank": data["pose_rank"],
                    "scores": data["scores"],
                    "mean_rank": round(float(mean_rank), 3),
                    "borda_count": int(borda_count),
                    "zscore_consensus": round(float(zscore_consensus), 3),
                    "rank_sd": round(float(rank_sd), 3),
                    "divergence_flag": "Robust" if rank_sd <= 1.0 else "⚠ Controversial",
                }
            )
        return sorted(consensus_rows, key=lambda item: (float(item["mean_rank"]), float(item["zscore_consensus"])))

    @staticmethod
    def _pose_identity(row: dict) -> tuple[str, int]:
        """Return the grouping key used for consensus metrics."""
        return (str(row.get("ligand_name", "")), int(row.get("pose_rank", row.get("mode", 0))))

    @staticmethod
    def _consensus_color(row_index: int, row_count: int) -> QColor:
        """Return quartile color for consensus ranking rows."""
        if row_count <= 1:
            return QColor("#d8ead3")
        percentile = row_index / max(row_count - 1, 1)
        if percentile <= 0.25:
            return QColor("#d8ead3")
        if percentile >= 0.75:
            return QColor("#f2c6bd")
        return QColor("#f5e6a6")

    def _cluster_cutoff_changed(self, value: int) -> None:
        """Update RMSD cluster cutoff from the slider."""
        self.cluster_cutoff_label.setText(f"RMSD cutoff: {value / 100:.1f} Å")
        self._update_clusters_tab()

    def _update_clusters_tab(self) -> None:
        """Compute and render RMSD pose clusters."""
        if not self.results:
            self._set_clusters_tab_visible(False)
            return
        self._set_clusters_tab_visible(True)
        try:
            self.current_clusters = self._build_pose_clusters(self.cluster_cutoff_slider.value() / 100)
        except ImportError as exc:
            self.current_clusters = []
            self.cluster_table.setRowCount(1)
            self.cluster_table.setColumnCount(1)
            self.cluster_table.setHorizontalHeaderLabels(["Clusters"])
            apply_header_tooltips(self.cluster_table)
            self.cluster_table.setItem(0, 0, QTableWidgetItem(f"scipy está indisponível: {exc}"))
            return
        self._populate_cluster_table()
        self._update_cluster_histogram()

    def _build_pose_clusters(self, cutoff: float) -> list[dict]:
        """Cluster poses of each ligand by heavy-atom RMSD."""
        import numpy as np
        from scipy.cluster.hierarchy import fcluster, linkage
        from scipy.spatial.distance import squareform

        clusters: list[dict] = []
        grouped_rows: dict[str, list[dict]] = {}
        for row in self.results:
            grouped_rows.setdefault(str(row.get("ligand_name", "")), []).append(row)

        for ligand_name, rows in sorted(grouped_rows.items()):
            prepared: list[tuple[dict, object]] = []
            for row in rows:
                try:
                    coordinates = self._pose_heavy_coordinates(row)
                except Exception:
                    continue
                if len(coordinates) > 0:
                    prepared.append((row, coordinates))
            if not prepared:
                continue
            labels = [1]
            if len(prepared) > 1:
                distance_matrix = np.zeros((len(prepared), len(prepared)), dtype=float)
                for left_index, (_left_row, left_coordinates) in enumerate(prepared):
                    for right_index in range(left_index + 1, len(prepared)):
                        right_coordinates = prepared[right_index][1]
                        rmsd = self._pose_rmsd(left_coordinates, right_coordinates)
                        distance_matrix[left_index, right_index] = rmsd
                        distance_matrix[right_index, left_index] = rmsd
                condensed = squareform(distance_matrix, checks=False)
                labels = list(fcluster(linkage(condensed, method="average"), t=cutoff, criterion="distance"))

            cluster_rows: dict[int, list[dict]] = {}
            for label, (row, _coordinates) in zip(labels, prepared, strict=False):
                cluster_rows.setdefault(int(label), []).append(row)
            for cluster_id, members in sorted(cluster_rows.items()):
                representative = min(members, key=self._docking_score)
                clusters.append(
                    {
                        "ligand": ligand_name,
                        "cluster_id": cluster_id,
                        "size": len(members),
                        "best_score": self._docking_score(representative),
                        "representative": representative,
                        "members": members,
                    }
                )
        return clusters

    def _populate_cluster_table(self) -> None:
        """Render RMSD clusters into the cluster table."""
        headers = [
            I18n.get("ligand_col", self.lang),
            I18n.get("cluster_id", self.lang),
            I18n.get("cluster_size", self.lang),
            I18n.get("best_score", self.lang),
            I18n.get("representative_pose", self.lang),
            I18n.get("members", self.lang),
        ]
        self.cluster_table.clear()
        self.cluster_table.setColumnCount(len(headers))
        self.cluster_table.setHorizontalHeaderLabels(headers)
        apply_header_tooltips(self.cluster_table)
        self.cluster_table.setRowCount(len(self.current_clusters))
        for row_index, cluster in enumerate(self.current_clusters):
            representative = cluster["representative"]
            values = [
                cluster["ligand"],
                cluster["cluster_id"],
                cluster["size"],
                round(float(cluster["best_score"]), 3),
                int(representative.get("pose_rank", representative.get("mode", 0))),
                ", ".join(str(int(member.get("pose_rank", member.get("mode", 0)))) for member in cluster["members"]),
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if isinstance(value, (int, float)):
                    item.setData(Qt.DisplayRole, value)
                item.setData(Qt.UserRole, self._row_id(representative))
                self.cluster_table.setItem(row_index, column_index, item)

    def _update_cluster_histogram(self) -> None:
        """Draw the cluster size histogram."""
        self.cluster_figure.clear()
        axis = self.cluster_figure.add_subplot(111)
        if self.current_clusters:
            labels = [f"{cluster['ligand']} C{cluster['cluster_id']}" for cluster in self.current_clusters]
            sizes = [int(cluster["size"]) for cluster in self.current_clusters]
            axis.bar(range(len(sizes)), sizes, color="#4f7cac")
            axis.set_xticks(range(len(labels)))
            axis.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
            axis.set_ylabel("Tamanho do cluster")
        self.cluster_canvas.draw_idle()

    def _cluster_row_clicked(self, row_index: int, _column_index: int) -> None:
        """Load a cluster representative when a cluster row is clicked."""
        if row_index < 0 or row_index >= len(self.current_clusters):
            return
        representative = self.current_clusters[row_index]["representative"]
        row_id = self._row_id(representative)
        for table_row in range(self.table.rowCount()):
            item = self.table.item(table_row, 0)
            if item is not None and item.data(Qt.UserRole) == row_id:
                self.table.selectRow(table_row)
                break
        self._load_pose_preview(representative)

    def export_cluster_representatives(self) -> None:
        """Export the representative pose of each RMSD cluster."""
        if not self.current_clusters:
            QMessageBox.information(self, "Exportar melhor por cluster", "Não há clusters disponíveis para exportar.")
            return
        export_format, ok = QInputDialog.getItem(
            self,
            "Exportar melhor por cluster",
            "Formato",
            ["pdbqt", "pdb", "mol2"],
            0,
            False,
        )
        if not ok:
            return
        output_folder = QFileDialog.getExistingDirectory(self, "Selecionar pasta de saída")
        if not output_folder:
            return
        if export_format in {"pdb", "mol2"} and find_obabel_executable() is None:
            QMessageBox.critical(self, "Exportar melhor por cluster", "OpenBabel não encontrado. Instale-o para exportar arquivos .pdb ou .mol2.")
            return
        output_dir = Path(output_folder)
        exported = 0
        for cluster in self.current_clusters:
            representative = cluster["representative"]
            basename = f"{safe_export_name(cluster['ligand'])}_cluster{int(cluster['cluster_id'])}_pose{int(representative['mode'])}"
            output_path = output_dir / f"{basename}.{export_format}"
            self._export_pose_to_path(representative, output_path, export_format)
            exported += 1
        QMessageBox.information(self, "Exportar melhor por cluster", f"{exported} pose(s) representativa(s) exportada(s) para {output_dir}.")

    def _export_pose_to_path(self, row: dict, output_path: Path, export_format: str) -> None:
        """Write one pose row to a target path, converting with Open Babel if needed."""
        temporary_pdbqt = output_path if export_format == "pdbqt" else output_path.with_suffix(".pdbqt")
        temporary_pdbqt.write_text(
            extract_pose_model(Path(row["output_file"]), int(row["mode"]), include_model=False),
            encoding="utf-8",
        )
        if export_format == "pdbqt":
            return
        convert_with_obabel(temporary_pdbqt, output_path)
        temporary_pdbqt.unlink(missing_ok=True)

    def _pose_heavy_coordinates(self, row: dict):
        """Extract heavy-atom coordinates from one PDBQT pose model."""
        import numpy as np

        pose_text = extract_pose_model(Path(row["output_file"]), int(row["mode"]), include_model=False)
        coordinates: list[tuple[float, float, float]] = []
        for line in pose_text.splitlines():
            if not line.startswith(("ATOM", "HETATM")):
                continue
            atom_name = line[12:16].strip()
            element = line[76:78].strip() if len(line) >= 78 else ""
            if not element:
                element = "".join(char for char in atom_name if char.isalpha())[:1]
            if element.upper().startswith("H"):
                continue
            coordinates.append((float(line[30:38]), float(line[38:46]), float(line[46:54])))
        return np.asarray(coordinates, dtype=float)

    @staticmethod
    def _pose_rmsd(left_coordinates, right_coordinates) -> float:
        """Compute direct heavy-atom RMSD between two docked poses."""
        import numpy as np

        if left_coordinates.shape != right_coordinates.shape or len(left_coordinates) == 0:
            return 9999.0
        delta = left_coordinates - right_coordinates
        return float(np.sqrt(np.mean(np.sum(delta * delta, axis=1))))

    def _apply_filters(self) -> None:
        """Apply all visible filters and re-render the table."""
        rows = [row for row in self.results if self._row_matches_filters(row)]
        if self._sort_criteria:
            rows = self._sort_rows(rows)
        self.filtered_results = rows
        self._populate_table()
        self._update_chart()
        self._save_state()

    def _row_matches_filters(self, row: dict) -> bool:
        """Return True when a result row passes all active filters."""
        ligand_query = self.ligand_filter.text().strip().lower()
        if ligand_query and ligand_query not in row["ligand_name"].lower():
            return False
        selected_scoring = self._selected_scoring_filters()
        scoring_label = row.get("scoring_function", row.get("scoring_key", ""))
        if selected_scoring and scoring_label not in selected_scoring:
            return False
        docking_score = self._docking_score(row)
        if docking_score < self.affinity_min.value() or docking_score > self.affinity_max.value():
            return False
        rmsd = float(row.get("rmsd_lb", 0.0))
        if rmsd < self.rmsd_min.value() or rmsd > self.rmsd_max.value():
            return False
        if self.pinned_only.isChecked() and not self._row_pinned(row):
            return False
        return True

    def _table_values(self, row: dict, scoring_headers: list[str]) -> list:
        """Return display values for one row in the enhanced results table."""
        scoring_label = row.get("scoring_function", row.get("scoring_key", ""))
        scoring_values = [row.get("affinity", "") if header == scoring_label else "" for header in scoring_headers]
        return [
            row["ligand_name"],
            row.get("pose_rank", row.get("mode", "")),
            self._docking_score(row),
            *scoring_values,
            row.get("rmsd_lb", ""),
            self._row_pinned(row),
            self._row_note(row),
            row.get("scoring_error", ""),
        ]

    def _table_item_changed(self, item: QTableWidgetItem) -> None:
        """Persist pin and note edits made directly in the table."""
        if self._rendering_table or item is None:
            return
        row_id = item.data(Qt.UserRole)
        if not row_id:
            return
        key = self.column_keys[item.column()] if item.column() < len(self.column_keys) else ""
        if key == "pinned":
            self.table_state.setdefault("pins", {})[row_id] = item.checkState() == Qt.Checked
        elif key == "notes":
            self.table_state.setdefault("notes", {})[row_id] = item.text()
        else:
            return
        self._save_state()

    def _open_context_menu(self, position: QPoint) -> None:
        """Open the result-row context menu."""
        item = self.table.itemAt(position)
        if item is None:
            return
        self.table.selectRow(item.row())
        row = self._selected_result_row()
        if row is None:
            return
        menu = QMenu(self)
        pin_action = QAction("Unpin" if self._row_pinned(row) else "Pin", self)
        note_action = QAction("Adicionar nota", self)
        export_action = QAction("Exportar esta pose", self)
        pin_action.triggered.connect(lambda: self._toggle_selected_pin(row))
        note_action.triggered.connect(lambda: self._edit_note(row))
        export_action.triggered.connect(lambda: self._export_single_pose(row))
        menu.addAction(pin_action)
        menu.addAction(note_action)
        menu.addAction(export_action)
        menu.exec(self.table.viewport().mapToGlobal(position))

    def _toggle_selected_pin(self, row: dict) -> None:
        """Toggle pin status for a result row."""
        row_id = self._row_id(row)
        self.table_state.setdefault("pins", {})[row_id] = not self._row_pinned(row)
        self._save_state()
        self._apply_filters()

    def _edit_note(self, row: dict) -> None:
        """Prompt for and persist a note for a result row."""
        row_id = self._row_id(row)
        note, ok = QInputDialog.getText(self, "Nota da pose", "Notas", text=self._row_note(row))
        if ok:
            self.table_state.setdefault("notes", {})[row_id] = note
            self._save_state()
            self._apply_filters()

    def _export_single_pose(self, row: dict) -> None:
        """Export one selected pose from the context menu."""
        default_name = f"{safe_export_name(row['ligand_name'])}_pose{int(row['mode'])}.pdbqt"
        file_name, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Exportar esta pose",
            default_name,
            "PDBQT (*.pdbqt);;PDB (*.pdb);;MOL2 (*.mol2)",
        )
        if not file_name:
            return
        output_path = Path(file_name)
        pose_pdbqt = output_path if output_path.suffix.lower() == ".pdbqt" else output_path.with_suffix(".pdbqt")
        pose_pdbqt.write_text(
            extract_pose_model(Path(row["output_file"]), int(row["mode"]), include_model=False),
            encoding="utf-8",
        )
        if output_path.suffix.lower() != ".pdbqt":
            if find_obabel_executable() is None:
                QMessageBox.critical(self, "Exportar esta pose", "OpenBabel não encontrado. Instale-o para exportar arquivos .pdb ou .mol2.")
                return
            convert_with_obabel(pose_pdbqt, output_path)
            pose_pdbqt.unlink(missing_ok=True)
        QMessageBox.information(self, "Exportar esta pose", f"Exportado para {output_path}.")

    def _header_clicked(self, section: int) -> None:
        """Sort rows by one column, preserving earlier keys with Shift-click."""
        if section >= len(self.column_keys):
            return
        key = self.column_keys[section]
        shift = QApplication.keyboardModifiers() & Qt.ShiftModifier
        existing = next((item for item in self._sort_criteria if item[0] == key), None)
        ascending = not existing[1] if existing else True
        if shift:
            self._sort_criteria = [item for item in self._sort_criteria if item[0] != key]
            self._sort_criteria.append((key, ascending))
        else:
            self._sort_criteria = [(key, ascending)]
        self._apply_filters()

    def _sort_rows(self, rows: list[dict]) -> list[dict]:
        """Sort rows using the active single or multi-column criteria."""
        sorted_rows = list(rows)
        for key, ascending in reversed(self._sort_criteria):
            sorted_rows.sort(key=lambda row: self._sort_value(row, key), reverse=not ascending)
        return sorted_rows

    def _sort_value(self, row: dict, key: str):
        """Return a comparable sort value for a row and column key."""
        if key.startswith("score::"):
            label = key.split("::", 1)[1]
            return float(row.get("affinity", 999999.0)) if row.get("scoring_function") == label else 999999.0
        if key == "docking_score":
            return self._docking_score(row)
        if key == "pose_rank":
            return int(row.get("pose_rank", row.get("mode", 0)))
        if key == "rmsd_lb":
            return float(row.get("rmsd_lb", 999999.0))
        if key == "pinned":
            return int(self._row_pinned(row))
        if key == "notes":
            return self._row_note(row).lower()
        return str(row.get(key, "")).lower()

    def _sync_state_path(self) -> None:
        """Load the JSON sidecar for the current output directory, if any."""
        output_dirs = {Path(row["output_file"]).parent for row in self.results if row.get("output_file")}
        if not output_dirs:
            return
        output_dir = sorted(output_dirs, key=lambda path: str(path))[0]
        if self._state_loaded_for == output_dir:
            return
        self.state_path = output_dir / "vina_results_state.json"
        self._state_loaded_for = output_dir
        if self.state_path.exists():
            try:
                self.table_state = json.loads(self.state_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.table_state = {"pins": {}, "notes": {}, "filters": {}}
        self._restore_filters()

    def _save_state(self) -> None:
        """Persist pins, notes, and filter state beside the docking output."""
        if self.state_path is None:
            return
        self.table_state["filters"] = self._current_filter_state()
        self.state_path.write_text(json.dumps(self.table_state, indent=2, ensure_ascii=False), encoding="utf-8")

    def _restore_filters(self) -> None:
        """Restore saved filter controls from sidecar state."""
        filters = self.table_state.get("filters", {})
        self.ligand_filter.blockSignals(True)
        self.affinity_min.blockSignals(True)
        self.affinity_max.blockSignals(True)
        self.rmsd_min.blockSignals(True)
        self.rmsd_max.blockSignals(True)
        self.pinned_only.blockSignals(True)
        self.ligand_filter.setText(filters.get("ligand", ""))
        self.affinity_min.setValue(float(filters.get("affinity_min", -9999.0)))
        self.affinity_max.setValue(float(filters.get("affinity_max", 9999.0)))
        self.rmsd_min.setValue(float(filters.get("rmsd_min", 0.0)))
        self.rmsd_max.setValue(float(filters.get("rmsd_max", 9999.0)))
        self.pinned_only.setChecked(bool(filters.get("pinned_only", False)))
        self.ligand_filter.blockSignals(False)
        self.affinity_min.blockSignals(False)
        self.affinity_max.blockSignals(False)
        self.rmsd_min.blockSignals(False)
        self.rmsd_max.blockSignals(False)
        self.pinned_only.blockSignals(False)

    def _current_filter_state(self) -> dict:
        """Return current filter values for persistence."""
        return {
            "ligand": self.ligand_filter.text(),
            "scoring": list(self._selected_scoring_filters()),
            "affinity_min": self.affinity_min.value(),
            "affinity_max": self.affinity_max.value(),
            "rmsd_min": self.rmsd_min.value(),
            "rmsd_max": self.rmsd_max.value(),
            "pinned_only": self.pinned_only.isChecked(),
        }

    def _refresh_scoring_filter_options(self) -> None:
        """Rebuild the multi-select scoring filter menu from result rows."""
        selected = set(self.table_state.get("filters", {}).get("scoring", []))
        labels = sorted({row.get("scoring_function", row.get("scoring_key", "")) for row in self.results})
        self.scoring_filter_menu.clear()
        self.scoring_filter_actions = {}
        for label in labels:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(not selected or label in selected)
            action.toggled.connect(lambda _checked: self._scoring_filter_changed())
            self.scoring_filter_menu.addAction(action)
            self.scoring_filter_actions[label] = action
        self._refresh_scoring_filter_button()

    def _scoring_filter_changed(self) -> None:
        """Persist and apply scoring filter changes."""
        self._refresh_scoring_filter_button()
        self._apply_filters()

    def _selected_scoring_filters(self) -> set[str]:
        """Return checked scoring labels; empty means all."""
        if not self.scoring_filter_actions:
            return set()
        checked = {label for label, action in self.scoring_filter_actions.items() if action.isChecked()}
        return set() if len(checked) == len(self.scoring_filter_actions) else checked

    def _refresh_scoring_filter_button(self) -> None:
        """Update the scoring filter button label."""
        selected = self._selected_scoring_filters()
        if not selected:
            self.scoring_filter_button.setText(I18n.get("scoring_all", self.lang))
        elif len(selected) == 1:
            self.scoring_filter_button.setText(f"Scoring: {next(iter(selected))}")
        else:
            self.scoring_filter_button.setText(f"Scoring: {len(selected)} selected")

    def _row_id(self, row: dict) -> str:
        """Return a stable sidecar key for a result row."""
        return "|".join(
            [
                str(row.get("ligand_name", "")),
                str(row.get("scoring_key", row.get("scoring_function", ""))),
                str(row.get("mode", "")),
                str(row.get("output_file", "")),
            ]
        )

    def _row_pinned(self, row: dict) -> bool:
        """Return persisted pin status for a row."""
        return bool(self.table_state.get("pins", {}).get(self._row_id(row), False))

    def _row_note(self, row: dict) -> str:
        """Return persisted notes for a row."""
        return str(self.table_state.get("notes", {}).get(self._row_id(row), ""))

    @staticmethod
    def _docking_score(row: dict) -> float:
        """Return the original docking score for a row."""
        return float(row.get("vina_affinity", row.get("affinity", 0.0)) or 0.0)

    @staticmethod
    def _numeric_column(key: str) -> bool:
        """Return True when a table column should sort as numeric."""
        return key in {"pose_rank", "docking_score", "rmsd_lb"} or key.startswith("score::")

    @staticmethod
    def _range_spin(value: float) -> QDoubleSpinBox:
        """Create a compact numeric filter spin box."""
        spin = QDoubleSpinBox()
        spin.setRange(-9999.0, 9999.0)
        spin.setDecimals(2)
        spin.setSingleStep(0.5)
        spin.setValue(value)
        spin.setMinimumWidth(72)
        spin.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        return spin

    def _scoring_headers(self) -> list[str]:
        """Return dynamic scorer column names."""
        return sorted({row.get("scoring_function", row.get("scoring_key", "")) for row in self.results if row.get("scoring_function") or row.get("scoring_key")})

    @staticmethod
    def _color_for_affinity(affinity: float) -> QColor:
        """Return a row color based on affinity score thresholds."""
        if affinity <= -9:
            return QColor("#2f6f4e")
        if affinity <= -7:
            return QColor("#8a7a2e")
        return QColor("#f5f5f5")

    @staticmethod
    def _excel_fill_for_affinity(affinity: float) -> PatternFill:
        """Return an Excel fill color based on affinity score thresholds."""
        if affinity <= -9:
            return PatternFill("solid", fgColor="5BA36A")
        if affinity <= -7:
            return PatternFill("solid", fgColor="E0C95A")
        return PatternFill("solid", fgColor="FFFFFF")


class PoseViewerDialog(QDialog):
    """Embedded Py3Dmol/3Dmol.js viewer for one receptor-pose complex."""

    def __init__(self, row: dict, parent: QWidget | None = None) -> None:
        """Prepare converted viewer files and render the complex in WebEngine."""
        super().__init__(parent)
        if QWebEngineView is None:
            raise RuntimeError("PySide6-WebEngine não está instalado.")
        self.row = dict(row)
        self.view_dir = Path(tempfile.mkdtemp(prefix="vinalab_py3dmol_"))
        self.receptor_pdb, self.pose_pdb = prepare_pose_view_files(self.row, self.view_dir)
        self.setWindowTitle(f"Visualizador de pose - {row['ligand_name']} pose {int(row['mode'])}")
        self.resize(1200, 850)
        self.web_view = QWebEngineView()
        self.scale_spin = QSpinBox()
        self.export_png_button = QPushButton("Exportar PNG em alta resolução")
        self.close_button = QPushButton("Fechar")
        self._build_ui()
        html_path = self.view_dir / "viewer.html"
        html_path.write_text(self._viewer_html(), encoding="utf-8")
        self.web_view.setUrl(QUrl.fromLocalFile(str(html_path)))

    def _build_ui(self) -> None:
        """Build the viewer dialog controls."""
        layout = QVBoxLayout(self)
        layout.addWidget(self.web_view, stretch=1)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Escala do PNG"))
        self.scale_spin.setRange(1, 5)
        self.scale_spin.setValue(3)
        controls.addWidget(self.scale_spin)
        self.export_png_button.clicked.connect(self.export_png)
        self.close_button.clicked.connect(self.accept)
        controls.addWidget(self.export_png_button)
        controls.addWidget(self.close_button)
        controls.addStretch()
        layout.addLayout(controls)

    def _viewer_html(self) -> str:
        """Return a self-contained viewer page that loads 3Dmol.js in WebEngine."""
        return build_pose_view_html(self.row, self.receptor_pdb, self.pose_pdb)

    def export_png(self) -> None:
        """Export a high-resolution PNG from the current 3Dmol view."""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar PNG em alta resolução",
            f"{safe_export_name(self.row['ligand_name'])}_pose{int(self.row['mode'])}.png",
            "Imagens PNG (*.png)",
        )
        if not file_name:
            return
        output_path = Path(file_name)
        scale = self.scale_spin.value()
        self.web_view.page().runJavaScript(f"exportPng({scale});", lambda data_url: self._save_png_data_url(data_url, output_path))

    def _save_png_data_url(self, data_url: str, output_path: Path) -> None:
        """Decode a browser PNG data URL and write it to disk."""
        prefix = "data:image/png;base64,"
        if not isinstance(data_url, str) or not data_url.startswith(prefix):
            QMessageBox.critical(self, "Exportar PNG", "Não foi possível capturar o visualizador Py3Dmol como PNG.")
            return
        output_path.write_bytes(base64.b64decode(data_url[len(prefix) :]))
        QMessageBox.information(self, "Exportar PNG", f"PNG exportado para {output_path}.")


class ComparisonDialog(QDialog):
    """Compare docked poses, crystal references, and scoring values."""

    def __init__(self, results: list[dict], parent: ResultsTab) -> None:
        """Create comparison controls."""
        super().__init__(parent)
        self.results = list(results)
        self.results_tab = parent
        self.view_dir = Path(tempfile.mkdtemp(prefix="vinalab_compare_"))
        self.setWindowTitle("Comparar poses")
        self.resize(1250, 850)
        self.pose_pair_radio = QRadioButton("Pose A vs Pose B")
        self.crystal_radio = QRadioButton("Pose vs cristal")
        self.scoring_radio = QRadioButton("Comparação de pontuação")
        self.mode_group = QButtonGroup(self)
        self.pose_a_combo = QComboBox()
        self.pose_b_combo = QComboBox()
        self.reference_edit = QLineEdit()
        self.top_n_spin = QSpinBox()
        self.run_button = QPushButton("Executar comparação")
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
        selector_row.addWidget(QLabel("Referência"))
        self.reference_edit.setReadOnly(True)
        selector_row.addWidget(self.reference_edit)
        browse_button = QPushButton("Procurar")
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
            layout.addWidget(QLabel("PySide6-WebEngine está indisponível."), stretch=3)
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
        file_name, _ = QFileDialog.getOpenFileName(self, "Pose de referência", "", "Arquivos PDBQT (*.pdbqt);;Todos os arquivos (*)")
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
        """Compare two docked poses by direct heavy-atom RMSD."""
        row_a = self._selected_row(self.pose_a_combo)
        row_b = self._selected_row(self.pose_b_combo)
        if row_a is None or row_b is None:
            return
        rmsd = self.results_tab._pose_rmsd(self.results_tab._pose_heavy_coordinates(row_a), self.results_tab._pose_heavy_coordinates(row_b))
        self.status_label.setText(f"RMSD: {rmsd:.3f} Å")
        self._populate_table(["Pose A", "Pose B", "RMSD Å"], [[self._row_label(row_a), self._row_label(row_b), f"{rmsd:.3f}"]])
        self._render_pose_pair(row_a, row_b, f"Pose A vs Pose B | RMSD {rmsd:.3f} Å")
        self.figure.clear()
        self.canvas.draw_idle()

    def _compare_to_crystal(self) -> None:
        """Rank top-N poses by RMSD to a reference crystal pose."""
        reference_path = Path(self.reference_edit.text().strip())
        if not reference_path.exists():
            QMessageBox.warning(self, "Pose vs cristal", "Escolha um arquivo .pdbqt de referência.")
            return
        reference_coordinates = pdbqt_file_heavy_coordinates(reference_path)
        rows = sorted(self.results, key=self.results_tab._docking_score)[: self.top_n_spin.value()]
        table_rows = []
        best_row = None
        best_rmsd = 9999.0
        for row in rows:
            rmsd = self.results_tab._pose_rmsd(self.results_tab._pose_heavy_coordinates(row), reference_coordinates)
            if rmsd < best_rmsd:
                best_rmsd = rmsd
                best_row = row
            table_rows.append([
                int(row.get("pose_rank", row.get("mode", 0))),
                f"{self.results_tab._docking_score(row):.3f}",
                f"{rmsd:.3f}",
            ])
        self.status_label.setText(f"Melhor RMSD para cristal: {best_rmsd:.3f} Å")
        self._populate_table(["Pose rank", "Score", "RMSD to crystal Å"], table_rows)
        if best_row is not None:
            self._render_pose_vs_reference(best_row, reference_path, f"Pose vs cristal | melhor RMSD {best_rmsd:.3f} Å")
        self.figure.clear()
        self.canvas.draw_idle()

    def _compare_scoring_values(self) -> None:
        """Plot scoring values for the selected pose identity."""
        selected = self._selected_row(self.pose_a_combo)
        if selected is None:
            return
        pose_key = self.results_tab._pose_identity(selected)
        rows = [row for row in self.results if self.results_tab._pose_identity(row) == pose_key]
        labels = [row.get("scoring_function", row.get("scoring_key", "")) for row in rows]
        values = [float(row.get("affinity", 0.0)) for row in rows]
        self.status_label.setText("Comparação de pontuação para a pose selecionada.")
        self._populate_table(["Função de pontuação", "Score"], [[label, f"{value:.3f}"] for label, value in zip(labels, values, strict=False)])
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
        html_path.write_text(build_comparison_html(title, receptor_pdb, pose_a_pdb, pose_b_pdb), encoding="utf-8")
        self.web_view.setUrl(QUrl.fromLocalFile(str(html_path)))

    def _render_pose_vs_reference(self, row: dict, reference_path: Path, title: str) -> None:
        """Render one docked pose against a crystal reference pose."""
        if self.web_view is None:
            return
        receptor_pdb, pose_pdb = prepare_pose_view_files(row, self.view_dir)
        reference_pdb = self.view_dir / "reference.pdb"
        reference_pdb.write_text(
            pdbqt_text_to_view_pdb(reference_path.read_text(encoding="utf-8", errors="replace"), include_conect=True),
            encoding="utf-8",
        )
        html_path = self.view_dir / "comparison.html"
        html_path.write_text(build_comparison_html(title, receptor_pdb, pose_pdb, reference_pdb), encoding="utf-8")
        self.web_view.setUrl(QUrl.fromLocalFile(str(html_path)))

    def _populate_table(self, headers: list[str], rows: list[list[str]]) -> None:
        """Populate the comparison result table."""
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))
        for row_index, row_values in enumerate(rows):
            for column_index, value in enumerate(row_values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(str(value)))

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

    def __init__(self, rows: list[dict], reference_path: Path, top_n: int, parent: QWidget | None = None) -> None:
        """Build validation report dialog."""
        super().__init__(parent)
        self.rows = sorted(rows, key=lambda row: float(row.get("affinity", 0.0)))
        self.reference_path = reference_path
        self.top_n = top_n
        self.validation_rows = self._compute_rows()
        self.setWindowTitle("Validar protocolo")
        self.resize(900, 620)
        self.summary_label = QLabel()
        self.table = QTableWidget(0, 4)
        self.export_button = QPushButton("Exportar relatório de validação")
        self._build_ui()

    def _build_ui(self) -> None:
        """Build validation report UI."""
        layout = QVBoxLayout(self)
        self.summary_label.setWordWrap(True)
        self.summary_label.setText(self._summary_text())
        layout.addWidget(self.summary_label)
        self.table.setHorizontalHeaderLabels(["rank_da_pose", "score", "RMSD_para_cristal", "dentro_de_2A"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setRowCount(len(self.validation_rows))
        for row_index, row in enumerate(self.validation_rows):
            values = [row["pose_rank"], f"{row['score']:.3f}", f"{row['rmsd_to_crystal']:.3f}", row["within_2A"]]
            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
        layout.addWidget(self.table, stretch=1)
        self.export_button.clicked.connect(self._export_csv)
        layout.addWidget(self.export_button)

    def _compute_rows(self) -> list[dict]:
        """Compute RMSD rows for validation output poses."""
        reference_coordinates = pdbqt_file_heavy_coordinates(self.reference_path)
        output_rows: list[dict] = []
        for row in self.rows:
            pose_text = extract_pose_model(Path(row["output_file"]), int(row["mode"]), include_model=False)
            rmsd = coordinate_rmsd(pdbqt_text_heavy_coordinates(pose_text), reference_coordinates)
            output_rows.append(
                {
                    "pose_rank": int(row.get("pose_rank", row.get("mode", 0))),
                    "score": float(row.get("affinity", 0.0)),
                    "rmsd_to_crystal": rmsd,
                    "within_2A": "sim" if rmsd <= 2.0 else "não",
                }
            )
        return output_rows

    def _summary_text(self) -> str:
        """Return top-1/top-3/top-N success summary."""
        if not self.validation_rows:
            return "Nenhuma pose de validação disponível."
        top1_rmsd = self.validation_rows[0]["rmsd_to_crystal"]
        top3_success = any(row["rmsd_to_crystal"] <= 2.0 for row in self.validation_rows[:3])
        topn_success = any(row["rmsd_to_crystal"] <= 2.0 for row in self.validation_rows[: self.top_n])
        return (
            f"Top-1 RMSD: {top1_rmsd:.3f} Å | "
            f"Top-3 success within 2 Å: {'yes' if top3_success else 'no'} | "
            f"Top-{self.top_n} success within 2 Å: {'yes' if topn_success else 'no'}"
        )

    def _export_csv(self) -> None:
        """Export validation report to CSV."""
        file_name, _ = QFileDialog.getSaveFileName(self, "Exportar relatório de validação", "", "Arquivos CSV (*.csv)")
        if not file_name:
            return
        pd.DataFrame(self.validation_rows).to_csv(Path(file_name), index=False)


def prepare_pose_view_files(row: dict, view_dir: Path) -> tuple[Path, Path]:
    """Extract one PDBQT pose and write PDB files for 3Dmol without bond-guessing converters."""
    output_file = Path(row.get("output_file", ""))
    receptor_file = Path(row.get("receptor_file", ""))
    if not output_file.is_absolute():
        output_file = output_file.resolve()
    if not receptor_file.is_absolute():
        receptor_file = receptor_file.resolve()
    if not output_file.exists():
        raise FileNotFoundError(f"Arquivo de saída da pose não encontrado: {output_file}")
    if not receptor_file.exists():
        raise FileNotFoundError(f"Arquivo do receptor não encontrado: {receptor_file}")
    view_dir.mkdir(parents=True, exist_ok=True)
    pose_file = view_dir / f"{safe_export_name(row['ligand_name'])}_pose{int(row['mode'])}.pdbqt"
    pose_text = extract_pose_model(output_file, int(row["mode"]), include_model=False)
    if not any(line.startswith(("ATOM", "HETATM")) for line in clean_pdbqt_text(pose_text).splitlines()):
        raise ValueError("A pose selecionada não contém átomos PDBQT para visualização.")
    pose_file.write_text(pose_text, encoding="utf-8")
    receptor_pdb = view_dir / "receptor.pdb"
    pose_pdb = view_dir / f"{safe_export_name(row['ligand_name'])}_pose{int(row['mode'])}.pdb"
    receptor_pdb.write_text(pdbqt_text_to_view_pdb(receptor_file.read_text(encoding="utf-8", errors="replace"), include_conect=False), encoding="utf-8")
    pose_pdb.write_text(pdbqt_text_to_view_pdb(pose_text, include_conect=True), encoding="utf-8")
    if not _pdb_file_has_atoms(receptor_pdb) or not _pdb_file_has_atoms(pose_pdb):
        raise ValueError("Erro ao carregar visualização 3D. Verifique os arquivos de entrada.")
    return receptor_pdb, pose_pdb


def _pdb_file_has_atoms(path: Path) -> bool:
    """Return True when a display PDB file contains atoms."""
    return any(line.startswith(("ATOM", "HETATM")) for line in path.read_text(encoding="utf-8", errors="replace").splitlines())


def pdbqt_text_to_view_pdb(text: str, include_conect: bool) -> str:
    """Convert PDBQT text to viewer-safe PDB, preserving coordinates and adding simple ligand CONECT records."""
    atoms: list[dict] = []
    forced_bonds: set[tuple[int, int]] = set()
    seen_model = False
    for line in clean_pdbqt_text(text).splitlines():
        if line.startswith("MODEL"):
            if seen_model:
                break
            seen_model = True
            continue
        if line.startswith("ENDMDL") and seen_model:
            break
        if line.startswith("BRANCH"):
            bond = _pdbqt_branch_bond(line)
            if bond is not None:
                forced_bonds.add(bond)
            continue
        if not line.startswith(("ATOM", "HETATM")):
            continue
        atom = _pdbqt_atom_record(line)
        if atom:
            atoms.append(atom)
    output_lines = [_format_view_pdb_atom(atom) for atom in atoms]
    if include_conect:
        output_lines.extend(_infer_conect_records(atoms, forced_bonds))
    output_lines.append("END")
    return "\n".join(output_lines) + "\n"


def _pdbqt_branch_bond(line: str) -> tuple[int, int] | None:
    """Parse the covalent edge encoded by a PDBQT BRANCH record."""
    parts = line.split()
    if len(parts) < 3:
        return None
    try:
        return tuple(sorted((int(parts[1]), int(parts[2]))))
    except ValueError:
        return None


def _pdbqt_atom_record(line: str) -> dict | None:
    """Parse one ATOM/HETATM PDBQT line into a normalized PDB atom record."""
    try:
        serial = int(line[6:11])
        name = line[12:16].strip() or "X"
        resname = line[17:20].strip() or "LIG"
        chain = (line[21].strip() if len(line) > 21 else "") or "A"
        resid = int((line[22:26].strip() or "1").split()[0])
        x = float(line[30:38])
        y = float(line[38:46])
        z = float(line[46:54])
    except ValueError:
        parts = line.split()
        if len(parts) < 8:
            return None
        try:
            serial = int(parts[1])
            name = parts[2]
            resname = parts[3] if len(parts) > 3 else "LIG"
            chain = parts[4] if len(parts) > 4 and not _is_number(parts[4]) else "A"
            resid = int(parts[5] if chain != "A" else parts[4])
            coordinate_offset = 6 if chain != "A" else 5
            x = float(parts[coordinate_offset])
            y = float(parts[coordinate_offset + 1])
            z = float(parts[coordinate_offset + 2])
        except (ValueError, IndexError):
            return None
    atom_type = line.rsplit(maxsplit=1)[-1] if line.split() else ""
    element = _element_from_atom(name, atom_type)
    return {
        "serial": serial,
        "name": name[:4],
        "resname": resname[:3],
        "chain": chain[:1],
        "resid": resid,
        "x": x,
        "y": y,
        "z": z,
        "element": element,
        "record": "HETATM" if line.startswith("HETATM") else "ATOM",
    }


def _format_view_pdb_atom(atom: dict) -> str:
    """Format one atom as a standards-compatible PDB line."""
    return (
        f"{atom['record']:<6}{int(atom['serial']):5d} {atom['name']:<4} {atom['resname']:>3} "
        f"{atom['chain']}{int(atom['resid']):4d}    "
        f"{float(atom['x']):8.3f}{float(atom['y']):8.3f}{float(atom['z']):8.3f}"
        f"  1.00  0.00          {atom['element']:>2}"
    )


def _infer_conect_records(atoms: list[dict], forced_bonds: set[tuple[int, int]] | None = None) -> list[str]:
    """Infer conservative ligand connectivity from distance and covalent radii."""
    records: dict[int, list[int]] = {int(atom["serial"]): [] for atom in atoms}
    forced_bonds = forced_bonds or set()
    for left_serial, right_serial in forced_bonds:
        if left_serial in records and right_serial in records:
            records[left_serial].append(right_serial)
            records[right_serial].append(left_serial)
    for left_index, left_atom in enumerate(atoms):
        for right_atom in atoms[left_index + 1 :]:
            if _atoms_likely_bonded(left_atom, right_atom):
                left_serial = int(left_atom["serial"])
                right_serial = int(right_atom["serial"])
                if right_serial not in records[left_serial]:
                    records[left_serial].append(right_serial)
                if left_serial not in records[right_serial]:
                    records[right_serial].append(left_serial)
    lines: list[str] = []
    for serial, bonded in records.items():
        if bonded:
            lines.append("CONECT" + f"{serial:5d}" + "".join(f"{target:5d}" for target in sorted(bonded)[:4]))
    return lines


def _atoms_likely_bonded(left_atom: dict, right_atom: dict) -> bool:
    """Return True when two atoms are close enough for a covalent bond."""
    if left_atom["element"] == "H" and right_atom["element"] == "H":
        return False
    dx = float(left_atom["x"]) - float(right_atom["x"])
    dy = float(left_atom["y"]) - float(right_atom["y"])
    dz = float(left_atom["z"]) - float(right_atom["z"])
    distance = (dx * dx + dy * dy + dz * dz) ** 0.5
    if distance < 0.35:
        return False
    threshold = _covalent_radius(left_atom["element"]) + _covalent_radius(right_atom["element"]) + 0.45
    return distance <= min(threshold, 2.25)


def _covalent_radius(element: str) -> float:
    """Return approximate covalent radius in Angstrom."""
    return {
        "H": 0.31,
        "C": 0.76,
        "N": 0.71,
        "O": 0.66,
        "S": 1.05,
        "P": 1.07,
        "F": 0.57,
        "CL": 1.02,
        "BR": 1.20,
        "I": 1.39,
        "MG": 1.30,
        "ZN": 1.22,
        "FE": 1.24,
        "CA": 1.74,
    }.get(element.upper(), 0.77)


def _element_from_atom(atom_name: str, atom_type: str) -> str:
    """Infer a PDB element from AutoDock atom type or atom name."""
    token = "".join(char for char in atom_type.strip() if char.isalpha()).upper()
    if token == "A":
        return "C"
    if token.startswith("CL"):
        return "Cl"
    if token.startswith("BR"):
        return "Br"
    if token[:2] in {"OA", "OS"}:
        return "O"
    if token[:2] in {"NA", "NS"}:
        return "N"
    if token[:2] == "SA":
        return "S"
    if token[:2] in {"HD", "HS"}:
        return "H"
    if token[:2] in {"MG", "ZN", "FE", "CA", "MN", "CU"}:
        return token[:2].title()
    if token:
        return token[0].upper()
    letters = "".join(char for char in atom_name if char.isalpha()).upper()
    return letters[:1] if letters else "C"


def _is_number(value: str) -> bool:
    """Return True when value can be parsed as a number."""
    try:
        float(value)
    except ValueError:
        return False
    return True


def build_pose_view_html(
    row: dict,
    receptor_pdb: Path,
    pose_pdb: Path,
    highlights: list[dict] | None = None,
    box: dict | None = None,
) -> str:
    """Return a 3Dmol.js HTML document for a receptor-pose complex."""
    receptor_text = receptor_pdb.read_text(encoding="utf-8", errors="replace")
    pose_text = pose_pdb.read_text(encoding="utf-8", errors="replace")
    ligand_name = html.escape(f"{row['ligand_name']} | {row.get('scoring_function', '')} | pose {int(row['mode'])}")
    highlight_js = _interaction_highlight_js(highlights or [])
    box_js = _box_preview_js(box)
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://cdn.jsdelivr.net/npm/3dmol@2.1.0/build/3Dmol-min.js"></script>
  <style>
    html, body {{ margin: 0; width: 100%; height: 100%; overflow: hidden; background: #0b0d12; color: #edf2ff; }}
    #viewer {{ width: 100vw; height: 100vh; position: relative; }}
    #error {{
      display: none; position: absolute; inset: 0; z-index: 20; align-items: center; justify-content: center;
      padding: 24px; text-align: center; background: #0b0d12; color: #f2dede; font: 14px Segoe UI, sans-serif;
    }}
    #label {{
      position: absolute; top: 12px; left: 12px; z-index: 10; padding: 8px 10px;
      background: rgba(10, 14, 22, 0.78); border: 1px solid rgba(255,255,255,0.14);
      border-radius: 8px; font: 13px Segoe UI, sans-serif;
    }}
    #hint {{
      position: absolute; bottom: 12px; left: 12px; z-index: 10; padding: 7px 9px;
      background: rgba(10, 14, 22, 0.72); border-radius: 8px; font: 12px Segoe UI, sans-serif;
      color: #b9c4d8;
    }}
  </style>
</head>
<body>
  <div id="viewer"></div>
  <div id="error">Erro ao carregar visualização 3D. Verifique os arquivos de entrada.</div>
  <div id="label">{ligand_name}</div>
  <div id="hint">Ligante: bastões ciano | resíduos próximos do receptor: bastões verdes | receptor: cartoon + superfície transparente</div>
  <script>
    const receptorPdb = {json.dumps(receptor_text)};
    const ligandPdb = {json.dumps(pose_text)};
    let viewer = null;
    let ligandModel = null;
    function showViewerError(error) {{
      console.log("Erro na visualização 3D:", error);
      document.getElementById("error").style.display = "flex";
    }}
    function renderComplex() {{
      if (typeof $3Dmol === "undefined") {{
        showViewerError("3Dmol.js indisponível");
        return;
      }}
      try {{
      viewer = $3Dmol.createViewer("viewer", {{backgroundColor: "#0b0d12"}});
      const receptorModel = viewer.addModel(receptorPdb, "pdb");
      ligandModel = viewer.addModel(ligandPdb, "pdb");
      receptorModel.setStyle({{}}, {{cartoon: {{color: "spectrum", opacity: 0.85}}}});
      ligandModel.setStyle({{}}, {{
        stick: {{colorscheme: "cyanCarbon", radius: 0.23}},
        sphere: {{scale: 0.23, colorscheme: "cyanCarbon"}}
      }});
      try {{
        viewer.addStyle({{model: receptorModel, within: {{distance: 4.0, sel: {{model: ligandModel}}}}}}, {{
          stick: {{colorscheme: "greenCarbon", radius: 0.14}}
        }});
        viewer.addSurface($3Dmol.SurfaceType.VDW, {{opacity: 0.16, color: "white"}}, {{
          model: receptorModel, within: {{distance: 6.0, sel: {{model: ligandModel}}}}
        }});
      }} catch (error) {{
        console.log("Interaction overlay skipped:", error);
      }}
      {highlight_js}
      {box_js}
      viewer.zoomTo({{model: ligandModel}});
      viewer.render();
      }} catch (error) {{
        showViewerError(error);
      }}
    }}
    function exportPng(scale) {{
      scale = Math.max(1, Math.min(5, Number(scale || 3)));
      const container = document.getElementById("viewer");
      const oldWidth = container.style.width;
      const oldHeight = container.style.height;
      const width = Math.max(1200, Math.floor(window.innerWidth * scale));
      const height = Math.max(900, Math.floor(window.innerHeight * scale));
      container.style.width = width + "px";
      container.style.height = height + "px";
      viewer.resize();
      viewer.zoomTo();
      viewer.render();
      const png = viewer.pngURI();
      container.style.width = oldWidth || "100vw";
      container.style.height = oldHeight || "100vh";
      viewer.resize();
      viewer.zoomTo({{model: ligandModel}});
      viewer.render();
      return png;
    }}
    window.addEventListener("resize", () => {{ if (viewer) {{ viewer.resize(); viewer.render(); }} }});
    renderComplex();
  </script>
</body>
</html>"""


def build_comparison_html(title: str, receptor_pdb: Path, pose_a_pdb: Path, pose_b_pdb: Path) -> str:
    """Return a 3Dmol.js page comparing two ligand poses against one receptor."""
    receptor_text = receptor_pdb.read_text(encoding="utf-8", errors="replace")
    pose_a_text = pose_a_pdb.read_text(encoding="utf-8", errors="replace")
    pose_b_text = pose_b_pdb.read_text(encoding="utf-8", errors="replace")
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://cdn.jsdelivr.net/npm/3dmol@2.1.0/build/3Dmol-min.js"></script>
  <style>
    html, body {{ margin: 0; width: 100%; height: 100%; overflow: hidden; background: #0b0d12; color: #edf2ff; }}
    #viewer {{ width: 100vw; height: 100vh; }}
    #label {{ position:absolute; top:12px; left:12px; z-index:10; padding:8px 10px; background:rgba(10,14,22,.78); border-radius:8px; font:13px Segoe UI,sans-serif; }}
  </style>
</head>
<body>
  <div id="viewer"></div>
  <div id="label">{html.escape(title)} | verde = A / dockada, magenta = B / referência</div>
  <script>
    const receptorPdb = {json.dumps(receptor_text)};
    const poseA = {json.dumps(pose_a_text)};
    const poseB = {json.dumps(pose_b_text)};
    const viewer = $3Dmol.createViewer("viewer", {{backgroundColor: "#0b0d12"}});
    const receptor = viewer.addModel(receptorPdb, "pdb");
    const modelA = viewer.addModel(poseA, "pdb");
    const modelB = viewer.addModel(poseB, "pdb");
    receptor.setStyle({{}}, {{cartoon: {{color: "spectrum", opacity: 0.75}}}});
    modelA.setStyle({{}}, {{stick: {{color: "limegreen", radius: 0.24}}, sphere: {{scale: 0.22, color: "limegreen"}}}});
    modelB.setStyle({{}}, {{stick: {{color: "magenta", radius: 0.24}}, sphere: {{scale: 0.22, color: "magenta"}}}});
    viewer.zoomTo({{model: modelA}});
    viewer.render();
    window.addEventListener("resize", () => {{ viewer.resize(); viewer.render(); }});
  </script>
</body>
</html>"""


def build_box_preview_html(box: dict, receptor_path: "Path | None" = None) -> str:
    """Return a standalone 3Dmol.js page with the search-box wireframe and optional receptor."""
    box_js = _box_preview_js(box)
    receptor_js = ""
    label_suffix = ""
    if receptor_path is not None:
        try:
            receptor_text = receptor_path.read_text(encoding="utf-8", errors="replace")
            receptor_pdb_text = pdbqt_text_to_view_pdb(receptor_text, include_conect=False)
            receptor_js = f"""
    const receptorPdb = {json.dumps(receptor_pdb_text)};
    const receptorModel = viewer.addModel(receptorPdb, "pdb");
    receptorModel.setStyle({{}}, {{cartoon: {{color: "spectrum", opacity: 0.75}}}});"""
            label_suffix = " | receptor carregado"
        except Exception:  # noqa: BLE001
            pass
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://cdn.jsdelivr.net/npm/3dmol@2.1.0/build/3Dmol-min.js"></script>
  <style>
    html, body {{ margin: 0; width: 100%; height: 100%; overflow: hidden; background: #0b0d12; color: #edf2ff; }}
    #viewer {{ width: 100vw; height: 100vh; }}
    #label {{ position:absolute; top:12px; left:12px; z-index:10; padding:8px 10px; background:rgba(10,14,22,.78); border-radius:8px; font:13px Segoe UI,sans-serif; }}
  </style>
</head>
<body>
  <div id="viewer"></div>
  <div id="label">Prévia da caixa de busca{html.escape(label_suffix)}</div>
  <script>
    const viewer = $3Dmol.createViewer("viewer", {{backgroundColor: "#0b0d12"}});{receptor_js}
    {box_js}
    viewer.zoomTo();
    viewer.render();
    window.addEventListener("resize", () => {{ viewer.resize(); viewer.render(); }});
  </script>
</body>
</html>"""


def pdbqt_file_heavy_coordinates(path: Path):
    """Read heavy-atom coordinates from a PDBQT file containing one pose."""
    return pdbqt_text_heavy_coordinates(path.read_text(encoding="utf-8", errors="replace"))


def pdbqt_text_heavy_coordinates(text: str):
    """Parse heavy-atom coordinates from PDBQT text."""
    import numpy as np

    coordinates: list[tuple[float, float, float]] = []
    for line in text.splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            continue
        atom_name = line[12:16].strip()
        element = line[76:78].strip() if len(line) >= 78 else ""
        if not element:
            element = "".join(char for char in atom_name if char.isalpha())[:1]
        if element.upper().startswith("H"):
            continue
        coordinates.append((float(line[30:38]), float(line[38:46]), float(line[46:54])))
    return np.asarray(coordinates, dtype=float)


def coordinate_rmsd(left_coordinates, right_coordinates) -> float:
    """Compute direct RMSD between two same-order heavy-atom coordinate arrays."""
    import numpy as np

    if left_coordinates.shape != right_coordinates.shape or len(left_coordinates) == 0:
        return 9999.0
    delta = left_coordinates - right_coordinates
    return float(np.sqrt(np.mean(np.sum(delta * delta, axis=1))))


def _interaction_highlight_js(highlights: list[dict]) -> str:
    """Return JavaScript statements that color highlighted receptor residues."""
    statements: list[str] = []
    color_by_type = {"H-bond": "dodgerblue", "Hydrophobic": "orange", "Contact": "lightgray"}
    for item in highlights:
        resi = str(item.get("residue_number", "")).strip()
        if not resi:
            continue
        color = color_by_type.get(str(item.get("interaction_type", "")), "lightgray")
        statements.append(
            "viewer.addStyle({model: receptorModel, resi: "
            f"{json.dumps(resi)}"
            f"}}, {{stick: {{color: {json.dumps(color)}, radius: 0.20}}}});"
        )
    return "\n      ".join(statements)


def _box_preview_js(box: dict | None) -> str:
    """Return 3Dmol.js statements for a search-box wireframe."""
    if not box:
        return ""
    center = {
        "x": float(box.get("center_x", 0.0)),
        "y": float(box.get("center_y", 0.0)),
        "z": float(box.get("center_z", 0.0)),
    }
    dimensions = {
        "w": float(box.get("size_x", 20.0)),
        "h": float(box.get("size_y", 20.0)),
        "d": float(box.get("size_z", 20.0)),
    }
    return (
        "viewer.addBox({"
        f"center: {json.dumps(center)}, "
        f"dimensions: {json.dumps(dimensions)}, "
        'color: "#C8922A", opacity: 0.95, wireframe: true'
        "});\n"
        f"viewer.addSphere({{center: {json.dumps(center)}, radius: 0.35, color: '#C8922A'}});"
    )


class ExportComplexDialog(QDialog):
    """Dialog for exporting selected or multiple docked poses."""

    def __init__(self, results: list[dict], parent: QWidget | None = None) -> None:
        """Initialize export controls."""
        super().__init__(parent)
        self.results = list(results)
        self.setWindowTitle("Exportar complexo")
        self.selected_radio = QRadioButton("Exportar apenas o complexo selecionado")
        self.all_radio = QRadioButton("Exportar todos os complexos")
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
        self.export_button = QPushButton("Exportar")
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the dialog layout."""
        layout = QVBoxLayout(self)
        layout.addWidget(self.selected_radio)
        layout.addWidget(self.all_radio)

        top_n_row = QHBoxLayout()
        top_n_row.addWidget(QLabel("Top N poses por ligante"))
        top_n_row.addWidget(self.top_n_spin)
        layout.addLayout(top_n_row)

        format_row = QHBoxLayout()
        format_row.addWidget(QLabel("Formato"))
        format_row.addWidget(self.format_combo)
        layout.addLayout(format_row)

        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder_edit)
        browse_button = QPushButton("Procurar")
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
        folder = QFileDialog.getExistingDirectory(self, "Selecionar pasta de saída")
        if folder:
            self.folder_edit.setText(folder)

    def _export(self) -> None:
        """Run the export workflow."""
        output_folder = self.folder_edit.text().strip()
        if not output_folder:
            QMessageBox.warning(self, "Exportar complexo", "Escolha uma pasta de saída.")
            return
        output_dir = Path(output_folder)
        output_dir.mkdir(parents=True, exist_ok=True)
        export_format = self.format_combo.currentText()
        rows = self._rows_to_export()
        if not rows:
            QMessageBox.warning(self, "Exportar complexo", "Nenhuma pose está selecionada no momento.")
            return
        if export_format in {"pdb", "mol2"} and find_obabel_executable() is None:
            QMessageBox.critical(
                self,
                "Exportar complexo",
                "OpenBabel não encontrado. Instale-o para exportar arquivos .pdb ou .mol2.",
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
            "Exportar complexo",
            f"{exported} arquivo(s) exportado(s) para {output_dir}.",
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
            key=lambda row: (row["ligand_name"], row.get("scoring_function", row.get("scoring_key", ""))),
        )
        for _, group_rows in grouped:
            rows.extend(list(group_rows)[:top_n])
        return rows

    def _export_row(self, row: dict, output_dir: Path, export_format: str) -> None:
        """Export a single pose row."""
        pose_basename = f"{safe_export_name(row['ligand_name'])}_pose{int(row['mode'])}"
        pose_pdbqt = output_dir / f"{pose_basename}.pdbqt"
        pose_pdbqt.write_text(
            extract_pose_model(Path(row["output_file"]), int(row["mode"]), include_model=False),
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
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "Falha na conversão com OpenBabel.")
        pose_pdbqt.unlink(missing_ok=True)


def safe_export_name(name: str) -> str:
    """Return a filesystem-safe ligand name for exports."""
    cleaned = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in Path(name).stem)
    return cleaned or "ligand"
