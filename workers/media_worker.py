
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from core.adb_manager import AdbError
from core.media_manager import MediaManager, MediaRecord


class ScreenshotThread(QThread):
    finished_with_result = Signal(object, str)  # record | None, error

    def __init__(self, manager: MediaManager, serial: str, device_name: str, parent=None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.serial = serial
        self.device_name = device_name

    def run(self) -> None:
        try:
            record = self.manager.screenshot(self.serial, self.device_name)
            self.finished_with_result.emit(record, "")
        except Exception as error:
            self.finished_with_result.emit(None, str(error))


class RecordControlThread(QThread):
    finished_with_result = Signal(bool, str, object)  # ok, message, record|None

    def __init__(self, manager: MediaManager, serial: str, device_name: str,
                 scrcpy_path: str, action: str, parent=None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.serial = serial
        self.device_name = device_name
        self.scrcpy_path = scrcpy_path
        self.action = action

    def run(self) -> None:
        try:
            if self.action == "start":
                record = self.manager.start_recording(self.serial, self.device_name, self.scrcpy_path)
                self.finished_with_result.emit(True, "录屏已开始", record)
            else:
                record = self.manager.stop_recording(self.serial)
                self.finished_with_result.emit(True, "录屏已停止并保存", record)
        except Exception as error:
            self.finished_with_result.emit(False, str(error), None)
