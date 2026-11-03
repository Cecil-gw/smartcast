import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from core.device_info import DeviceInfo
from core.encoder_detector import CodecCandidate
from ui.main_window import MainWindow
from ui.theme import DARK_STYLE


app = QApplication(sys.argv)
app.setStyleSheet(DARK_STYLE)
window = MainWindow()
window.worker.devices_changed.disconnect(window.refresh_devices)
window._detect_codecs = lambda *args, **kwargs: None
window.resize(1280, 820)
window.show()

phone = DeviceInfo("320146588834", "device", "ZTE", "ZTE", "W201DS", "13", "33", "1200x1920", "260")
honor = DeviceInfo("192.168.1.8:5555", "device", "HONOR", "HONOR", "MAA-AN00", "16", "36", "1264x2800", "460")
zte_codecs = [
    CodecCandidate("H.264", "c2.unisoc.avc.encoder", True, 11),
    CodecCandidate("H.264", "c2.android.avc.encoder", False, 1),
    CodecCandidate("VP9", "c2.android.vp9.encoder", False, 0),
]
honor_codecs = [
    CodecCandidate("H.265", "c2.qti.hevc.encoder", True, 12),
    CodecCandidate("H.264", "c2.qti.avc.encoder", True, 11),
    CodecCandidate("H.264", "c2.android.avc.encoder", False, 1),
]
window.refresh_devices([phone, honor], "设备扫描完成")
window.show_device_page()
window.codecs[phone.serial] = zte_codecs
window.codecs[honor.serial] = honor_codecs
window.device_page.set_card_codecs(phone.serial, zte_codecs)
window.device_page.set_card_codecs(honor.serial, honor_codecs)
window._set_cast_state(phone.serial, "running")
for _ in range(4):
    app.processEvents()

out = Path("tests/shots")
out.mkdir(parents=True, exist_ok=True)
window.grab().save(str(out / "devices-1280.png"))

window.show_cast_settings_page()
for _ in range(4):
    app.processEvents()
window.grab().save(str(out / "cast-1280.png"))

window.open_settings()
for _ in range(4):
    app.processEvents()
window.grab().save(str(out / "settings-1280.png"))

window.show_details(honor.serial)
for _ in range(4):
    app.processEvents()
window.grab().save(str(out / "detail-1280.png"))

window.show_device_page()
window.refresh_devices([], "设备扫描完成")
for _ in range(4):
    app.processEvents()
window.grab().save(str(out / "empty-1280.png"))

window.resize(1000, 720)
window.refresh_devices([phone, honor], "设备扫描完成")
window.show_device_page()
window.device_page.set_card_codecs(phone.serial, zte_codecs)
window.device_page.set_card_codecs(honor.serial, honor_codecs)
for _ in range(6):
    app.processEvents()
window.grab().save(str(out / "devices-1000.png"))
print("screenshots saved")
window.close()
app.quit()


