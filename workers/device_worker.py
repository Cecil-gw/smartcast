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
        self._recovery_level = 0   # 0=正常 1=重启服务 2=彻底重置
        self._failure_streak = 0   # 连续失败次数
        self._scanning = False     # 防重入

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

    def _try_recover(self) -> bool:
        """分级自动恢复：先重启服务，仍失败则彻底重置。12 秒内不重复。"""
        import time

        now = time.monotonic()
        if now - self._last_recovery < 12:
            return False
        self._last_recovery = now

        if self._recovery_level == 0:
            self._recovery_level = 1
            return self.adb.recover_server()
        self._recovery_level = 2
        hard_reset = getattr(self.adb, "hard_reset_server", None)
        if hard_reset is not None:
            return bool(hard_reset())
        return self.adb.recover_server()

    def _scan_devices(self) -> list[RawDevice]:
        """扫描设备；失败时按级别自动恢复并重试。"""
        try:
            return self.adb.devices()
        except AdbError as error:
            message = str(error)
            if not is_server_fault(message):
                raise
            self._failure_streak += 1
            self.logger.warning("ADB 扫描失败（连续 %s 次）：%s", self._failure_streak, message)
            if self._try_recover():
                return self.adb.devices()
            raise

    @Slot()
    def scan(self) -> None:
        if self._scanning:
            return  # 上一轮扫描还没结束，跳过本次定时触发
        self._scanning = True
        try:
            raw_devices = self._scan_devices()
            self._failure_streak = 0
            self._recovery_level = 0
            self._reset_backoff()
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
            self._apply_backoff()
        finally:
            self._scanning = False

    def _apply_backoff(self) -> None:
        """连续失败时临时降低扫描频率，避免反复打服务端。"""
        timer = getattr(self, "timer", None)
        if timer is None:
            return
        factor = min(4, max(1, self._failure_streak))
        timer.setInterval(self.interval * factor)

    def _reset_backoff(self) -> None:
        timer = getattr(self, "timer", None)
        if timer is not None:
            timer.setInterval(self.interval)
