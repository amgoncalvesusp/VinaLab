"""UI for scorer recommendation, compatibility, and availability."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from vinalab_core.scoring.registry import ScoringPlan


class ScoringPanel(QWidget):
    """Displays a plan without silently enabling unavailable or incompatible scorers."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.recommendation = QLabel("Inspect a ligand to choose a scoring plan.", self)
        self.recommendation.setObjectName("scoringRecommendation")
        self.recommendation.setWordWrap(True)
        self.table = QTableWidget(0, 4, self)
        self.table.setObjectName("scoringTable")
        self.table.setHorizontalHeaderLabels(["Scorer", "Compatible", "Available", "Details"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.recommendation)
        layout.addWidget(self.table)

    def show_plan(self, plan: ScoringPlan) -> None:
        recommended = plan.option(plan.recommended_key)
        availability = "available" if recommended.available else f"not configured: {recommended.reason}"
        self.recommendation.setText(
            f"Recommended scorer: {recommended.label} ({availability})."
        )
        self.table.setRowCount(len(plan.options))
        for row_index, option in enumerate(plan.options):
            values = (
                option.label,
                "Yes" if option.compatible else "No",
                "Yes" if option.available else "No",
                option.reason,
            )
            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))
