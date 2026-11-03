from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from core.adb_network_manager import parse_address, validate_port
from core.device_info import CONNECTION_WIFI, DeviceInfo
from ui.icons import icon
from ui.theme import COLORS


class NetworkConnectDialog(QDialog):
    connect_requested = Signal(str, int)
    disconnect_requested = Signal(str, int)
    scan_requested = Signal()
    restart_server_requested = Signal()

    def __init__(self, parent=None, devices: list[DeviceInfo] | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("连接网络设备")
        self.setModal(True)
        self.setMinimumWidth(420)
        self._busy = False
        devices = devices or []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        title = QLabel("连接网络设备")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        subtitle = QLabel("通过 ADB TCP/IP 连接同一局域网内的 Android 手机")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(subtitle)

        layout.addWidget(self._field_label("连接地址（支持 192.168.1.23 或 192.168.1.23:5555）"))
        self.address_edit = QLineEdit()
        self.address_edit.setPlaceholderText("10.23.224.216:39401")
        known = [d.serial for d in devices if d.connection_type == CONNECTION_WIFI]
        if known:
            self.address_edit.setText(known[0])
        layout.addWidget(self.address_edit)

        layout.addWidget(self._field_label("端口（地址未含端口时生效）"))
        self.port_edit = QLineEdit("5555")
        layout.addWidget(self.port_edit)

        mode_row = QHBoxLayout()
        mode_label = QLabel("连接方式：ADB TCP/IP")
        mode_label.setObjectName("Muted")
        mode_row.addWidget(mode_label)
        mode_row.addStretch()
        self.scan_button = QPushButton("扫描局域网")
        self.scan_button.setObjectName("GhostButton")
        self.scan_button.setIcon(icon("wifi", COLORS["muted"], 14))
        self.scan_button.setIconSize(QSize(14, 14))
        self.scan_button.setToolTip("探测局域网常用 ADB 端口，并优先直连最近连接过的设备地址")
        self.scan_button.setCursor(Qt.PointingHandCursor)
        self.scan_button.clicked.connect(self._scan)
        mode_row.addWidget(self.scan_button)
        layout.addLayout(mode_row)

        self.status_label = QLabel("")
        self.status_label.setObjectName("Muted")
        self.status_label.setWordWrap(True)
        self.status_label.hide()
        layout.addWidget(self.status_label)

        self.retry_button = QPushButton("重启 ADB Server")
        self.retry_button.setObjectName("GhostButton")
        self.retry_button.setIcon(icon("refresh", COLORS["muted"], 14))
        self.retry_button.setIconSize(QSize(14, 14))
        self.retry_button.setToolTip("仅在 ADB Server 异常时使用；会短暂断开所有 ADB 连接")
        self.retry_button.setCursor(Qt.PointingHandCursor)
        self.retry_button.clicked.connect(self._restart_server)
        self.retry_button.hide()
        layout.addWidget(self.retry_button)

        actions = QHBoxLayout()
        actions.addStretch()
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        self.disconnect_button = QPushButton("断开连接")
        self.disconnect_button.setObjectName("GhostButton")
        self.disconnect_button.setIcon(icon("close", COLORS["muted"], 13))
        self.disconnect_button.setIconSize(QSize(13, 13))
        self.disconnect_button.setToolTip("断开上述地址的 ADB 网络连接")
        self.disconnect_button.setCursor(Qt.PointingHandCursor)
        self.disconnect_button.clicked.connect(self._disconnect)
        self.connect_button = QPushButton("连接设备")
        self.connect_button.setObjectName("PrimaryButton")
        self.connect_button.setIcon(icon("link", "#FFFFFF", 14))
        self.connect_button.setIconSize(QSize(14, 14))
        self.connect_button.setCursor(Qt.PointingHandCursor)
        self.connect_button.clicked.connect(self._submit)
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.disconnect_button)
        actions.addWidget(self.connect_button)
        layout.addLayout(actions)

        hint = QLabel("提示：请确保手机已开启 ADB 网络调试并与电脑处于同一局域网。\n（Android 11+ 无线调试配对暂不支持）")
        hint.setObjectName("Caption")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.address_edit.returnPressed.connect(self._submit)
        self.port_edit.returnPressed.connect(self._submit)

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("InfoLabel")
        return label

    # ------------------------------------------------------------------
    def _parsed(self) -> tuple[str | None, int | None]:
        ip, port, error = parse_address(self.address_edit.text())
        if error:
            self._show_error(error)
            return None, None
        if port is None:
            port, port_error = validate_port(self.port_edit.text())
            if port_error:
                self._show_error(port_error)
                return None, None
        return ip, port

    def _submit(self) -> None:
        if self._busy:
            return
        ip, port = self._parsed()
        if ip is None or port is None:
            return
        self.set_busy(True)
        self.retry_button.hide()
        self.connect_requested.emit(ip, port)

    def _disconnect(self) -> None:
        if self._busy:
            return
        ip, port = self._parsed()
        if ip is None or port is None:
            return
        self.disconnect_requested.emit(ip, port)

    def _scan(self) -> None:
        if self._busy:
            return
        self._busy = True
        self.scan_button.setEnabled(False)
        self.scan_button.setText("扫描中…")
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(False)
        self.address_edit.setEnabled(False)
        self.port_edit.setEnabled(False)
        self.status_label.setText("正在扫描局域网常用端口（5555～5560）并尝试记忆的设备地址…")
        self.status_label.setStyleSheet("")
        self.status_label.show()
        self.scan_requested.emit()

    def _restart_server(self) -> None:
        if self._busy:
            return
        self._busy = True
        self.retry_button.setEnabled(False)
        self.retry_button.setText("正在重启…")
        self.restart_server_requested.emit()

    # ------------------------------------------------------------------
    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.connect_button.setEnabled(not busy)
        self.connect_button.setText("连接中…" if busy else "连接设备")
        self.disconnect_button.setEnabled(not busy)
        self.address_edit.setEnabled(not busy)
        self.port_edit.setEnabled(not busy)

    def set_scanning(self, scanning: bool) -> None:
        self._busy = scanning
        self.scan_button.setEnabled(not scanning)
        self.scan_button.setText("扫描中…" if scanning else "扫描局域网")
        self.connect_button.setEnabled(not scanning)
        self.disconnect_button.setEnabled(not scanning)
        self.address_edit.setEnabled(not scanning)
        self.port_edit.setEnabled(not scanning)
        if not scanning:
            self.status_label.hide()

    def set_restarting(self, restarting: bool) -> None:
        self._busy = restarting
        self.retry_button.setEnabled(not restarting)
        self.retry_button.setText("正在重启…" if restarting else "重启 ADB Server")
        self.connect_button.setEnabled(not restarting)
        self.address_edit.setEnabled(not restarting)
        self.port_edit.setEnabled(not restarting)
        if not restarting:
            self.retry_button.hide()

    def _show_error(self, message: str) -> None:
        self.status_label.setText(f"⚠ {message}")
        self.status_label.setStyleSheet(f"color: {COLORS['error']};")
        self.status_label.show()

    def show_result(self, success: bool, message: str, server_error: bool = False) -> None:
        self.set_busy(False)
        if success:
            self.retry_button.hide()
            self.status_label.setText(f"✓ {message or '连接成功'}")
            self.status_label.setStyleSheet(f"color: {COLORS['success']};")
            self.status_label.show()
            self.accept()
            return
        self.retry_button.setVisible(bool(server_error))
        self.retry_button.setEnabled(True)
        self.retry_button.setText("重启 ADB Server")
        self._show_error(message or "连接失败")

    def show_scan_result(self, found: int, connected: int) -> None:
        self.set_scanning(False)
        if connected:
            self.status_label.setText(f"✓ 发现 {found} 台设备，成功连接 {connected} 台")
            self.status_label.setStyleSheet(f"color: {COLORS['success']};")
            self.status_label.show()
            self.accept()
        elif found:
            self._show_error(f"发现 {found} 台设备开放端口，但 ADB 连接失败")
        else:
            self._show_error("未发现可连接的设备；请确认手机已开启 ADB 网络调试（adb tcpip 5555）")

    def show_restart_result(self, success: bool, message: str) -> None:
        self.set_restarting(False)
        if success:
            self.status_label.setText("✓ ADB Server 已重启，请重新点击「连接设备」")
            self.status_label.setStyleSheet(f"color: {COLORS['success']};")
            self.status_label.show()
        else:
            self.retry_button.show()
            self._show_error(message or "ADB Server 重启失败")
