"""Small worker boundary for conversion, validation and rescoring operations."""

from PySide6.QtCore import QThread, Signal


class TaskWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, operation, parent=None):
        super().__init__(parent)
        self.operation = operation

    def run(self):
        try:
            result = self.operation()
        except Exception as error:  # noqa: BLE001 - Arbitrary task failures must be delivered through Qt signals.
            self.failed.emit(str(error))
        else:
            self.completed.emit(result)
