from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from ui.components.common import StatusDot
from ui.icons import icon
from ui.theme import COLORS


class HeaderBar(QFrame):
    settings_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("HeaderBar")
        self.setFixedHeight(56)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(10)

        self.context_label = QLabel("设备管理")
        self.context_label.setObjectName("Caption")
        layout.addWidget(self.context_label)
        layout.addStretch()

        status_chip = QFrame()
        status_chip.setObjectName("HeaderStatusChip")
        status_layout = QHBoxLayout(status_chip)
        status_layout.setContentsMargins(8, 3, 8, 3)
        status_layout.setSpacing(6)
        self.adb_dot = StatusDot(COLORS["faint"], 7)
        self.adb_label = QLabel("ADB 连接中")
        self.adb_label.setObjectName("Muted")
        status_layout.addWidget(self.adb_dot)
        status_layout.addWidget(self.adb_label)
        divider = QFrame()
        divider.setObjectName("VerticalDivider")
        divider.setFixedSize(1, 12)
        self.divider = divider
        status_layout.addWidget(divider)
        device_icon = QLabel()
        device_icon.setPixmap(icon("phone", COLORS["muted"], 14).pixmap(14, 14))
        self.device_icon = device_icon
        status_layout.addWidget(device_icon)
        self.device_label = QLabel("0 台设备")
        self.device_label.setObjectName("InfoValue")
        status_layout.addWidget(self.device_label)
        layout.addWidget(status_chip)

        self.settings_button = QPushButton()
        self.settings_button.setObjectName("TopIconButton")
        self.settings_button.setIcon(icon("settings", COLORS["muted"], 16))
        self.settings_button.setIconSize(QSize(16, 16))
        self.settings_button.setToolTip("打开设置")
        self.settings_button.setCursor(Qt.PointingHandCursor)
        self.settings_button.clicked.connect(self.settings_requested)
        layout.addWidget(self.settings_button)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        width = self.width()
        self.context_label.setVisible(width >= 720)
        compact = width < 600
        self.adb_label.setVisible(not compact)
        self.device_label.setVisible(not compact)
        self.device_icon.setVisible(not compact)
        self.divider.setVisible(not compact)

    def set_adb_status(self, ok: bool, text: str) -> None:
        self.adb_dot.set_color(COLORS["success"] if ok else COLORS["error"])
        self.adb_label.setText(text)

    def set_device_count(self, count: int) -> None:
        self.device_label.setText(f"{count} 台设备")

    def set_context(self, text: str) -> None:
        self.context_label.setText(text)


