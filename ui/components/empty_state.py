from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.components.common import StatusDot
from ui.icons import icon
from ui.theme import COLORS


class EmptyState(QWidget):
    scan_requested = Signal()
    help_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 16, 24, 24)
        outer.addStretch(1)
        panel = QWidget()
        panel.setMaximumWidth(530)
        layout = QVBoxLayout(panel)
        layout.setSpacing(13)
        layout.setAlignment(Qt.AlignHCenter)
        illustration = QFrame()
        illustration.setObjectName("EmptyIllustration")
        illustration.setFixedSize(154, 108)
        illustration_layout = QHBoxLayout(illustration)
        illustration_layout.setContentsMargins(0, 0, 0, 0)
        illustration_layout.setSpacing(-6)
        phone_icon = QLabel()
        phone_icon.setPixmap(icon("phone", COLORS["accent"], 58).pixmap(58, 58))
        phone_icon.setAlignment(Qt.AlignCenter)
        usb_icon = QLabel()
        usb_icon.setPixmap(icon("usb", COLORS["faint"], 34).pixmap(34, 34))
        usb_icon.setAlignment(Qt.AlignCenter)
        illustration_layout.addStretch()
        illustration_layout.addWidget(phone_icon)
        illustration_layout.addWidget(usb_icon)
        illustration_layout.addStretch()
        layout.addWidget(illustration, 0, Qt.AlignHCenter)
        title = QLabel("暂未发现 Android 设备")
        title.setObjectName("EmptyTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        description = QLabel("请使用 USB 数据线连接手机，并开启 USB 调试")
        description.setObjectName("EmptyDescription")
        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)
        layout.addWidget(description)
        scan_button = QPushButton("立即扫描")
        scan_button.setObjectName("PrimaryButton")
        scan_button.setIcon(icon("refresh", "#FFFFFF", 16))
        scan_button.setIconSize(QSize(16, 16))
        scan_button.setCursor(Qt.PointingHandCursor)
        scan_button.setMinimumWidth(148)
        scan_button.clicked.connect(self.scan_requested)
        layout.addWidget(scan_button, 0, Qt.AlignHCenter)
        help_button = QPushButton("设备无法识别？查看常见问题")
        help_button.setObjectName("LinkButton")
        help_button.setCursor(Qt.PointingHandCursor)
        help_button.clicked.connect(self.help_requested)
        layout.addWidget(help_button, 0, Qt.AlignHCenter)
        status_row = QHBoxLayout()
        status_row.setSpacing(7)
        status_row.addStretch()
        self.adb_dot = StatusDot(COLORS["faint"], 7)
        self.adb_label = QLabel("ADB 连接中")
        self.adb_label.setObjectName("Caption")
        status_row.addWidget(self.adb_dot)
        status_row.addWidget(self.adb_label)
        status_row.addStretch()
        layout.addLayout(status_row)
        outer.addWidget(panel, 0, Qt.AlignHCenter)
        outer.addStretch(2)

    def set_adb_status(self, ok: bool, text: str) -> None:
        self.adb_dot.set_color(COLORS["success"] if ok else COLORS["error"])
        self.adb_label.setText(text)
