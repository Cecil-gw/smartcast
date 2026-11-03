from __future__ import annotations

import re
from dataclasses import dataclass, field

from core.adb_manager import AdbError, AdbManager
from utils.logger import setup_logger

BRIGHTNESS_MIN = 1
BRIGHTNESS_MAX = 255


# Android KeyEvent codes (common; some vendor ROMs may differ)
KEY_BACK = 4
KEY_HOME = 3
KEY_RECENT = 187
KEY_VOLUME_UP = 24
KEY_VOLUME_DOWN = 25
KEY_VOLUME_MUTE = 164
KEY_POWER = 26
KEY_WAKEUP = 224
KEY_SLEEP = 235

ACTION_LABELS = {
    "back": "返回",
    "home": "主页",
    "recent": "多任务",
    "volume_up": "音量增加",
    "volume_down": "音量降低",
    "mute": "静音切换",
    "lock": "锁屏",
    "power_menu": "电源菜单",
    "wakeup": "唤醒屏幕",
}


@dataclass(frozen=True)
class ControlResult:
    serial: str
    action: str
    success: bool
    message: str = ""


class DeviceControlManager:
    """ Sends per-device shell commands; serial is always explicit. """

    def __init__(self, adb: AdbManager) -> None:
        self.adb = adb
        self.logger = setup_logger()

    def run_action(self, serial: str, action: str) -> ControlResult:
        label = ACTION_LABELS.get(action, action)
        try:
            if action == "power_menu":
                # Long-press power opens the power menu on most modern ROMs.
                self.adb.shell(serial, "input keyevent --longpress 26", 4.0)
            elif action == "mute":
                self._toggle_mute(serial)
            elif action in ACTION_LABELS:
                code = {
                    "back": KEY_BACK,
                    "home": KEY_HOME,
                    "recent": KEY_RECENT,
                    "volume_up": KEY_VOLUME_UP,
                    "volume_down": KEY_VOLUME_DOWN,
                    "lock": KEY_POWER,
                    "wakeup": KEY_WAKEUP,
                }[action]
                self.adb.shell(serial, f"input keyevent {code}", 4.0)
            else:
                return ControlResult(serial, action, False, f"未知操作：{action}")
            self.logger.info("控制 %s: %s (%s)", serial, action, label)
            return ControlResult(serial, action, True, f"{label} 已执行")
        except AdbError as error:
            self.logger.warning("控制 %s: %s 失败 - %s", serial, action, error)
            return ControlResult(serial, action, False, f"{label} 失败：{error}")

    def _toggle_mute(self, serial: str) -> None:
        # KEYCODE_VOLUME_MUTE toggles the ringer; reading the exact state is
        # ROM-specific, so we only verify the command succeeded.
        self.adb.shell(serial, f"input keyevent {KEY_VOLUME_MUTE}", 4.0)


# ------------------------------------------------------------------
# Stage 2: screen control with original-value backup
# ------------------------------------------------------------------


@dataclass
class ScreenBackup:
    """Original Android settings captured before screen modifications."""

    auto_brightness: str | None = None
    brightness: str | None = None
    accelerometer_rotation: str | None = None
    user_rotation: str | None = None
    screen_off_timeout: str | None = None

    def to_dict(self) -> dict:
        return {
            "auto_brightness": self.auto_brightness,
            "brightness": self.brightness,
            "accelerometer_rotation": self.accelerometer_rotation,
            "user_rotation": self.user_rotation,
            "screen_off_timeout": self.screen_off_timeout,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScreenBackup":
        return cls(
            auto_brightness=data.get("auto_brightness"),
            brightness=data.get("brightness"),
            accelerometer_rotation=data.get("accelerometer_rotation"),
            user_rotation=data.get("user_rotation"),
            screen_off_timeout=data.get("screen_off_timeout"),
        )


_ROTATION_RE = re.compile(r"\d+")


class ScreenControlError(Exception):
    pass


class ScreenControlManager:
    """Read/modify brightness, rotation and screen-off timeout per device.

    Every mutating call captures the original value once (if no backup
    exists yet) so a later ``restore_all`` returns the phone to the state
    the user had before SmartCast touched anything.
    """

    def __init__(self, adb: AdbManager) -> None:
        self.adb = adb
        self.logger = setup_logger()

    # -- low-level helpers -------------------------------------------------
    def _get(self, serial: str, key: str) -> str | None:
        try:
            value = self.adb.shell(serial, f"settings get system {key}", 5.0)
        except AdbError as error:
            raise ScreenControlError(f"读取 {key} 失败：{error}") from error
        value = (value or "").strip()
        return value or None

    def _put(self, serial: str, key: str, value: str) -> None:
        try:
            self.adb.shell(serial, f"settings put system {key} {value}", 5.0)
        except AdbError as error:
            raise ScreenControlError(f"设置 {key}={value} 失败：{error}") from error

    def _capture(self, backup: ScreenBackup, serial: str, key: str, attr: str) -> None:
        if getattr(backup, attr) is None:
            setattr(backup, attr, self._get(serial, key))

    # -- brightness --------------------------------------------------------
    def get_brightness(self, serial: str, backup: ScreenBackup) -> dict:
        auto = self._get(serial, "screen_brightness_mode")
        value = self._get(serial, "screen_brightness")
        backup.auto_brightness = auto if backup.auto_brightness is None else backup.auto_brightness
        backup.brightness = value if backup.brightness is None else backup.brightness
        try:
            current = int(value) if value else None
        except ValueError:
            current = None
        return {
            "auto": auto == "1",
            "brightness": current,
            "min": BRIGHTNESS_MIN,
            "max": BRIGHTNESS_MAX,
        }

    def set_brightness(self, serial: str, backup: ScreenBackup, value: int, auto: bool | None = None) -> int:
        if auto is False:
            self._capture(backup, serial, "screen_brightness_mode", "auto_brightness")
            self._put(serial, "screen_brightness_mode", "0")
        elif auto is True:
            self._capture(backup, serial, "screen_brightness_mode", "auto_brightness")
            self._put(serial, "screen_brightness_mode", "1")
            return -1  # auto mode; manual value not applied
        self._capture(backup, serial, "screen_brightness", "brightness")
        if not BRIGHTNESS_MIN <= value <= BRIGHTNESS_MAX:
            raise ScreenControlError(f"亮度超出范围 {BRIGHTNESS_MIN}~{BRIGHTNESS_MAX}")
        self._put(serial, "screen_brightness", str(value))
        return value

    # -- rotation ----------------------------------------------------------
    ROTATION_VALUES = {"auto": None, "portrait": "0", "landscape": "1"}

    def get_rotation(self, serial: str, backup: ScreenBackup) -> dict:
        accel = self._get(serial, "accelerometer_rotation")
        user = self._get(serial, "user_rotation")
        backup.accelerometer_rotation = accel if backup.accelerometer_rotation is None else backup.accelerometer_rotation
        backup.user_rotation = user if backup.user_rotation is None else backup.user_rotation
        auto = accel == "1"
        orientation = "auto"
        if not auto:
            orientation = "landscape" if user == "1" else "portrait"
        return {"auto": auto, "orientation": orientation}

    def set_rotation(self, serial: str, backup: ScreenBackup, mode: str) -> str:
        self._capture(backup, serial, "accelerometer_rotation", "accelerometer_rotation")
        self._capture(backup, serial, "user_rotation", "user_rotation")
        if mode == "auto":
            self._put(serial, "accelerometer_rotation", "1")
            return "auto"
        if mode not in ("portrait", "landscape"):
            raise ScreenControlError(f"未知旋转模式：{mode}")
        self._put(serial, "accelerometer_rotation", "0")
        self._put(serial, "user_rotation", self.ROTATION_VALUES[mode])
        return mode

    # -- screen-off timeout ------------------------------------------------
    def get_screen_off_timeout(self, serial: str, backup: ScreenBackup) -> int | None:
        value = self._get(serial, "screen_off_timeout")
        backup.screen_off_timeout = value if backup.screen_off_timeout is None else backup.screen_off_timeout
        try:
            return int(value) if value else None
        except ValueError:
            return None

    def set_screen_always_on(self, serial: str, backup: ScreenBackup) -> int:
        self._capture(backup, serial, "screen_off_timeout", "screen_off_timeout")
        self._put(serial, "screen_off_timeout", "2147483647")
        return 2147483647

    def restore_screen_timeout(self, serial: str, backup: ScreenBackup) -> int | None:
        if backup.screen_off_timeout is None:
            raise ScreenControlError("没有记录原始休眠时间")
        self._put(serial, "screen_off_timeout", backup.screen_off_timeout)
        try:
            return int(backup.screen_off_timeout)
        except ValueError:
            return None

    # -- restore -----------------------------------------------------------
    def restore_all(self, serial: str, backup: ScreenBackup) -> dict:
        """Restore every captured setting; skips values never captured."""
        restored: dict[str, str] = {}
        pairs = (
            ("screen_brightness_mode", "auto_brightness"),
            ("screen_brightness", "brightness"),
            ("accelerometer_rotation", "accelerometer_rotation"),
            ("user_rotation", "user_rotation"),
            ("screen_off_timeout", "screen_off_timeout"),
        )
        for key, attr in pairs:
            value = getattr(backup, attr)
            if value is None:
                continue
            try:
                self._put(serial, key, value)
                restored[key] = value
            except ScreenControlError as error:
                self.logger.warning("恢复 %s 失败：%s", key, error)
        return restored
