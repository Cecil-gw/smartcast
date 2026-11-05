from __future__ import annotations

import math

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.device_info import DeviceInfo
from ui.components.common import ElidedLabel, InfoTile, MetaChip, StatusPill
from ui.icons import icon
from ui.theme import COLORS


class DetailPage(QWidget):
    back_requested = Signal()
    start_requested = Signal(str)
    stop_requested = Signal(str)
    settings_requested = Signal(str)
    copy_requested = Signal(str)
    redetect_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.device: DeviceInfo | None = None
        self._cast_state = "idle"
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(11)
        back = QPushButton("返回设备")
        back.setObjectName("GhostButton")
        back.setIcon(icon("back", COLORS["muted"], 15))
        back.setIconSize(QSize(15, 15))
        back.setCursor(Qt.PointingHandCursor)
        back.clicked.connect(self.back_requested)
        header.addWidget(back)
        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        title = QLabel("设备详情")
        title.setObjectName("PageTitle")
        self.header_subtitle = QLabel("设备信息与编码器能力")
        self.header_subtitle.setObjectName("PageSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(self.header_subtitle)
        header.addLayout(title_column, 1)
        self.redetect_button = QPushButton("重新检测编码器")
        self.redetect_button.setIcon(icon("refresh", COLORS["muted"], 14))
        self.redetect_button.setIconSize(QSize(14, 14))
        self.redetect_button.setCursor(Qt.PointingHandCursor)
        self.redetect_button.clicked.connect(lambda: self.device and self.redetect_requested.emit(self.device.serial))
        header.addWidget(self.redetect_button)
        root.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        host = QWidget()
        center = QHBoxLayout(host)
        center.setContentsMargins(0, 0, 4, 0)
        center.addStretch(1)
        content = QWidget()
        content.setMaximumWidth(980)
        content.setMinimumWidth(680)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(14)
        layout.addWidget(self._build_hero())
        layout.addWidget(self._build_info())
        layout.addWidget(self._build_codecs())
        layout.addStretch(1)
        center.addWidget(content, 1)
        center.addStretch(1)
        scroll.setWidget(host)
        root.addWidget(scroll, 1)

    def _build_hero(self) -> QWidget:
        hero = QFrame()
        hero.setObjectName("HeroCard")
        layout = QVBoxLayout(hero)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        head_row = QHBoxLayout()
        head_row.setSpacing(14)
        icon_tile = QFrame()
        icon_tile.setObjectName("IconBadge")
        icon_tile.setFixedSize(58, 58)
        icon_layout = QHBoxLayout(icon_tile)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        phone = QLabel()
        phone.setPixmap(icon("phone", COLORS["accent"], 30).pixmap(30, 30))
        phone.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(phone)
        head_row.addWidget(icon_tile)
        title_column = QVBoxLayout()
        title_column.setSpacing(3)
        title_row = QHBoxLayout()
        title_row.setSpacing(9)
        self.hero_title = QLabel("设备")
        self.hero_title.setObjectName("HeroTitle")
        self.status_pill = StatusPill("已连接", "success")
        title_row.addWidget(self.hero_title)
        title_row.addWidget(self.status_pill)
        title_row.addStretch()
        self.hero_subtitle = QLabel("")
        self.hero_subtitle.setObjectName("SerialLabel")
        self.hero_subtitle.setTextInteractionFlags(Qt.TextSelectableByMouse)
        title_column.addLayout(title_row)
        self.hero_subtitle.setWordWrap(True)
        title_column.addWidget(self.hero_subtitle)
        head_row.addLayout(title_column, 1)
        layout.addLayout(head_row)
        self.start_button = QPushButton("开始投屏")
        self.start_button.setObjectName("PrimaryButton")
        self.start_button.setIcon(icon("play", "#FFFFFF", 15))
        self.start_button.setIconSize(QSize(15, 15))
        self.start_button.clicked.connect(lambda: self.device and self.start_requested.emit(self.device.serial))
        self.stop_button = QPushButton("停止投屏")
        self.stop_button.setObjectName("DangerButton")
        self.stop_button.setIcon(icon("stop", COLORS["error"], 13))
        self.stop_button.setIconSize(QSize(13, 13))
        self.stop_button.clicked.connect(lambda: self.device and self.stop_requested.emit(self.device.serial))
        settings_button = QPushButton("投屏设置")
        settings_button.setIcon(icon("settings", COLORS["muted"], 15))
        settings_button.setIconSize(QSize(15, 15))
        settings_button.clicked.connect(lambda: self.device and self.settings_requested.emit(self.device.serial))
        copy_button = QPushButton("复制序列号")
        copy_button.setObjectName("GhostButton")
        copy_button.setIcon(icon("copy", COLORS["muted"], 15))
        copy_button.setIconSize(QSize(15, 15))
        copy_button.clicked.connect(lambda: self.device and self.copy_requested.emit(self.device.serial))
        button_grid = QGridLayout()
        button_grid.setHorizontalSpacing(8)
        button_grid.setVerticalSpacing(8)
        for index, button in enumerate((self.start_button, self.stop_button, settings_button, copy_button)):
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(30)
            button_grid.addWidget(button, index // 2, index % 2)
        button_grid.setColumnStretch(0, 1)
        button_grid.setColumnStretch(1, 1)
        layout.addLayout(button_grid)
        return hero

    def _build_info(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        title = QLabel("设备信息")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)
        grid = QGridLayout()
        grid.setHorizontalSpacing(9)
        grid.setVerticalSpacing(9)
        self.manufacturer_tile = InfoTile("厂商", "—")
        self.brand_tile = InfoTile("品牌", "—")
        self.android_tile = InfoTile("Android 版本", "—")
        self.sdk_tile = InfoTile("SDK 版本", "—")
        self.resolution_tile = InfoTile("屏幕分辨率", "—")
        self.screen_size_tile = InfoTile("屏幕尺寸（估算）", "—")
        self.density_tile = InfoTile("屏幕密度", "—")
        self.connection_tile = InfoTile("连接方式", "—")
        self.serial_tile = InfoTile("ADB 序列号", "—")
        tiles = [
            self.manufacturer_tile, self.brand_tile, self.android_tile,
            self.sdk_tile, self.resolution_tile, self.screen_size_tile,
            self.density_tile, self.connection_tile, self.serial_tile,
        ]
        for index, tile in enumerate(tiles):
            grid.addWidget(tile, index // 3, index % 3)
        layout.addLayout(grid)
        return card

    def _build_codecs(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(11)
        header = QHBoxLayout()
        title = QLabel("编码器能力")
        title.setObjectName("SectionTitle")
        self.codec_summary = QLabel("正在检测…")
        self.codec_summary.setObjectName("Caption")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.codec_summary)
        layout.addLayout(header)
        groups = QHBoxLayout()
        groups.setSpacing(12)
        self.hardware_group, self.hardware_layout = self._codec_group("硬件编码器", COLORS["success"])
        self.software_group, self.software_layout = self._codec_group("软件编码器", COLORS["muted"])
        groups.addWidget(self.hardware_group, 1)
        groups.addWidget(self.software_group, 1)
        layout.addLayout(groups)
        return card

    def _codec_group(self, title: str, color: str) -> tuple[QWidget, QVBoxLayout]:
        frame = QWidget()
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)
        heading = QLabel(title)
        heading.setObjectName("CodecGroupHeading")
        heading.setProperty("tone", "success" if color == COLORS["success"] else "muted")
        layout.addWidget(heading)
        return frame, layout

    def set_device(self, device: DeviceInfo, codecs, cast_state: str = "idle") -> None:
        self.device = device
        self._cast_state = cast_state
        self.hero_title.setText(f"{device.manufacturer} {device.model}")
        self.header_subtitle.setText(f"{device.brand} · {device.serial}")
        self.hero_subtitle.setText(f"{self._connection_mode(device.serial)} · {device.serial}")
        self.manufacturer_tile.set_value(device.manufacturer)
        self.brand_tile.set_value(device.brand)
        self.android_tile.set_value(device.android_version)
        self.sdk_tile.set_value(device.sdk)
        self.resolution_tile.set_value(device.resolution)
        self.screen_size_tile.set_value(self._screen_size(device.resolution, device.density))
        self.density_tile.set_value(f"{device.density} dpi")
        self.connection_tile.set_value(self._connection_mode(device.serial))
        self.serial_tile.set_value(device.serial)
        self.set_codecs(codecs)
        self.set_casting_state(cast_state)

    def set_codecs(self, codecs) -> None:
        self._clear_layout(self.hardware_layout)
        self._clear_layout(self.software_layout)
        hardware = [item for item in codecs if item.hardware]
        software = [item for item in codecs if not item.hardware]
        for group_layout, items in ((self.hardware_layout, hardware), (self.software_layout, software)):
            heading = QLabel("硬件编码器" if group_layout is self.hardware_layout else "软件编码器")
            heading.setObjectName("CodecGroupHeading")
            heading.setProperty("tone", "success" if group_layout is self.hardware_layout else "muted")
            group_layout.addWidget(heading)
            if not items:
                empty = QLabel("暂无")
                empty.setObjectName("Caption")
                group_layout.addWidget(empty)
                group_layout.addStretch(1)
                continue
            for item in items:
                group_layout.addWidget(self._codec_row(item))
            group_layout.addStretch(1)
        self.codec_summary.setText(f"硬件 {len(hardware)} · 软件 {len(software)}" if codecs else "尚未检测到编码器")

    def set_codecs_pending(self) -> None:
        self._clear_layout(self.hardware_layout)
        self._clear_layout(self.software_layout)
        for layout, title in ((self.hardware_layout, "硬件编码器"), (self.software_layout, "软件编码器")):
            heading = QLabel(title)
            heading.setObjectName("CodecGroupHeading")
            heading.setProperty("tone", "muted")
            layout.addWidget(heading)
            pending = QLabel("正在检测…")
            pending.setObjectName("Caption")
            layout.addWidget(pending)
            layout.addStretch(1)
        self.codec_summary.setText("正在检测编码器…")

    def _codec_row(self, item) -> QWidget:
        row = QFrame()
        row.setObjectName("CodecPanel")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(9, 6, 9, 6)
        layout.setSpacing(8)
        badge = MetaChip(item.codec, "success" if item.hardware else "idle")
        name = ElidedLabel(item.encoder)
        name.setObjectName("MonoLabel")
        layout.addWidget(badge)
        layout.addWidget(name, 1)
        return row

    def set_casting_state(self, state: str) -> None:
        self._cast_state = state
        device_state = self.device.state if self.device else "offline"
        if state == "starting":
            self.status_pill.setText("启动中")
            self.status_pill.set_tone("info")
        elif state == "stopping":
            self.status_pill.setText("停止中")
            self.status_pill.set_tone("warning")
        elif state == "running":
            self.status_pill.setText("投屏中")
            self.status_pill.set_tone("success")
        elif state == "error":
            self.status_pill.setText("启动失败")
            self.status_pill.set_tone("error")
        elif device_state == "device":
            self.status_pill.setText("已连接")
            self.status_pill.set_tone("success")
        elif device_state == "unauthorized":
            self.status_pill.setText("未授权")
            self.status_pill.set_tone("warning")
        else:
            self.status_pill.setText("离线")
            self.status_pill.set_tone("error")
        online = device_state == "device"
        self.start_button.setEnabled(online and state in {"idle", "error"})
        self.stop_button.setEnabled(state in {"starting", "running"})
        self.redetect_button.setEnabled(online and state not in {"starting", "stopping"})

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    @staticmethod
    def _connection_mode(serial: str) -> str:
        return "Wi-Fi" if ":" in serial else "USB"

    @staticmethod
    def _screen_size(resolution: str, density: str) -> str:
        try:
            width, height = (int(part) for part in resolution.lower().split("x"))
            dpi = float(density)
            if dpi > 0:
                return f"约 {math.hypot(width, height) / dpi:.1f} 英寸"
        except (ValueError, TypeError):
            pass
        return "—"




