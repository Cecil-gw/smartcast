from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.components.common import repolish
from ui.icons import icon
from ui.theme import COLORS
from utils.system_utils import resource_path


class Sidebar(QWidget):
    navigation_requested = Signal(str)

    NAV_ITEMS = (
        ("home", "首页", "bolt"),
        ("devices", "设备管理", "phone"),
        ("sessions", "投屏中心", "monitor"),
        ("cast", "投屏设置", "screen"),
        ("guide", "使用指南", "help"),
        ("media", "媒体管理", "folder"),
        ("logs", "日志", "list"),
        ("settings", "设置", "settings"),
    )

    def __init__(self, status_bar: QWidget, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(200)
        layout = QVBoxLayout(self)
        # Top padding equals the custom title-bar height (40px) so the
        # navigation starts level with the content on the right.
        layout.setContentsMargins(14, 56, 14, 12)
        layout.setSpacing(6)

        layout.addWidget(self._build_brand())

        self.buttons: dict[str, QPushButton] = {}
        for key, text, icon_name in self.NAV_ITEMS:
            button = QPushButton(text)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setIcon(icon(icon_name, COLORS["muted"], 17))
            button.setIconSize(QSize(17, 17))
            button.clicked.connect(lambda checked=False, nav_key=key: self._activate(nav_key))
            layout.addWidget(button)
            self.buttons[key] = button

        layout.addStretch(1)
        layout.addWidget(status_bar)
        self.set_active("home")

    def _build_brand(self) -> QWidget:
        brand = QFrame()
        brand.setObjectName("SidebarBrand")
        row = QHBoxLayout(brand)
        row.setContentsMargins(6, 4, 6, 12)
        row.setSpacing(9)

        logo = QLabel()
        icon_file = resource_path("resources/assets/app-icon.png")
        from PySide6.QtGui import QPixmap

        pixmap = QPixmap(str(icon_file))
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setFixedSize(30, 30)
        row.addWidget(logo, 0, Qt.AlignVCenter)

        text = QVBoxLayout()
        text.setSpacing(0)
        name = QLabel("SmartCast")
        name.setObjectName("SidebarName")
        version = QLabel("v1.0")
        version.setObjectName("SidebarVersion")
        text.addWidget(name)
        text.addWidget(version)
        row.addLayout(text, 1)
        return brand

    def _activate(self, key: str) -> None:
        self.set_active(key)
        self.navigation_requested.emit(key)

    def set_active(self, key: str) -> None:
        for nav_key, button in self.buttons.items():
            active = nav_key == key
            button.setChecked(active)
            button.setProperty("active", active)
            self._refresh_button_icon(nav_key, button, active)
            repolish(button)

    def _refresh_button_icon(self, nav_key: str, button: QPushButton, active: bool) -> None:
        color = "#3F6555" if active else COLORS["muted"]
        icon_name = dict((k, i) for k, _, i in self.NAV_ITEMS)[nav_key]
        button.setIcon(icon(icon_name, color, 17))
