"""Responsive layout management for VinaLab."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLabel, QLayout, QMainWindow, QSizePolicy, QSplitter, QTabBar, QToolButton


class ResponsiveManager:
    """Apply screen-profile-specific typography, spacing, and splitter settings."""

    PROFILE_SETTINGS = {
        "compact": {
            "base_font": 9,
            "icon_size": 16,
            "tab_height": 26,
            "padding": 3,
            "h_splitter_ratio": [42, 58],
            "v_splitter_ratio": [38, 62],
            "minimum_size": [980, 640],
        },
        "standard": {
            "base_font": 10,
            "icon_size": 18,
            "tab_height": 30,
            "padding": 6,
            "h_splitter_ratio": [38, 62],
            "v_splitter_ratio": [36, 64],
            "minimum_size": [1120, 720],
        },
        "large": {
            "base_font": 11,
            "icon_size": 22,
            "tab_height": 34,
            "padding": 9,
            "h_splitter_ratio": [34, 66],
            "v_splitter_ratio": [34, 66],
            "minimum_size": [1280, 760],
        },
        "ultrawide": {
            "base_font": 12,
            "icon_size": 24,
            "tab_height": 38,
            "padding": 12,
            "h_splitter_ratio": [30, 70],
            "v_splitter_ratio": [32, 68],
            "minimum_size": [1360, 820],
        },
    }

    @classmethod
    def detect_screen_profile(cls, screen) -> str:
        """Detect the screen profile from available screen geometry."""
        if screen is None:
            return "standard"
        geometry = screen.availableGeometry()
        width = geometry.width()
        height = geometry.height()
        if width < 1280 or height < 720:
            return "compact"
        if width < 1920:
            return "standard"
        if width < 2560:
            return "large"
        return "ultrawide"

    @classmethod
    def profile_for_width(cls, width: int, current: str = "standard") -> str:
        """Return a profile based on the current window width."""
        if width < 1280:
            return "compact"
        if width < 1920:
            return "standard"
        if width < 2560:
            return "large"
        return "ultrawide"

    @classmethod
    def apply_profile(cls, window: QMainWindow, profile: str) -> None:
        """Apply a responsive profile to the main window and save it."""
        profile = profile if profile in cls.PROFILE_SETTINGS else "standard"
        settings = cls.PROFILE_SETTINGS[profile]
        app = QApplication.instance()
        if app:
            app.setFont(QFont("Segoe UI", settings["base_font"]))
        window.setMinimumSize(QSize(*settings["minimum_size"]))

        for tab_bar in window.findChildren(QTabBar):
            tab_bar.setMinimumHeight(settings["tab_height"])
        icon_size = QSize(settings["icon_size"], settings["icon_size"])
        for button in window.findChildren(QToolButton):
            button.setIconSize(icon_size)
        for splitter in window.findChildren(QSplitter):
            total = max(splitter.width(), 1)
            ratio = settings["h_splitter_ratio"] if splitter.orientation() == Qt.Horizontal else settings["v_splitter_ratio"]
            if splitter.orientation() == Qt.Vertical:
                total = max(splitter.height(), 1)
            splitter.setSizes([int(total * ratio[0] / 100), int(total * ratio[1] / 100)])
        cls.apply_layout_margins(window, settings["padding"])
        cls.apply_responsive_labels(window)
        cls._save_profile(window, profile)

    @classmethod
    def apply_layout_margins(cls, widget, padding: int) -> None:
        """Apply profile padding recursively to all child layouts."""
        layout = widget.layout() if hasattr(widget, "layout") else None
        if layout:
            cls._apply_layout(layout, padding)
        for child in widget.findChildren(QLayout):
            cls._apply_layout(child, padding)

    @classmethod
    def connect_screen_change(cls, app: QApplication, window: QMainWindow) -> None:
        """Connect screen changes to automatic profile reapplication."""
        def reapply() -> None:
            """Reapply the best profile after a screen geometry change."""
            profile = cls.detect_screen_profile(window.screen() or app.primaryScreen())
            window.current_screen_profile = profile
            cls.apply_profile(window, profile)

        app.primaryScreenChanged.connect(lambda *_: reapply())
        screen = window.screen()
        if screen:
            screen.geometryChanged.connect(lambda *_: reapply())

    @classmethod
    def _apply_layout(cls, layout: QLayout, padding: int) -> None:
        """Apply margins and spacing to one layout."""
        layout.setContentsMargins(padding, padding, padding, padding)
        layout.setSpacing(padding)

    @staticmethod
    def apply_responsive_labels(window: QMainWindow) -> None:
        """Allow labels to shrink and wrap instead of clipping on small screens."""
        for label in window.findChildren(QLabel):
            label.setWordWrap(True)
            label.setMinimumWidth(0)
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    @staticmethod
    def _save_profile(window: QMainWindow, profile: str) -> None:
        """Persist the selected screen profile."""
        prefs_path = Path(__file__).resolve().parents[1] / "config" / "user_prefs.json"
        prefs = {}
        if prefs_path.exists():
            try:
                prefs = json.loads(prefs_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                prefs = {}
        prefs["screen_profile"] = profile
        prefs_path.parent.mkdir(parents=True, exist_ok=True)
        prefs_path.write_text(json.dumps(prefs, indent=2, ensure_ascii=False), encoding="utf-8")
