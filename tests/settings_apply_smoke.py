import sys
import tempfile
from pathlib import Path

from PySide6.QtWidgets import QApplication

from core.device_info import DeviceInfo
from ui.main_window import MainWindow
from utils.config_manager import ConfigManager


app = QApplication(sys.argv)
with tempfile.TemporaryDirectory() as temp:
    config = ConfigManager(Path(temp))
    window = MainWindow(config)
    window.worker.devices_changed.disconnect(window.refresh_devices)
    window.save_settings({
        "adb_path": "",
        "scrcpy_path": "",
        "scan_interval": 5,
        "casting_scan_interval": 20,
        "auto_scan": False,
        "default_parameters": {
            "video_codec": "H.264",
            "resolution": "720",
            "fps": 30,
            "bitrate_mbps": 16,
            "audio": False,
        },
    })
    assert config.settings["scan_interval"] == 5
    assert config.settings["casting_scan_interval"] == 20
    assert config.settings["auto_scan"] is False
    assert config.settings["default_parameters"]["audio"] is False
    assert window.base_scan_interval == 5
    assert window.casting_scan_interval == 20
    assert window.auto_scan_enabled is False
    assert config.settings["render_driver"] == "opengl"

    window.current_devices["serial"] = DeviceInfo("serial", "device")
    window.apply_default_parameters({
        "video_codec": "H.265",
        "resolution": "original",
        "fps": 0,
        "bitrate_mbps": 8,
        "audio": True,
    })
    assert config.devices["serial"]["parameters"]["video_codec"] == "H.265"
    assert config.devices["serial"]["parameters"]["audio"] is True
    assert (Path(temp) / "settings.json").exists()
    window.close()

print("settings apply smoke passed")
