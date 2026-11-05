from __future__ import annotations

from PySide6.QtCore import QSize, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.device_info import DeviceInfo
from ui.components.card_grid import CardGrid
from ui.components.common import StatusPill
from ui.components.device_card import DeviceCard
from ui.components.empty_state import EmptyState
from ui.components.toggle import ToggleSwitch
from ui.icons import icon
from ui.theme import COLORS


class DevicePage(QWidget):
    start_requested = Signal(str)
    stop_requested = Signal(str)
    details_requested = Signal(str)
    settings_requested = Signal(str)
    copy_requested = Signal(str)
    refresh_requested = Signal()
    help_requested = Signal()
    auto_scan_changed = Signal(bool)
    network_connect_requested = Signal()
    disconnect_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.cards: dict[str, DeviceCard] = {}
        self._devices: list[DeviceInfo] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(10)
        title_column = QVBoxLayout()
        title_column.setSpacing(4)
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title = QLabel("设备管理")
        title.setObjectName("PageTitle")
        self.count_pill = StatusPill("0 台在线", "idle")
        self.count_pill.hide()
        title_row.addWidget(title)
        title_row.addWidget(self.count_pill, 0, Qt.AlignVCenter)
        title_row.addStretch()
        title_column.addLayout(title_row)
        self.page_subtitle = QLabel("连接手机后自动识别设备信息与可用编码器")
        self.page_subtitle.setObjectName("PageSubtitle")
        title_column.addWidget(self.page_subtitle)
        header.addLayout(title_column, 1)

        refresh_button = QPushButton("刷新")
        refresh_button.setIcon(icon("refresh", COLORS["muted"], 15))
        refresh_button.setIconSize(QSize(15, 15))
        refresh_button.setCursor(Qt.PointingHandCursor)
        refresh_button.clicked.connect(self.refresh_requested)
        header.addWidget(refresh_button)

        self.network_button = QPushButton("网络连接设备")
        self.network_button.setObjectName("GhostButton")
        self.network_button.setIcon(icon("wifi", COLORS["muted"], 15))
        self.network_button.setIconSize(QSize(15, 15))
        self.network_button.setToolTip("通过 ADB TCP/IP 连接局域网设备")
        self.network_button.setCursor(Qt.PointingHandCursor)
        self.network_button.clicked.connect(self.network_connect_requested)
        header.addWidget(self.network_button)

        self.scan_chip = QLabel("自动扫描")
        self.scan_chip.setObjectName("Muted")
        header.addWidget(self.scan_chip)
        self.auto_scan = ToggleSwitch(True)
        self.auto_scan.setToolTip("自动扫描设备")
        self.auto_scan.toggled.connect(self.auto_scan_changed)
        header.addWidget(self.auto_scan, 0, Qt.AlignVCenter)
        root.addLayout(header)

        self.stack = QStackedWidget()
        self.empty_state = EmptyState()
        self.empty_state.scan_requested.connect(self.refresh_requested)
        self.empty_state.help_requested.connect(self.help_requested)
        self.stack.addWidget(self.empty_state)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.grid_host = QWidget()
        host_layout = QVBoxLayout(self.grid_host)
        host_layout.setContentsMargins(0, 1, 4, 1)
        host_layout.setSpacing(0)
        self.card_grid = CardGrid(min_card_width=430, gap=14)
        host_layout.addWidget(self.card_grid)
        host_layout.addStretch(1)
        self.scroll.setWidget(self.grid_host)
        self.stack.addWidget(self.scroll)
        root.addWidget(self.stack, 1)
        self._last_width = 0

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "scroll"):
            self.scroll.setMaximumWidth(max(360, int(self.width() * 0.7)))
            QTimer.singleShot(0, self._update_grid_width)

    def _update_grid_width(self) -> None:
        width = self.scroll.viewport().width() or self.width() - 48
        self.card_grid.set_available_width(max(120, width - 8))

    def set_devices(self, devices: list[DeviceInfo]) -> list[str]:
        previous = set(self.cards)
        current = {device.serial for device in devices}
        for serial in previous - current:
            card = self.cards.pop(serial)
            self.card_grid.set_cards(list(self.cards.values()))
            card.deleteLater()
        for device in devices:
            card = self.cards.get(device.serial)
            if card is None:
                card = DeviceCard(device)
                card.start_requested.connect(self.start_requested)
                card.stop_requested.connect(self.stop_requested)
                card.details_requested.connect(self.details_requested)
                card.settings_requested.connect(self.settings_requested)
                card.serial_copied.connect(self.copy_requested)
                card.disconnect_requested.connect(self.disconnect_requested)
                self.cards[device.serial] = card
            else:
                card.update_device(device)
        self._devices = list(devices)
        ordered = [self.cards[device.serial] for device in devices]
        self.card_grid.set_cards(ordered)
        online = sum(1 for device in devices if device.state == "device")
        self.count_pill.setText(f"{online} 台在线" if devices else "暂无设备")
        self.count_pill.set_tone("success" if online else "idle")
        if devices:
            self.page_subtitle.setText(f"已连接 {online} 台设备 · 发现 {len(devices)} 台设备")
        else:
            self.page_subtitle.setText("连接手机后自动识别设备信息与可用编码器")
        self.stack.setCurrentWidget(self.scroll if devices else self.empty_state)
        QTimer.singleShot(0, self._update_grid_width)
        return sorted(previous - current)

    def set_card_casting(self, serial: str, state: str) -> None:
        card = self.cards.get(serial)
        if card:
            card.set_casting_state(state)

    def set_card_codecs(self, serial: str, codecs) -> None:
        card = self.cards.get(serial)
        if card:
            card.set_codecs(codecs)

    def set_adb_status(self, ok: bool, text: str) -> None:
        self.empty_state.set_adb_status(ok, text)

    def set_auto_scan(self, enabled: bool, interval: int) -> None:
        self.auto_scan.blockSignals(True)
        self.auto_scan.setChecked(enabled)
        self.auto_scan.blockSignals(False)
        self.scan_chip.setText(f"自动扫描 · {interval}s" if enabled else "自动扫描已暂停")


