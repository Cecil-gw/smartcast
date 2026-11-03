import sys

from PySide6.QtWidgets import QApplication, QPushButton, QTextEdit

from core.encoder_detector import CodecCandidate
from core.device_info import DeviceInfo
from ui.device_card import DeviceCard
from ui.device_detail import DeviceDetailDialog
from ui.settings_dialog import DeviceSettingsDialog, SettingsDialog
from utils.config_manager import ConfigManager


app = QApplication(sys.argv)
config = ConfigManager()
device = DeviceInfo("serial", "device", "ZTE", "ZTE", "W201DS", "13", "33", "1200x1920", "260")
codecs = [CodecCandidate("H.264", "c2.unisoc.avc.encoder", True, 11)]

card = DeviceCard(device)
card.set_codecs(codecs)
assert "c2.unisoc.avc.encoder" in card.codec_label.text()

emitted = []
card.details_requested.connect(emitted.append)
detail_button = next(button for button in card.findChildren(QPushButton) if button.text() == "详情")
detail_button.click()
assert emitted == ["serial"]

dialog = DeviceSettingsDialog({"video_codec": "H.265", "resolution": "1080p", "fps": 60, "bitrate_mbps": 8}, codecs)
assert [dialog.codec.itemText(i) for i in range(dialog.codec.count())] == ["auto", "H.264"]
dialog.codec.setCurrentText("H.264")
dialog.resolution.setCurrentText("1080")
dialog.fps.setCurrentText("120")
dialog.bitrate.setValue(16)
assert dialog.parameters() == {
    "video_codec": "H.264",
    "resolution": "1080",
    "fps": 120,
    "bitrate_mbps": 16,
    "audio": True,
}

detail = DeviceDetailDialog(device, codecs)
assert "c2.unisoc.avc.encoder" in detail.findChild(QTextEdit).toPlainText()

settings = SettingsDialog(config)
assert hasattr(settings, "save")

print("dialog smoke passed")
