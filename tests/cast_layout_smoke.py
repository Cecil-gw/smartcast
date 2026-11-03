import tempfile
from pathlib import Path

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QScrollArea

from ui.main_window import MainWindow
from utils.config_manager import ConfigManager


app = QApplication([])

with tempfile.TemporaryDirectory() as temp:
    window = MainWindow(ConfigManager(Path(temp)))
    window.show()

    def check(width, height, compact):
        window.resize(width, height)
        window.show_cast_settings_page()
        app.processEvents()
        app.processEvents()
        panel = window.cast_page.quick_config
        assert panel._compact_parameters is compact
        controls = [panel.codec, panel.resolution, panel.fps, panel.bitrate]
        names = ["codec", "resolution", "fps", "bitrate"]
        boxes = []
        for control in controls:
            assert control.width() >= 230
            assert control.minimumSizeHint().width() <= control.width() + 2
            top_left = control.mapTo(panel, control.rect().topLeft())
            boxes.append((top_left.x(), top_left.y(), top_left.x() + control.width(), top_left.y() + control.height()))
        for index, left in enumerate(boxes):
            for other, right in enumerate(boxes[index + 1:], index + 1):
                overlap_x = min(left[2], right[2]) > max(left[0], right[0])
                overlap_y = min(left[3], right[3]) > max(left[1], right[1])
                assert not (overlap_x and overlap_y), (width, names[index], names[other], left, right)
        areas = window.cast_page.findChildren(QScrollArea)
        assert areas and areas[0].widgetResizable()

    check(1280, 720, False)
    check(1366, 768, False)
    check(900, 640, True)
    window.close()

print("cast layout smoke passed")
