import ctypes
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


def _ensure_single_instance() -> bool:
    """通过命名互斥体确保同时只能运行一个 SmartCast 实例。

    第二个实例启动时会弹窗提示并自动退出，避免两个 adb 服务端互相冲突。
    """
    if sys.platform != "win32":
        return True
    try:
        handle = ctypes.windll.kernel32.CreateMutexW(None, False, "SmartCast_SingleInstance_Mutex")
        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            return False
    except Exception:
        return True  # 互斥体创建失败时保守放行，不阻断启动
    return True


def main() -> int:
    _set_taskbar_identity()

    if not _ensure_single_instance():
        import ctypes as _ct

        _ct.windll.user32.MessageBoxW(
            None,
            "SmartCast 已经在运行中。\n"
            "请使用已打开的窗口，或先关闭它再启动新实例。\n\n"
            "（多个实例会互相抢占 ADB 服务端，导致设备扫描失败）",
            "SmartCast",
            0x40 | 0x30,  # MB_ICONINFORMATION | MB_SETFOREGROUND
        )
        return 0

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
