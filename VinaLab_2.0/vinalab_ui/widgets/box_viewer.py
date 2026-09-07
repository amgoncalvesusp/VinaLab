"""Offline Three.js viewport hosted by Qt; coordinates are always Angstroms."""

from __future__ import annotations

import json
import math
from collections.abc import Iterable
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

try:
    # Import before QApplication; Qt 6.7 can deadlock loading this DLL in showEvent.
    # No browser/profile/page is constructed until the viewport is shown.
    from PySide6.QtWebEngineCore import (
        QWebEnginePage,
        QWebEngineProfile,
        QWebEngineSettings,
        QWebEngineUrlRequestInterceptor,
    )
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    QWebEngineView = None

from vinalab_core.docking.search_box import SearchBox

ASSET_DIRECTORY = Path(__file__).resolve().parent / "assets" / "box_viewer"


def validate_coordinates(coordinates: Iterable) -> tuple[tuple[float, float, float], ...]:
    """Reject incomplete/nonfinite data before passing anything to JavaScript."""
    try:
        points = tuple(tuple(float(value) for value in point) for point in coordinates)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("Coordinates must be finite XYZ triples") from error
    if not points or any(len(p) != 3 or not all(math.isfinite(v) for v in p) for p in points):
        raise ValueError("Coordinates must be nonempty finite XYZ triples")
    return points


def box_payload(box: SearchBox) -> dict:
    values = (*box.center, *box.size, box.margin)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("Search box values must be finite")
    return {"center": list(box.center), "size": list(box.size)}


class BoxViewer(QWidget):
    """Lazy WebEngine initialization keeps hidden workflow tabs inexpensive."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dockingBoxViewer")
        self.setMinimumSize(240, 280)
        self._scene = {"receptor": [], "reference": [], "box": None}
        self._web = None
        self._page = None
        self._profile = None
        self._interceptor = None
        self._auto_fit = True
        self._renderer_ready = False
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._status = QLabel("", self)
        self._status.setWordWrap(True)
        self._layout.addWidget(self._status)

    @property
    def scene_data(self) -> dict:
        return json.loads(json.dumps(self._scene, allow_nan=False))

    def set_box(self, box: SearchBox) -> None:
        self._scene = {**self._scene, "box": box_payload(box)}
        self._publish()

    def set_coordinates(self, kind: str, coordinates: Iterable) -> None:
        if kind not in {"receptor", "reference"}:
            raise ValueError("Unknown structure layer")
        points = validate_coordinates(coordinates)
        self._scene = {**self._scene, kind: [list(p) for p in points]}
        self._auto_fit = True
        self._publish()

    def clear_coordinates(self, kind: str) -> None:
        """Explicitly remove one molecular layer, preserving the canonical box."""
        if kind not in {"receptor", "reference"}:
            raise ValueError("Unknown structure layer")
        self._scene = {**self._scene, kind: []}
        self._auto_fit = True
        self._publish()

    def reset_view(self) -> None:
        self._auto_fit = True
        self._publish()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._web is None:
            self._start_web_view()

    def _start_web_view(self) -> None:
        if QWebEngineView is None:
            self._status.setText("3D preview unavailable: install PySide6 with QtWebEngine.")
            return
        if not (ASSET_DIRECTORY / "index.html").is_file():
            self._status.setText("3D preview unavailable: bundled viewer assets are missing.")
            return

        class LocalAssetsOnly(QWebEngineUrlRequestInterceptor):
            def interceptRequest(self, info):
                url = info.requestUrl()
                allowed = False
                if url.isLocalFile():
                    allowed = Path(url.toLocalFile()).resolve().is_relative_to(ASSET_DIRECTORY)
                info.block(not allowed)

        viewer = self

        class LocalPage(QWebEnginePage):
            def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
                return url.isLocalFile() and Path(url.toLocalFile()).resolve() == ASSET_DIRECTORY / "index.html"

            def javaScriptConsoleMessage(self, level, message, line_number, source_id):
                if message == "VINALAB_RENDERER_READY":
                    viewer._renderer_ready = True
                    viewer._status.setText("")
                elif message.startswith("VINALAB_RENDERER_ERROR:"):
                    viewer._renderer_ready = False
                    viewer._status.setText(message.partition(":")[2])

        self._web = QWebEngineView(self)
        self._web.setObjectName("dockingBoxWebView")
        self._profile = QWebEngineProfile(self._web)
        self._interceptor = LocalAssetsOnly(self._profile)
        self._profile.setUrlRequestInterceptor(self._interceptor)
        self._page = LocalPage(self._profile, self._web)
        self._web.setPage(self._page)
        settings = self._page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False)
        self._layout.addWidget(self._web, 1)
        self._web.loadFinished.connect(self._loaded)
        self._web.load(QUrl.fromLocalFile(str(ASSET_DIRECTORY / "index.html")))

    def _loaded(self, ok: bool) -> None:
        if not ok:
            self._status.setText("3D preview could not load its local assets.")
            return
        self._publish()
        QTimer.singleShot(1500, self._check_renderer)

    def _check_renderer(self) -> None:
        if not self._renderer_ready:
            self._status.setText("3D preview unavailable: WebGL initialization failed.")

    def _publish(self) -> None:
        if self._web is None:
            return
        payload = json.dumps({**self._scene, "autoFit": self._auto_fit}, allow_nan=False)
        self._web.page().runJavaScript(
            f"window.vinalabPending = {payload}; "
            "if (window.setVinaLabScene) window.setVinaLabScene(window.vinalabPending);"
        )
        self._auto_fit = False
