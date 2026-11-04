from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.device_info import DeviceInfo
from ui.components.common import StatusPill
from ui.components.control_panel import ControlPanelCard, ScreenControlCard
from ui.icons import icon
from ui.theme import COLORS


class ActionCard(QFrame):
    clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class OverviewPage(QWidget):
    control_requested = Signal(str, str)
    screen_op_requested = Signal(str, str, object)
    screen_off_cast_requested = Signal(str)
    fullscreen_requested = Signal(str)
    screenshot_requested = Signal(str)
    record_requested = Signal(str)
    scan_requested = Signal()
    help_requested = Signal()
    manage_requested = Signal()
    cast_requested = Signal()
    settings_requested = Signal()
    start_requested = Signal(str)
    stop_requested = Signal(str)
    details_requested = Signal(str)
    settings_for_device_requested = Signal(str)
    serial_copied = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.primary_serial: str | None = None
        self._device: DeviceInfo | None = None
        self._codecs: list = []
        self._cast_state = "idle"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("OverviewScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        content = QWidget()
        content.setObjectName("OverviewContent")
        scroll.setWidget(content)

        # 右侧留白给人物立绘；内容集中在左侧
        root = QVBoxLayout(content)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        title_column = QVBoxLayout()
        title_column.setSpacing(3)
        title = QLabel("首页")
        title.setObjectName("PageTitle")
        subtitle = QLabel("快速了解设备与投屏状态，进入常用工作台")
        subtitle.setObjectName("PageSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        root.addLayout(title_column)

        device_title = QLabel("设备概览")
        device_title.setObjectName("SectionTitle")
        root.addWidget(device_title)
        root.addWidget(self._build_device_card())

        control_title = QLabel("手机控制")
        control_title.setObjectName("SectionTitle")
        root.addWidget(control_title)

        self.control_panel = ControlPanelCard()
        self.control_panel.control_requested.connect(self.control_requested.emit)
        root.addWidget(self.control_panel)

        screen_title = QLabel("屏幕控制")
        screen_title.setObjectName("SectionTitle")
        root.addWidget(screen_title)

        self.screen_card = ScreenControlCard()
        self.screen_card.screen_op_requested.connect(self.screen_op_requested.emit)
        self.screen_card.control_requested.connect(self.control_requested_emit_bridge)
        self.screen_card.screen_off_cast_requested.connect(self.screen_off_cast_requested.emit)
        self.screen_card.fullscreen_requested.connect(self.fullscreen_requested.emit)
        self.screen_card.screenshot_requested.connect(self.screenshot_requested.emit)
        self.screen_card.record_requested.connect(self.record_requested.emit)
        root.addWidget(self.screen_card)

        stats_title = QLabel("运行概况")
        stats_title.setObjectName("SectionTitle")
        root.addWidget(stats_title)

        summary = QGridLayout()
        summary.setHorizontalSpacing(12)
        summary.setVerticalSpacing(12)
        self.adb_tile = self._metric_tile("usb", "ADB 服务", "检测中", "工具连接状态")
        self.device_tile = self._metric_tile("phone", "在线设备", "0 / 0 台", "已授权设备数量")
        self.casting_tile = self._metric_tile("monitor", "投屏中", "0 路", "正在运行的会话")
        self.scan_tile = self._metric_tile("refresh", "最近扫描", "等待扫描", "自动 / 手动扫描结果")
        summary.addWidget(self.adb_tile[0], 0, 0)
        summary.addWidget(self.device_tile[0], 0, 1)
        summary.addWidget(self.casting_tile[0], 1, 0)
        summary.addWidget(self.scan_tile[0], 1, 1)
        summary.setColumnStretch(0, 1)
        summary.setColumnStretch(1, 1)
        summary.setRowStretch(0, 1)
        summary.setRowStretch(1, 1)
        root.addLayout(summary)

        actions_title = QLabel("常用操作")
        actions_title.setObjectName("SectionTitle")
        root.addWidget(actions_title)

        action_grid = QGridLayout()
        action_grid.setHorizontalSpacing(12)
        action_grid.setVerticalSpacing(12)
        scan_card = self._action_card("立即扫描设备", "使用内置 ADB 检测已连接手机", "refresh")
        scan_card.clicked.connect(self.scan_requested)
        manage_card = self._action_card("进入设备管理", "查看设备信息与编码器能力", "phone")
        manage_card.clicked.connect(self.manage_requested)
        cast_card = self._action_card("调整投屏配置", "设置编码、分辨率与音频", "monitor")
        cast_card.clicked.connect(self.cast_requested)
        help_card = self._action_card("设备连接帮助", "检查 USB 调试与授权问题", "help")
        help_card.clicked.connect(self.help_requested)
        action_grid.addWidget(scan_card, 0, 0)
        action_grid.addWidget(manage_card, 0, 1)
        action_grid.addWidget(cast_card, 1, 0)
        action_grid.addWidget(help_card, 1, 1)
        action_grid.setColumnStretch(0, 1)
        action_grid.setColumnStretch(1, 1)
        action_grid.setRowStretch(0, 1)
        action_grid.setRowStretch(1, 1)
        root.addLayout(action_grid)

        root.addStretch(1)

    def _metric_tile(self, icon_name: str, title: str, value: str, hint: str) -> tuple[QFrame, QLabel, QLabel]:
        card = QFrame()
        card.setObjectName("StatCard")
        card.setMinimumHeight(82)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        badge = QFrame()
        badge.setObjectName("IconBadge")
        badge.setFixedSize(34, 34)
        badge_layout = QHBoxLayout(badge)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel()
        icon_label.setPixmap(icon(icon_name, COLORS["accent_hover"], 18).pixmap(18, 18))
        icon_label.setAlignment(Qt.AlignCenter)
        badge_layout.addWidget(icon_label)
        layout.addWidget(badge, 0, Qt.AlignVCenter)

        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(1)
        value_label = QLabel(value)
        value_label.setObjectName("MetricValue")
        title_label = QLabel(title)
        title_label.setObjectName("InfoLabel")
        hint_label = QLabel(hint)
        hint_label.setObjectName("Caption")
        hint_label.setWordWrap(True)
        text.addWidget(value_label)
        text.addWidget(title_label)
        text.addWidget(hint_label)
        text.addStretch(1)
        layout.addLayout(text, 1)
        return card, value_label, hint_label

    def _action_card(self, title: str, hint: str, icon_name: str) -> QFrame:
        card = ActionCard()
        card.setObjectName("ActionCard")
        card.setMinimumHeight(78)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        glyph = QLabel()
        glyph.setPixmap(icon(icon_name, COLORS["accent_hover"], 22).pixmap(22, 22))
        glyph.setAlignment(Qt.AlignCenter)
        glyph.setFixedSize(34, 34)
        layout.addWidget(glyph, 0, Qt.AlignVCenter)

        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("ActionTitle")
        hint_label = QLabel(hint)
        hint_label.setObjectName("Caption")
        hint_label.setWordWrap(True)
        text.addWidget(title_label)
        text.addWidget(hint_label)
        layout.addLayout(text, 1)

        arrow = QLabel("›")
        arrow.setObjectName("Muted")
        layout.addWidget(arrow, 0, Qt.AlignVCenter)
        return card

    def control_requested_emit_bridge(self, serial: str, action: str) -> None:
        # wake-up reuses the control pipeline
        self.screen_op_requested.emit(serial, "__control__", action)

    def _build_device_card(self) -> QWidget:
        """Grid of small cards, one per connected device."""
        self._card_container = QWidget()
        self._card_grid = QGridLayout(self._card_container)
        self._card_grid.setContentsMargins(0, 0, 0, 0)
        self._card_grid.setSpacing(10)
        self._card_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        return self._card_container

    def _clear_device_cards(self) -> None:
        while self._card_grid.count():
            item = self._card_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _make_small_card(self, device: DeviceInfo, state: str) -> QFrame:
        card = QFrame()
        card.setObjectName("DeviceCard")
        card.setFixedSize(160, 148)
        column = QVBoxLayout(card)
        column.setContentsMargins(12, 12, 12, 12)
        column.setSpacing(6)

        # head: icon + name
        head = QHBoxLayout()
        head.setSpacing(8)
        icon_tile = QFrame()
        icon_tile.setObjectName("IconBadge")
        icon_tile.setFixedSize(34, 34)
        icon_layout = QHBoxLayout(icon_tile)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        phone = QLabel()
        phone.setPixmap(icon("phone", COLORS["accent_hover"], 18).pixmap(18, 18))
        phone.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(phone)
        head.addWidget(icon_tile, 0, Qt.AlignTop)
        name = QLabel(f"{device.manufacturer} {device.model}".strip())
        name.setObjectName("InfoValue")
        name.setWordWrap(True)
        head.addWidget(name, 1)
        column.addLayout(head)

        # pills
        pills = QHBoxLayout()
        pills.setSpacing(5)
        conn = StatusPill("Wi-Fi" if device.connection_type == "wifi" else "USB", "info")
        pills.addWidget(conn)
        online = device.state == "device"
        state_pill = StatusPill(
            "已连接" if online else "未授权" if device.state == "unauthorized" else "离线",
            "success" if online else "warning" if device.state in {"unauthorized", "offline"} else "error",
        )
        pills.addWidget(state_pill)
        pills.addStretch()
        column.addLayout(pills)

        # buttons stacked vertically
        start_btn = QPushButton("开始投屏" if online else "投屏不可用")
        start_btn.setObjectName("PrimaryButton")
        start_btn.setFixedHeight(28)
        start_btn.setCursor(Qt.PointingHandCursor)
        start_btn.setEnabled(online and state in ("idle", "error"))
        start_btn.clicked.connect(
            lambda checked, s=device.serial: self.start_requested.emit(s)
        )
        column.addWidget(start_btn)
        return card

    def set_device_cards(self, devices: list[DeviceInfo], cast_states: dict[str, str]) -> None:
        self._clear_device_cards()
        columns = max(1, min(3, len(devices)))
        for index, device in enumerate(devices):
            state = cast_states.get(device.serial, "idle")
            self._card_grid.addWidget(self._make_small_card(device, state), index // columns, index % columns)
        self._card_container.setVisible(bool(devices))

    def set_primary_device(self, device: DeviceInfo | None, codecs: list, state: str = "idle") -> None:
        if device is None:
            self._device = None
            self.control_panel.set_device(None)
            self.screen_card.set_device(None)
            return
        self._device = device
        name = f"{device.manufacturer} {device.model}".strip()
        self.control_panel.set_device(device.serial, name)
        self.screen_card.set_device(device.serial)

    def set_screen_info(self, info: dict) -> None:
        self.screen_card.set_screen_info(info)

    def set_recording(self, serial: str, recording: bool) -> None:
        if self._device is not None and self._device.serial == serial:
            self.screen_card.set_recording(recording)

    def set_device_codecs(self, serial: str, codecs: list) -> None:
        pass  # codecs live on the device cards / detail page now

    def set_device_cast_state(self, serial: str, state: str) -> None:
        pass  # casting state lives on device cards / sessions page now


    def set_adb(self, ok: bool, text: str) -> None:
        self.adb_tile[1].setText(text)

    def set_devices(self, devices: int, online: int) -> None:
        self.device_tile[1].setText(f"{online} / {devices} 台")

    def set_casting(self, count: int) -> None:
        self.casting_tile[1].setText(f"{count} 路")

    def set_scan(self, text: str) -> None:
        self.scan_tile[1].setText(text)


