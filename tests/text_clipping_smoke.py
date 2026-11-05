
"""窄窗口下确保文字不会被裁切（回归防护）。"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
vendor = Path(__file__).resolve().parents[1] / "vendor"
if vendor.is_dir():
    sys.path.insert(0, str(vendor))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from core.device_info import DeviceInfo
from core.media_manager import MediaRecord
from ui.pages.cast_settings_page import CastSettingsPage
from ui.pages.detail_page import DetailPage
from ui.pages.device_page import DevicePage
from ui.pages.guide_page import GuidePage
from ui.pages.log_page import LogPage
from ui.pages.media_page import MediaPage
from ui.pages.overview_page import OverviewPage
from ui.pages.sessions_page import SessionsPage
from utils.config_manager import ConfigManager


app = QApplication.instance() or QApplication([])
app.setStyle("Fusion")

DEVICE = DeviceInfo(
    "320146588834", "device", "ZTE", "ZTE",
    "W201DS-Pro-Max-Ultra-5G-Edition", "13", "33", "1080x2400", "420", "usb",
)


def clipped(page, width: int) -> list[tuple]:
    page.resize(width, 700)
    page.show()
    app.processEvents()
    app.processEvents()
    problems = []
    widgets = list(page.findChildren(QLabel)) + list(page.findChildren(QPushButton))
    for widget in widgets:
        if not widget.isVisible() or widget.width() < 10 or not widget.text():
            continue
        wrap = getattr(widget, "wordWrap", lambda: False)()
        if wrap:
            need = widget.heightForWidth(widget.width())
            if need > widget.height() + 2:
                problems.append(("vertical", widget.text()[:24], need, widget.height()))
        elif widget.sizeHint().width() > widget.width() + 2:
            problems.append(("horizontal", widget.text()[:24], widget.sizeHint().width(), widget.width()))
    page.hide()
    return problems


def check(name: str, page, width: int = 620) -> None:
    problems = clipped(page, width)
    assert not problems, f"{name} 在 {width}px 宽下有 {len(problems)} 处文字被裁: {problems[:3]}"


# 概览：设备名很长 + 屏幕控制按钮
overview = OverviewPage()
overview.set_primary_device(DEVICE, [], "idle")
check("overview", overview)

# 详情：标题 + 操作按钮
detail = DetailPage()
detail.set_device(DEVICE, [], "idle")
check("detail", detail)

# 会话卡
sessions = SessionsPage()
check("sessions", sessions)

# 媒体记录行（超长文件名）
media = MediaPage()
media.set_records([
    MediaRecord(
        file_name="SmartCast_20261104_123456_screenshot_with_a_very_long_name.png",
        path=r"C:\nonexistent\file.png", media_type="screenshot",
        device_name="W201DS-Long-Device-Name", serial="320146588834",
        created="2026-11-04 12:34:56", size=524288,
    )
])
check("media", media)

# 其余页面
check("guide", GuidePage())
check("logs", LogPage())
check("devices", DevicePage())
cfg = ConfigManager(Path(tempfile.mkdtemp()))
settings_page = __import__("ui.pages.settings_page", fromlist=["SettingsPage"]).SettingsPage()
settings_page.load(cfg.settings)
check("settings", settings_page)
check("cast", CastSettingsPage())

print("text clipping smoke passed")
