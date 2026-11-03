import sys
from pathlib import Path

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from ui.components.wheel_guard import WheelGuard

from ui.main_window import MainWindow
from ui.theme import stylesheet_for
from utils.config_manager import ConfigManager


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


def app_icon() -> QIcon:
    icon_file = resource_path("resources/assets/app-icon.ico")
    if not icon_file.exists():
        icon_file = resource_path("resources/assets/app-icon.png")
    return QIcon(str(icon_file))


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("SmartCast")
    app.setApplicationDisplayName("SmartCast")
    app.setWindowIcon(app_icon())
    app.setStyle("Fusion")
    # combo boxes / spin boxes must not react to mouse-wheel scrolling
    app.installEventFilter(WheelGuard(app))
    app.setFont(QFont("Microsoft YaHei UI", 10))
    config = ConfigManager()
    app.setStyleSheet(stylesheet_for(config.settings.get("theme", "light")))
    window = MainWindow(config)
    window.setWindowIcon(app_icon())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
