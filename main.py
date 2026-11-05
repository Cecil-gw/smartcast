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


def _set_taskbar_identity() -> None:
    """让 Windows 任务栏使用本程序自己的图标，而不是通用/空白图标。

    未设置 AppUserModelID 时，Python 打包应用的任务栏图标可能显示为空白，
    因为任务栏按钮归属不到 exe 内嵌的图标资源。
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Cecil.SmartCast.Desktop"
        )
    except Exception:
        pass


def main() -> int:
    _set_taskbar_identity()
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
