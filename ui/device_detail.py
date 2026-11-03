from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout

from core.device_info import DeviceInfo
from ui.icons import icon


class DeviceDetailDialog(QDialog):
    """Compatibility dialog. The full detail experience is DetailPage."""

    def __init__(self, device: DeviceInfo, codecs, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("设备详情")
        self.resize(640, 560)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)
        title = QLabel(f"{device.manufacturer} {device.model}")
        title.setObjectName("PageTitle")
        subtitle = QLabel(f"{device.brand} · {device.serial}")
        subtitle.setObjectName("SerialLabel")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        text = QTextEdit()
        text.setObjectName("LogView")
        text.setReadOnly(True)
        hardware = [item for item in codecs if item.hardware]
        software = [item for item in codecs if not item.hardware]
        hardware_lines = "\n".join(f"  {item.codec} · {item.encoder}" for item in hardware) or "  暂无"
        software_lines = "\n".join(f"  {item.codec} · {item.encoder}" for item in software) or "  暂无"
        text.setPlainText(
            f"厂商：{device.manufacturer}\n品牌：{device.brand}\n型号：{device.model}\n"
            f"Android：{device.android_version} (SDK {device.sdk})\n序列号：{device.serial}\n"
            f"状态：{device.state}\n分辨率：{device.resolution}\n密度：{device.density}\n\n"
            f"硬件编码器：\n{hardware_lines}\n\n软件编码器：\n{software_lines}"
        )
        layout.addWidget(text, 1)
        actions = QHBoxLayout()
        actions.addStretch()
        close = QPushButton("关闭")
        close.setObjectName("PrimaryButton")
        close.setIcon(icon("check", "#FFFFFF", 14))
        close.setIconSize(QSize(14, 14))
        close.clicked.connect(self.accept)
        actions.addWidget(close)
        layout.addLayout(actions)
