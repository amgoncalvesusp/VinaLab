# -*- coding: utf-8 -*-
"""Shared scroll-area configuration for VinaLab."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QApplication,
    QComboBox,
    QFrame,
    QAbstractSpinBox,
    QScrollArea,
    QSizePolicy,
    QWidget,
)


class WheelGuard(QObject):
    """Stop the mouse wheel from silently changing parameters while scrolling.

    Scrolling a panel that contains numeric fields used to mutate any
    QSpinBox / QDoubleSpinBox / QComboBox the cursor happened to pass over.
    Installed application-wide, this filter swallows wheel events on those
    widgets when they are not focused and forwards the scroll to the enclosing
    scroll area, so the panel moves instead of the parameter. A focused widget
    still accepts the wheel, so deliberate adjustment keeps working.
    """

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Block the wheel on spin/combo widgets and scroll the panel instead.

        Spin boxes ship with Qt.WheelFocus, so a wheel tick both focuses the
        widget and changes its value. Checking focus is therefore not enough;
        we consume every wheel event delivered to a spin box / combo and
        forward it to the enclosing scroll area, so the panel moves and the
        parameter never changes by accident. Values are still editable by
        clicking and typing or using the up/down buttons.
        """
        if event.type() == QEvent.Type.Wheel and isinstance(
            obj, (QAbstractSpinBox, QComboBox)
        ):
            area = self._scroll_area_for(obj)
            if area is not None:
                QApplication.sendEvent(area.viewport(), event)
            return True
        return False

    @staticmethod
    def _scroll_area_for(widget: QWidget) -> QScrollArea | None:
        """Walk up the parent chain to the nearest enclosing scroll area."""
        parent = widget.parentWidget()
        while parent is not None:
            if isinstance(parent, QScrollArea):
                return parent
            parent = parent.parentWidget()
        return None


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
        # Always show both bars so there is a draggable handle at all times.
        # AsNeeded combined with widgetResizable and responsive label shrinking
        # squeezed the content and clipped controls (e.g. "Load config") without
        # ever spawning a horizontal bar, leaving the mouse no way to reach them.
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
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
