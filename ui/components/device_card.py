from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.device_info import CONNECTION_USB, CONNECTION_WIFI, DeviceInfo
from ui.components.common import ElidedLabel, StatusPill, repolish
from ui.icons import icon
from ui.theme import COLORS


class DeviceCard(QFrame):
    start_requested = Signal(str)
    stop_requested = Signal(str)
    details_requested = Signal(str)
    settings_requested = Signal(str)
    serial_copied = Signal(str)
    disconnect_requested = Signal(str)
    transfer_requested = Signal(str)

    def __init__(self, device: DeviceInfo, parent=None) -> None:
        super().__init__(parent)
        self.device = device
        self._cast_state = "idle"
        self.setObjectName("DeviceCard")
        self.setMinimumWidth(480)
        self.setMinimumHeight(244)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(12)
        icon_badge = QFrame()
        icon_badge.setObjectName("IconBadge")
        icon_badge.setFixedSize(44, 44)
        icon_layout = QHBoxLayout(icon_badge)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        phone_icon = QLabel()
        phone_icon.setPixmap(icon("phone", COLORS["accent_hover"], 26).pixmap(26, 26))
        phone_icon.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(phone_icon)
        top.addWidget(icon_badge, 0, Qt.AlignTop)

        identity = QVBoxLayout()
        identity.setSpacing(4)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self.title_label = ElidedLabel(f"{device.manufacturer} {device.model}")
        self.title_label.setObjectName("CardTitle")
        title_row.addWidget(self.title_label, 1)
        self.status_label = StatusPill("已连接", "success")
        title_row.addWidget(self.status_label, 0, Qt.AlignTop)
        identity.addLayout(title_row)

        self.subtitle_label = QLabel(self._subtitle(device))
        self.subtitle_label.setObjectName("Muted")
        self.subtitle_label.setWordWrap(True)
        identity.addWidget(self.subtitle_label)
        self.serial_label = ElidedLabel(f"序列号：{device.serial}")
        self.serial_label.setObjectName("SerialLabel")
        self.serial_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        identity.addWidget(self.serial_label)
        top.addLayout(identity, 1)
        layout.addLayout(top)

        self.metrics_label = QLabel(self._metrics(device))
        self.metrics_label.setObjectName("InfoValue")
        self.metrics_label.setWordWrap(True)
        layout.addWidget(self.metrics_label)

        codec_title = QLabel("视频编码")
        codec_title.setObjectName("InfoLabel")
        layout.addWidget(codec_title)

        codec_row = QHBoxLayout()
        codec_row.setSpacing(8)
        self.codec_badge = StatusPill("检测中", "idle")
        codec_row.addWidget(self.codec_badge, 0, Qt.AlignVCenter)
        self.codec_label = QLabel("正在读取设备编码器…")
        self.codec_label.setObjectName("CodecName")
        self.codec_label.setWordWrap(True)
        codec_row.addWidget(self.codec_label, 1)
        layout.addLayout(codec_row)

        layout.addStretch(1)
        primary_actions = QHBoxLayout()
        primary_actions.setSpacing(8)
        secondary_actions = QHBoxLayout()
        secondary_actions.setSpacing(8)
        self.start_button = QPushButton("开始投屏")
        self.start_button.setObjectName("PrimaryButton")
        self.start_button.setIcon(icon("play", "#FFFFFF", 14))
        self.start_button.setIconSize(QSize(14, 14))
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.stop_button = QPushButton("停止")
        self.stop_button.setObjectName("GhostButton")
        self.stop_button.setIcon(icon("stop", COLORS["muted"], 13))
        self.stop_button.setIconSize(QSize(13, 13))
        self.stop_button.setCursor(Qt.PointingHandCursor)
        self.details_button = QPushButton("详情")
        self.details_button.setObjectName("GhostButton")
        self.details_button.setIcon(icon("info", COLORS["muted"], 14))
        self.details_button.setIconSize(QSize(14, 14))
        self.details_button.setCursor(Qt.PointingHandCursor)
        self.settings_button = QPushButton("设置")
        self.settings_button.setObjectName("GhostButton")
        self.settings_button.setIcon(icon("settings", COLORS["muted"], 14))
        self.settings_button.setIconSize(QSize(14, 14))
        self.settings_button.setCursor(Qt.PointingHandCursor)
        self.copy_button = QPushButton()
        self.copy_button.setObjectName("IconButton")
        self.copy_button.setIcon(icon("copy", COLORS["muted"], 16))
        self.copy_button.setIconSize(QSize(16, 16))
        self.copy_button.setToolTip("复制 ADB 序列号")
        self.copy_button.setCursor(Qt.PointingHandCursor)
        self.start_button.clicked.connect(lambda: self.start_requested.emit(self.device.serial))
        self.stop_button.clicked.connect(lambda: self.stop_requested.emit(self.device.serial))
        self.details_button.clicked.connect(lambda: self.details_requested.emit(self.device.serial))
        self.settings_button.clicked.connect(lambda: self.settings_requested.emit(self.device.serial))
        self.copy_button.clicked.connect(lambda: self.serial_copied.emit(self.device.serial))
        self.transfer_button = QPushButton("文件互传")
        self.transfer_button.setObjectName("GhostButton")
        self.transfer_button.setIcon(icon("export", COLORS["muted"], 13))
        self.transfer_button.setIconSize(QSize(13, 13))
        self.transfer_button.setCursor(Qt.PointingHandCursor)
        self.transfer_button.clicked.connect(lambda: self.transfer_requested.emit(self.device.serial))
        self.disconnect_button = QPushButton('断开')
        self.disconnect_button.setObjectName('GhostButton')
        self.disconnect_button.setIcon(icon('close', COLORS['muted'], 13))
        self.disconnect_button.setIconSize(QSize(13, 13))
        self.disconnect_button.setToolTip('断开 ADB 网络连接')
        self.disconnect_button.setCursor(Qt.PointingHandCursor)
        self.disconnect_button.clicked.connect(lambda: self.disconnect_requested.emit(self.device.serial))
        primary_actions.addWidget(self.start_button, 1)
        primary_actions.addWidget(self.stop_button)
        layout.addLayout(primary_actions)

        secondary_actions.addWidget(self.details_button, 1)
        secondary_actions.addWidget(self.transfer_button, 1)
        secondary_actions.addWidget(self.settings_button, 1)
        secondary_actions.addWidget(self.copy_button)
        secondary_actions.addWidget(self.disconnect_button)
        layout.addLayout(secondary_actions)

        self.details_label = QLabel("", self)
        self.details_label.hide()
        self._refresh_presentation()

    @staticmethod
    def _connection_mode(device: DeviceInfo) -> str:
        if device.connection_type == CONNECTION_WIFI:
            return "Wi-Fi"
        if device.connection_type == CONNECTION_USB:
            return "USB"
        if device.connection_type == "emulator":
            return "模拟器"
        return "未知"

    @classmethod
    def _subtitle(cls, device: DeviceInfo) -> str:
        mode = cls._connection_mode(device)
        suffix = f"{device.serial}" if device.connection_type == CONNECTION_WIFI else ""
        text = f"{device.manufacturer} · Android {device.android_version} (SDK {device.sdk}) · {mode} 连接"
        return f"{text}\n{suffix}" if suffix else text

    @staticmethod
    def _metrics(device: DeviceInfo) -> str:
        return f"{device.resolution} · {device.density} DPI"

    def update_device(self, device: DeviceInfo) -> None:
        self.device = device
        self.title_label.setText(f"{device.manufacturer} {device.model}")
        self.subtitle_label.setText(self._subtitle(device))
        self.serial_label.setText(f"序列号：{device.serial}")
        self.metrics_label.setText(self._metrics(device))
        self.details_label.setText(
            f"Android {device.android_version}\n序列号：{device.serial}\n分辨率：{device.resolution}\n密度：{device.density}"
        )
        self._refresh_presentation()

    def set_device(self, device: DeviceInfo) -> None:
        self.update_device(device)

    def set_codecs(self, codecs) -> None:
        if not codecs:
            self.codec_label.setText("暂未检测到可用编码器")
            self.codec_badge.setText("未检测")
            self.codec_badge.set_tone("warning")
            return
        best = codecs[0]
        kind = "硬件编码" if best.hardware else "软件编码"
        self.codec_label.setText(f"{best.encoder} · {kind} · 共 {len(codecs)} 个可用编码器")
        self.codec_badge.setText(best.codec)
        self.codec_badge.set_tone("success" if best.hardware else "idle")

    def set_codecs_pending(self) -> None:
        self.codec_label.setText("正在读取设备编码器…")
        self.codec_badge.setText("检测中")
        self.codec_badge.set_tone("idle")

    def set_casting_state(self, state: str) -> None:
        self._cast_state = state
        self._refresh_presentation()

    def set_casting(self, casting: bool) -> None:
        self.set_casting_state("running" if casting else "idle")

    def _refresh_presentation(self) -> None:
        state = self._cast_state
        if state == "starting":
            self.status_label.setText("启动中")
            self.status_label.set_tone("info")
        elif state == "stopping":
            self.status_label.setText("停止中")
            self.status_label.set_tone("warning")
        elif state == "running":
            self.status_label.setText("投屏中")
            self.status_label.set_tone("success")
        elif state == "error":
            self.status_label.setText("启动失败")
            self.status_label.set_tone("error")
        elif state == "detecting":
            self.status_label.setText("检测中")
            self.status_label.set_tone("info")
        elif self.device.state == "device":
            self.status_label.setText("已连接")
            self.status_label.set_tone("success")
        elif self.device.state == "unauthorized":
            self.status_label.setText("未授权")
            self.status_label.set_tone("warning")
        else:
            self.status_label.setText("离线")
            self.status_label.set_tone("error")

        online = self.device.state == "device"
        if state == "starting":
            self.start_button.setText("启动中…")
        elif state == "detecting":
            self.start_button.setText("检测编码器…")
        elif state == "error":
            self.start_button.setText("重新开始")
        else:
            self.start_button.setText("开始投屏")
        self.start_button.setEnabled(online and state in {"idle", "error"})
        self.stop_button.setEnabled(state in {"starting", "running"})
        self.setProperty("casting", state in {"starting", "running"})
        self.disconnect_button.setVisible(self.device.connection_type == CONNECTION_WIFI)
        self.disconnect_button.setEnabled(state not in {"starting", "stopping"})
        repolish(self)

