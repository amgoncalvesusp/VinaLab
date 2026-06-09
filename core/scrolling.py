# -*- coding: utf-8 -*-
"""Shared scroll-area configuration for VinaLab."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QWidget,
)


class ScrollManager:
    """Create and tune scrollable areas consistently across the application."""

    VERTICAL_STEP = 36
    HORIZONTAL_STEP = 36
    PAGE_STEP = 360

    @classmethod
    def wrap(
        cls, content: QWidget, object_name: str = "tab_scroll_area"
    ) -> QScrollArea:
        """Wrap a content widget in a responsive vertical scroll area."""
        scroll_area = QScrollArea()
        scroll_area.setObjectName(object_name)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # With widgetResizable the content is squeezed to the viewport width and a
        # horizontal scrollbar never appears. Pin the content to its natural width
        # so a horizontal bar shows when the pane is too narrow to reveal every
        # option, while the vertical bar handles depth.
        natural_width = content.sizeHint().width()
        if natural_width > 0:
            content.setMinimumWidth(natural_width)
        cls.optimize(scroll_area)
        return scroll_area

    @classmethod
    def optimize(cls, scrollable: QAbstractScrollArea) -> None:
        """Apply consistent wheel and scrollbar behavior to a scrollable widget."""
        scrollable.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        vertical = scrollable.verticalScrollBar()
        horizontal = scrollable.horizontalScrollBar()
        vertical.setSingleStep(cls.VERTICAL_STEP)
        vertical.setPageStep(cls.PAGE_STEP)
        horizontal.setSingleStep(cls.HORIZONTAL_STEP)
