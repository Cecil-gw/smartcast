import sys
import tempfile
from pathlib import Path

from PySide6.QtWidgets import QApplication, QLabel

from core.encoder_detector import CodecCandidate
from core.device_info import DeviceInfo
from core.scrcpy_manager import ScrcpyManager
from ui.pages.detail_page import DetailPage
from ui.pages.cast_settings_page import CastSettingsPage
from ui.pages.device_page import DevicePage
from ui.pages.settings_page import SettingsPage
from ui.theme import DARK_STYLE
from utils.config_manager import ConfigManager


app = QApplication(sys.argv)
app.setStyleSheet(DARK_STYLE)

device = DeviceInfo("320146588834", "device", "ZTE", "ZTE", "W201DS", "13", "33", "1200x1920", "260")
second = DeviceInfo("192.168.1.8:5555", "device", "HONOR", "HONOR", "MAA-AN00", "16", "36", "1264x2800", "460")
codecs = [
    CodecCandidate("H.264", "c2.unisoc.avc.encoder", True, 11),
    CodecCandidate("H.264", "c2.android.avc.encoder", False, 1),
    CodecCandidate("H.265", "c2.android.hevc.encoder", False, 0),
]

page = DevicePage()
page.resize(1280, 760)
page.show()
app.processEvents()
assert page.stack.currentWidget() is page.empty_state

page.set_devices([device])
app.processEvents()
assert page.stack.currentWidget() is page.scroll
assert list(page.cards) == [device.serial]
card = page.cards[device.serial]
assert "W201DS" in card.title_label.text()
card.set_codecs(codecs)
assert "c2.unisoc.avc.encoder" in card.codec_label.text()

started = []
details = []
page.start_requested.connect(started.append)
page.details_requested.connect(details.append)
card.start_button.click()
card.details_button.click()
assert started == [device.serial]
assert details == [device.serial]

page.set_devices([device, second])
app.processEvents()
assert len(page.cards) == 2
assert page.card_grid._columns >= 1
page.resize(1600, 760)
app.processEvents()
assert page.card_grid._columns >= 2
page.resize(1000, 720)
app.processEvents()
app.processEvents()
assert page.card_grid._columns == 1

page.set_devices([])
app.processEvents()
assert page.stack.currentWidget() is page.empty_state

auto_events = []
page.auto_scan_changed.connect(auto_events.append)
page.auto_scan.setChecked(False)
assert auto_events[-1] is False

applied = []
cast_page = CastSettingsPage()
cast_page.quick_config.applied.connect(applied.append)
cast_page.quick_config.load({"video_codec": "H.264", "resolution": "720", "fps": 30, "bitrate_mbps": 16, "audio": False})
cast_page.quick_config._apply()
assert applied[-1]["resolution"] == "720" and applied[-1]["audio"] is False

settings = SettingsPage()
settings.load({
    "adb_path": "",
    "scrcpy_path": "",
    "scan_interval": 2,
    "casting_scan_interval": 15,
    "auto_scan": True,
    "default_parameters": {"video_codec": "auto", "resolution": "1080p", "fps": 0, "bitrate_mbps": 8},
})
collected = settings.collect()
assert collected["default_parameters"]["resolution"] == "1080"
assert collected["default_parameters"]["audio"] is True
assert collected["casting_scan_interval"] == 15
assert collected["render_driver"] == "opengl"
saved = []
settings.save_requested.connect(saved.append)
settings._emit_save()
assert saved[-1]["scan_interval"] == 2
detected = []
settings.detect_adb_requested.connect(detected.append)
settings.adb_detect_button.click()
assert detected == [""]

detail = DetailPage()
detail.set_device(device, codecs, "idle")
labels = [label.text() for label in detail.findChildren(QLabel)]
assert any("c2.unisoc.avc.encoder" in text for text in labels)
assert any("c2.android.avc.encoder" in text for text in labels)
redetected = []
detail.redetect_requested.connect(redetected.append)
detail.redetect_button.click()
assert redetected == [device.serial]

manager = ScrcpyManager("")
command = manager.build_command(device.serial, "H.264", "original", 0, 8, True)
assert command[:2] == ["-s", device.serial]
assert "--max-size" not in command and "--max-fps" not in command
assert "--render-driver" in command and command[command.index("--render-driver") + 1] == "opengl"
audio_off_command = manager.build_command(device.serial, "H.265", "1080", 60, 16, False)
assert "--no-audio" in audio_off_command

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    (root / "settings.json").write_text(
        '{"scan_interval": "3", "default_parameters": {"resolution": "1080p", "fps": 60}}',
        encoding="utf-8",
    )
    (root / "devices.json").write_text(
        '{"serial": {"parameters": {"video_codec": "H.265", "resolution": "720p"}}}',
        encoding="utf-8",
    )
    compat = ConfigManager(root)
    assert compat.settings["scan_interval"] == 3
    assert compat.settings["casting_scan_interval"] == 0
    assert compat.settings["auto_scan"] is True
    assert compat.settings["render_driver"] == "opengl"
    assert compat.settings["default_parameters"]["audio"] is True
    assert compat.devices["serial"]["parameters"]["resolution"] == "720"
    assert compat.devices["serial"]["parameters"]["audio"] is True
    compat.save()
    reloaded = ConfigManager(root)
    assert reloaded.devices["serial"]["parameters"]["video_codec"] == "H.265"

print("ui refactor smoke passed")

