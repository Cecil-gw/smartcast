
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from core.adb_manager import AdbError
from core.device_control import ScreenBackup, ScreenControlError, ScreenControlManager


class ScreenCommandThread(QThread):
    """Runs one screen-control operation off the UI thread."""

    finished_with_result = Signal(str, object, str)  # op, payload(dict|None), error("")

    def __init__(self, manager: ScreenControlManager, serial: str, op: str,
                 backup: ScreenBackup, value: int | None = None,
                 mode: str | None = None, auto: bool | None = None, parent=None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.serial = serial
        self.op = op
        self.backup = backup
        self.value = value
        self.mode = mode
        self.auto = auto

    def run(self) -> None:
        payload = None
        error = ""
        try:
            if self.op == "get_info":
                info = self.manager.get_brightness(self.serial, self.backup)
                info.update(self.manager.get_rotation(self.serial, self.backup))
                info["screen_off_timeout"] = self.manager.get_screen_off_timeout(self.serial, self.backup)
                payload = info
            elif self.op == "set_brightness":
                payload = {"brightness": self.manager.set_brightness(self.serial, self.backup, self.value, self.auto)}
            elif self.op == "set_auto_brightness":
                payload = {"brightness": self.manager.set_brightness(self.serial, self.backup, 128, True)}
            elif self.op == "set_rotation":
                payload = {"orientation": self.manager.set_rotation(self.serial, self.backup, self.mode)}
            elif self.op == "always_on":
                payload = {"screen_off_timeout": self.manager.set_screen_always_on(self.serial, self.backup)}
            elif self.op == "restore_timeout":
                payload = {"screen_off_timeout": self.manager.restore_screen_timeout(self.serial, self.backup)}
            elif self.op == "restore_all":
                payload = {"restored": self.manager.restore_all(self.serial, self.backup)}
            else:
                error = f"未知屏幕操作：{self.op}"
        except (ScreenControlError, AdbError) as exc:
            error = str(exc)
        except Exception as exc:  # keep UI responsive on unexpected errors
            error = f"执行异常：{exc}"
        self.finished_with_result.emit(self.op, payload, error)
