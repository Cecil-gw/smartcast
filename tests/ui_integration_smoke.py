import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from core.encoder_detector import CodecCandidate
from core.device_info import DeviceInfo
from ui.main_window import MainWindow
from ui.theme import DARK_STYLE
from utils.config_manager import ConfigManager


app = QApplication(sys.argv)
app.setStyleSheet(DARK_STYLE)
with tempfile.TemporaryDirectory() as temp:
    window = MainWindow(ConfigManager(Path(temp)))
    window.show()
    window._detect_codecs = lambda *args, **kwargs: None
    window.worker.devices_changed.disconnect(window.refresh_devices)
    fake = DeviceInfo("TEST-SERIAL", "device", "ZTE", "ZTE", "W201DS", "13", "33", "1200x1920", "260")
    window.refresh_devices([fake], "设备扫描完成")
    assert window.stack.currentWidget() is window.overview_page
    assert "TEST-SERIAL" in window.cards
    window.show_device_page()
    assert window.header.device_label.text() == "1 台设备"
    window.show_cast_settings_page()
    assert window.stack.currentWidget() is window.cast_page
    window.show_device_page()
    assert window.stack.currentWidget() is window.device_page
    window.open_settings()
    assert window.stack.currentWidget() is window.settings_page
    assert not window.header.settings_button.isEnabled()
    window.show_device_page()
    assert window.stack.currentWidget() is window.device_page
    window._set_scan_interval(15)

    window.codecs[fake.serial] = [CodecCandidate("H.264", "c2.test.avc.encoder", True, 11)]
    window.scrcpy.start = lambda *args, **kwargs: True
    window.start_cast(fake.serial)
    assert window.cast_states[fake.serial] == "starting"
    window._scrcpy_started(fake.serial)
    assert window.cast_states[fake.serial] == "running"
    window._casting_stopped(fake.serial, 0)
    assert window.cast_states[fake.serial] == "idle"

    def finish() -> None:
        print("integration cards:", sorted(window.cards))
        print("scan_interval_ms:", window.worker.interval)
        window.close()

    QTimer.singleShot(800, finish)
    QTimer.singleShot(3000, app.quit)
    raise SystemExit(app.exec())



