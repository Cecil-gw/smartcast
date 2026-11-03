from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal


class LogEmitter(QObject):
    message = Signal(str)


class QtLogHandler(logging.Handler):
    def __init__(self, emitter: LogEmitter) -> None:
        super().__init__(level=logging.INFO)
        self.emitter = emitter
        self.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-5s  %(message)s", "%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.emitter.message.emit(self.format(record))
        except Exception:
            self.handleError(record)
