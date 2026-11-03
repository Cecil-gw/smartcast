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
        assert hasattr(window, "network")
        assert window.device_page.network_button.text() == "网络连接设备"
        # media feature must be fully wired (page, manager, worker state)
        assert hasattr(window, "media_page")
        assert hasattr(window, "media")
        assert hasattr(window, "_media_threads")
        assert hasattr(window, "_recording_serials")
        window._navigate("media")
        app.processEvents()
        assert window.stack.currentWidget() is window.media_page
        window._navigate("sessions")
        app.processEvents()
        assert window.stack.currentWidget() is window.sessions_page
        window._navigate("devices")
        app.processEvents()
        print("main window network wiring smoke passed")
        window.close()
        window.device_thread.quit()
        window.device_thread.wait(3000)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
