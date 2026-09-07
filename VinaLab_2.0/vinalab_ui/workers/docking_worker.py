"""Non-blocking Qt worker for one Vina docking request."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from PySide6.QtCore import QThread, Signal

from vinalab_core.docking.docking_service import DockingRunResult
from vinalab_ui.widgets.docking_panel import DockingRequest


class DockingServiceProtocol(Protocol):
    def run(self, **kwargs: object) -> DockingRunResult: ...


class DockingWorker(QThread):
    """Runs the core service without accessing Qt widgets from the worker thread."""

    completed = Signal(object)
    failed = Signal(str)
    process_finished = Signal(object)

    def __init__(
        self,
        service: DockingServiceProtocol,
        request: DockingRequest,
        output: Path,
        parent: QThread | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.request = request
        self.output = output

    def run(self) -> None:
        try:
            result = self.service.run(
                receptor=self.request.receptor,
                ligand=self.request.ligand,
                output=self.output,
                search_box=self.request.search_box,
                cpu_threads=self.request.cpu_threads,
                exhaustiveness=self.request.exhaustiveness,
                seed=self.request.seed,
                scoring=self.request.scoring,
                num_modes=self.request.num_modes,
            )
        except Exception as error:  # pragma: no cover  # noqa: BLE001 - Native failures use Qt signals.
            self.failed.emit(str(error))
            return
        if result.ok:
            self.process_finished.emit(result.process)
            self.completed.emit(result)
        else:
            self.process_finished.emit(result.process)
            self.failed.emit("\n".join((*result.errors, result.process.stderr.strip()))
                             .strip() or "Vina exited without a result")
