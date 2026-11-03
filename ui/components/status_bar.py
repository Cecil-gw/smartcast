from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from ui.components.common import ElidedLabel, StatusDot, repolish
from ui.theme import COLORS


class StatusBar(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("StatusBar")
        self.setMinimumHeight(86)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 11, 4, 7)
        layout.setSpacing(4)

        adb_row = QHBoxLayout()
        adb_row.setSpacing(7)
        self.adb_dot = StatusDot(COLORS["faint"], 8)
        self.adb_label = QLabel("ADB 未连接")
        self.adb_label.setObjectName("Muted")
        self.adb_label.setWordWrap(True)
        adb_row.addWidget(self.adb_dot)
        adb_row.addWidget(self.adb_label, 1)
        layout.addLayout(adb_row)

        self.scan_label = QLabel("正在初始化扫描")
        self.scan_label.setObjectName("Caption")
        self.scan_label.setContentsMargins(15, 0, 0, 0)
        self.scan_label.setWordWrap(True)
        layout.addWidget(self.scan_label)

        self.message_label = ElidedLabel("就绪")
        self.message_label.setObjectName("StatusMessage")
        self.message_label.setContentsMargins(15, 0, 0, 0)
        layout.addWidget(self.message_label)
        self.cast_label = QLabel("投屏 0")
        self.cast_label.hide()

    def set_adb(self, ok: bool, text: str) -> None:
        self.adb_dot.set_color(COLORS["success"] if ok else COLORS["error"])
        self.adb_label.setText(text)

    def set_scan(self, text: str) -> None:
        self.scan_label.setText(text)

    def set_casting_count(self, count: int) -> None:
        self.cast_label.setText(f"投屏 {count}")

    def set_message(self, text: str, tone: str = "muted") -> None:
        self.message_label.setProperty("tone", tone)
        repolish(self.message_label)
        self.message_label.setText(text)



