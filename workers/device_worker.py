from PySide6.QtCore import QObject, Signal, QTimer, Slot

from core.adb_manager import AdbError, AdbManager, RawDevice, is_server_fault
from core.device_info import DeviceInfo, DeviceInfoReader
from utils.logger import setup_logger


class DeviceWorker(QObject):
    devices_changed = Signal(list, str)

    def __init__(self, adb: AdbManager, interval: int = 2) -> None:
        super().__init__()
        self.adb = adb
        self.logger = setup_logger()
        self.reader = DeviceInfoReader(adb)
        self.cache: dict[str, DeviceInfo] = {}
        self.interval = interval * 1000
        self.enabled = True
        self.paused = False
        self._last_scan_signature: tuple | None = None
        self._last_error: str | None = None
        self._last_recovery = 0.0  # 上次自动恢复的时间（限频用）

    @Slot()
    def start(self) -> None:
        self.timer = QTimer(self)
        self.timer.setInterval(self.interval)
        self.timer.timeout.connect(self.scan)
        self._update_timer()
        self.scan()

    @Slot(int)
    def set_interval(self, seconds: int) -> None:
        self.interval = max(1, seconds) * 1000
        timer = getattr(self, "timer", None)
        if timer is not None:
            timer.setInterval(self.interval)

    @Slot(bool)
    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self._update_timer()
        if enabled and not self.paused:
            self.scan()

    @Slot(bool)
    def set_paused(self, paused: bool) -> None:
        self.paused = paused
        self._update_timer()
        if not paused and self.enabled:
            self.scan()

    def _update_timer(self) -> None:
        timer = getattr(self, "timer", None)
        if timer is None:
            return
        if self.enabled and not self.paused:
            timer.start(self.interval)
        else:
            timer.stop()

    def _try_recover(self, message: str) -> bool:
        """ADB 服务端故障时做一次受控恢复，30 秒内不重复触发。"""
        import time

        if not is_server_fault(message):
            return False
        now = time.monotonic()
        if now - self._last_recovery < 30:
            return False
        self._last_recovery = now
        return self.adb.recover_server()

    @Slot()
    def scan(self) -> None:
        try:
            try:
                raw_devices: list[RawDevice] = self.adb.devices()
            except AdbError as first_error:
                # 服务端握手失败/超时：自动恢复后重试一次
                if self._try_recover(str(first_error)):
                    raw_devices = self.adb.devices()
                elif "timed out" in str(first_error).lower():
                    # 服务繁忙导致的偶发超时，直接重试一次
                    raw_devices = self.adb.devices()
                else:
                    raise
            signature = tuple((item.serial, item.state) for item in raw_devices)
            if signature != self._last_scan_signature:
                self.logger.info("Device scan: %s", list(signature))
                self._last_scan_signature = signature
            self._last_error = None
            current: list[DeviceInfo] = []
            for raw in raw_devices:
                cached = self.cache.get(raw.serial)
                if cached and cached.state == raw.state:
                    current.append(cached)
                else:
                    info = self.reader.read(raw)
                    self.cache[raw.serial] = info
                    current.append(info)
            for serial in list(self.cache):
                if serial not in {item.serial for item in current}:
                    del self.cache[serial]
            self.devices_changed.emit(current, "设备扫描完成")
        except AdbError as error:
            if str(error) != self._last_error:
                self.logger.warning("Device scan failed: %s", error)
                self._last_error = str(error)
            self.devices_changed.emit(list(self.cache.values()), str(error))
