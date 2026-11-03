from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.icons import icon
from ui.theme import COLORS


class FaqDialog(QDialog):
    rescan_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("连接常见问题")
        self.resize(580, 600)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(14)
        title = QLabel("无法发现设备？")
        title.setObjectName("PageTitle")
        subtitle = QLabel("按下面顺序检查，通常可以在 1 分钟内解决。")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        steps = [
            ("01", "使用支持数据传输的 USB 线", "部分充电线没有数据针脚。换一根原装或确认支持传输的线。"),
            ("02", "开启开发者选项与 USB 调试", "设置 → 关于手机 → 连续点击版本号；然后在开发者选项中开启 USB 调试。"),
            ("03", "允许这台电脑调试", "手机弹出“允许 USB 调试吗？”时勾选始终允许并确认。若已拒绝，可撤销 USB 调试授权后重连。"),
            ("04", "切换 USB 连接模式", "将 USB 用途从“仅充电”切换到“文件传输（MTP）”，等待设备重新出现。"),
            ("05", "仍未识别时重新扫描", "SmartCast 会使用内置 ADB。点击下方“重新扫描”触发一次手动检测。"),
        ]
        for number, heading, description in steps:
            layout.addWidget(self._step(number, heading, description))
        layout.addStretch(1)
        actions = QHBoxLayout()
        actions.addStretch()
        close = QPushButton("关闭")
        close.clicked.connect(self.reject)
        rescan = QPushButton("重新扫描")
        rescan.setObjectName("PrimaryButton")
        rescan.setIcon(icon("refresh", "#FFFFFF", 14))
        rescan.setIconSize(QSize(14, 14))
        rescan.clicked.connect(self._rescan)
        actions.addWidget(close)
        actions.addWidget(rescan)
        layout.addLayout(actions)

    def _step(self, number: str, heading: str, description: str) -> QWidget:
        row = QFrame()
        row.setObjectName("Card")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(13, 11, 13, 11)
        layout.setSpacing(11)
        badge = QLabel(number)
        badge.setFixedSize(28, 28)
        badge.setAlignment(Qt.AlignCenter)
        badge.setObjectName("StepBadge")
        text_column = QVBoxLayout()
        text_column.setSpacing(2)
        title = QLabel(heading)
        title.setObjectName("InfoValue")
        description_label = QLabel(description)
        description_label.setObjectName("Caption")
        description_label.setWordWrap(True)
        text_column.addWidget(title)
        text_column.addWidget(description_label)
        layout.addWidget(badge, 0, Qt.AlignTop)
        layout.addLayout(text_column, 1)
        return row

    def _rescan(self) -> None:
        self.rescan_requested.emit()
        self.accept()

