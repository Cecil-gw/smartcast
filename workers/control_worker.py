from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from core.adb_manager import AdbError, AdbManager
from core.device_control import ControlResult, DeviceControlManager


class ControlCommandThread(QThread):
    """ Runs one device-control action off the UI thread. """

    finished_with_result = Signal(object)

    def __init__(self, manager: DeviceControlManager, serial: str, action: str, parent=None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.serial = serial
        self.action = action

    def run(self) -> None:
        try:
            result = self.manager.run_action(self.serial, self.action)
        except AdbError as error:
            result = ControlResult(self.serial, self.action, False, str(error))
        except Exception as error:  # never leave the UI waiting
            result = ControlResult(self.serial, self.action, False, f"执行异常：{error}")
        self.finished_with_result.emit(result)
