import tempfile
from pathlib import Path

from PySide6.QtWidgets import QApplication, QFrame, QLabel

from core.device_info import DeviceInfo
from core.encoder_detector import CodecCandidate
from ui.main_window import MainWindow
from utils.config_manager import ConfigManager


app = QApplication([])

with tempfile.TemporaryDirectory() as temp:
    window = MainWindow(ConfigManager(Path(temp)))
    window.worker.devices_changed.disconnect(window.refresh_devices)
    window._detect_codecs = lambda *args, **kwargs: None
    device = DeviceInfo("320146588834", "device", "ZTE", "ZTE", "W201DS", "13", "33", "1200x1920", "260")
    codecs = [CodecCandidate("H.264", "c2.unisoc.avc.encoder", True, 11)]

    def check_size(width: int, height: int) -> None:
        window.resize(width, height)
        window.show()
        window.refresh_devices([device], "设备扫描完成")
        window.overview_page.set_device_codecs(device.serial, codecs)
        app.processEvents()
        app.processEvents()

        overview = window.overview_page
        stats = [child for child in overview.findChildren(QFrame) if child.objectName() == "StatCard"]
        actions = [child for child in overview.findChildren(QFrame) if child.objectName() == "ActionCard"]
        assert len(stats) == 4
        assert len(actions) == 4

        def bounds(widget) -> tuple[int, int, int, int]:
            top_left = widget.mapTo(overview, widget.rect().topLeft())
            return (top_left.x(), top_left.y(), top_left.x() + widget.width(), top_left.y() + widget.height())

        for group in (stats, actions):
            boxes = [bounds(item) for item in group]
            for i, left in enumerate(boxes):
                for right in boxes[i + 1:]:
                    overlap_x = min(left[2], right[2]) > max(left[0], right[0])
                    overlap_y = min(left[3], right[3]) > max(left[1], right[1])
                    assert not (overlap_x and overlap_y), f"cards overlap at {width}x{height}"

        for card in stats + actions:
            assert card.width() >= 220, (width, card.width())
            for child in card.findChildren(QLabel):
                assert child.geometry().right() <= card.width() + 1
                assert child.geometry().bottom() <= card.height() + 1

        assert window.overview_page.control_panel.serial == device.serial
        assert window.overview_page.control_panel.buttons[0].isEnabled()
        assert window.overview_page.screen_card.serial == device.serial

    check_size(1280, 720)
    check_size(1366, 768)
    window.close()

print("home layout smoke passed")

