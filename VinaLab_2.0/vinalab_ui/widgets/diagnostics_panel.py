"""Native dependency diagnostics shown before a docking run."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFormLayout, QLabel, QWidget

from vinalab_core.tools.tool_locator import ToolLocator
from vinalab_core.tools.xtb_bundle import XtbBundleValidator


class DiagnosticsPanel(QWidget):
    """Shows a clear native-tool status before the user starts a run."""

    def __init__(self, project_root: str | Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QFormLayout(self)
        status = QLabel(self)
        status.setObjectName("vinaStatus")
        vina = ToolLocator(project_root).find("vina")
        status.setText(f"Available: {vina}" if vina else "Not available: Vina binary was not found")
        layout.addRow("AutoDock Vina", status)

        xtb_status = QLabel(self)
        xtb_status.setObjectName("xtbStatus")
        xtb = XtbBundleValidator(project_root).validate()
        xtb_status.setText(
            f"Available: {xtb.executable}"
            if xtb.ready
            else f"Not available: {'; '.join(xtb.errors)}"
        )
        layout.addRow("xTB (standalone)", xtb_status)

        gpu_status = QLabel(
            "GPU acceleration is not available with the bundled Vina/xTB engines. "
            "Use the CPU threads control in Pose Generation.",
            self,
        )
        gpu_status.setObjectName("gpuStatus")
        gpu_status.setWordWrap(True)
        layout.addRow("Compute capability", gpu_status)
