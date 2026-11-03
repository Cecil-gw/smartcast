from PySide6.QtCore import QThread, Signal

from core.adb_manager import AdbManager
from core.device_info import DeviceInfo
from core.encoder_detector import EncoderDetector


class EncoderDetectionThread(QThread):
    detected = Signal(str, list)

    def __init__(self, adb: AdbManager, device: DeviceInfo) -> None:
        super().__init__()
        self.adb = adb
        self.device = device

    def run(self) -> None:
        candidates = EncoderDetector(self.adb).detect(self.device)
        self.detected.emit(self.device.serial, candidates)
