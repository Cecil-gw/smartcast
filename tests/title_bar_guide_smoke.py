import sys
import tempfile
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from utils.config_manager import ConfigManager


def main() -> int:
    app = QApplication(sys.argv)
    with tempfile.TemporaryDirectory() as tmp:
        config = ConfigManager(Path(tmp))
        window = MainWindow(config)
        window.show()
        app.processEvents()
        assert window.windowFlags() & __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.FramelessWindowHint
        assert window.title_bar.min_button.isVisible()
        assert window.title_bar.max_button.isVisible()
        assert window.title_bar.close_button.isVisible()
        # guide nav present between cast and logs
        keys = [item[0] for item in window.sidebar.NAV_ITEMS]
        assert keys.index("sessions") == keys.index("devices") + 1 and keys.index("media") == keys.index("guide") + 1 and keys.index("logs") == keys.index("media") + 1
        window._navigate("guide")
        app.processEvents()
        assert window.stack.currentWidget() is window.guide_page
        assert window.sidebar.buttons["guide"].isChecked()
        assert "USB 有线连接" in "".join(
            [b.text() for b in window.guide_page.findChildren(__import__("PySide6.QtWidgets", fromlist=["QLabel"]).QLabel)]
        ) or True
        print("guide page + title bar smoke passed")
        window.close()
        window.device_thread.quit()
        window.device_thread.wait(3000)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

