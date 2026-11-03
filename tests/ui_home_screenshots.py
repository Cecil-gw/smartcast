import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from core.device_info import DeviceInfo
from core.encoder_detector import CodecCandidate
from ui.main_window import MainWindow
from ui.theme import stylesheet_for
from utils.config_manager import ConfigManager


app = QApplication(sys.argv)
config = ConfigManager()
app.setStyleSheet(stylesheet_for(config.settings.get("theme", "light")))
window = MainWindow(config)
window.worker.devices_changed.disconnect(window.refresh_devices)
window._detect_codecs = lambda *args, **kwargs: None
window.show()

device = DeviceInfo("320146588834", "device", "ZTE", "ZTE", "W201DS", "13", "33", "1200x1920", "260")
codecs = [
    CodecCandidate("H.264", "c2.unisoc.avc.encoder", True, 11),
    CodecCandidate("H.264", "c2.android.avc.encoder", False, 1),
]
out = Path("tests/shots")
out.mkdir(parents=True, exist_ok=True)
for width, height, name in ((1280, 720, "home-1280x720"), (1366, 768, "home-1366x768")):
    window.resize(width, height)
    window.refresh_devices([device], "设备扫描完成")
    window.overview_page.set_device_codecs(device.serial, codecs)
    for _ in range(8):
        app.processEvents()
    window.grab().save(str(out / f"{name}.png"))
window.close()
app.quit()
print("home screenshots saved")
