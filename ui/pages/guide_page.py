from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.icons import icon
from ui.theme import COLORS


_STEPS_USB = [
    ("01", "使用支持数据传输的 USB 线连接手机", "部分充电线没有数据针脚，建议使用原装线或确认支持文件传输的线。"),
    ("02", "开启开发者选项与 USB 调试", "设置 → 关于手机 → 连续点击「版本号」7 次；返回设置 → 开发者选项 → 打开「USB 调试」。"),
    ("03", "允许这台电脑调试", "插入 USB 后手机弹出「允许 USB 调试吗？」时，勾选「始终允许」并确定。"),
    ("04", "等待 SmartCast 自动识别", "设备管理页会自动出现设备卡片，点击「开始投屏」即可。"),
]

_STEPS_WIFI = [
    ("01", "先让手机开启 ADB 网络调试", "最常见方式：USB 连接一次，执行 adb tcpip 5555 后拔线；Android 11+ 也可在开发者选项中开启「无线调试」。"),
    ("02", "确认手机与电脑在同一 Wi-Fi", "两者必须处于同一局域网网段，否则无法连接。"),
    ("03", "打开设备管理 → 网络连接设备", "点击右上角带 Wi-Fi 图标的「网络连接设备」按钮。"),
    ("04", "输入地址并连接", "支持两种格式：完整地址如 192.168.1.23:5555，或只填 IP 再单独填端口（默认 5555）。"),
    ("05", "扫描局域网（可选）", "不确定手机 IP 时点「扫描局域网」，自动探测常用端口并优先直连最近连接过的设备。"),
    ("06", "开始投屏", "Wi-Fi 设备卡片出现后，点「开始投屏」，与 USB 投屏使用完全相同的设置和编码器。"),
]

_TIPS = [
    ("断开连接", "Wi-Fi 设备卡片上的「断开」按钮或连接窗口中的「断开连接」，只断开该设备，不影响其他设备。"),
    ("无线调试端口不固定", "Android 11+ 的「无线调试」端口是随机的（如 39401），扫描无法直接发现，但连接过一次后 SmartCast 会记住地址，下次秒连。"),
    ("设备未授权", "手机弹出授权时请点允许；已拒绝可在开发者选项中「撤销 USB 调试授权」后重试。"),
    ("设备 offline / 掉线", "网络波动后设备会显示 offline，恢复 Wi-Fi 后重新连接即可，独立投屏设置不会丢失。"),
    ("连接失败排查", "依次检查：是否同一 Wi-Fi → 手机 ADB 网络调试是否开启 → 端口是否正确 → Windows 防火墙是否拦截（错误 10013）。"),
]


class GuidePage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("SettingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(scroll)

        page = QWidget()
        scroll.setWidget(page)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(20, 16, 20, 16)
        page_layout.setSpacing(14)

        title_column = QVBoxLayout()
        title_column.setSpacing(3)
        title = QLabel("使用指南")
        title.setObjectName("PageTitle")
        subtitle = QLabel("USB 与 Wi-Fi 网络投屏的连接方法和常见问题")
        subtitle.setObjectName("PageSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        page_layout.addLayout(title_column)

        content = QWidget()
        content.setMaximumWidth(900)
        content.setMinimumWidth(560)
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        layout.addWidget(self._section("USB 有线连接", "phone", _STEPS_USB))
        layout.addWidget(self._section("Wi-Fi 网络连接（ADB TCP/IP）", "wifi", _STEPS_WIFI))
        layout.addWidget(self._tips_card())
        layout.addStretch(1)

        page_layout.addWidget(content)
        page_layout.addStretch(1)

    def _section(self, title: str, icon_name: str, steps) -> QFrame:
        card = QFrame()
        card.setObjectName("SettingsSection")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(8)
        head_icon = QLabel()
        head_icon.setPixmap(icon(icon_name, COLORS["accent_hover"], 18).pixmap(18, 18))
        head.addWidget(head_icon)
        head_label = QLabel(title)
        head_label.setObjectName("InfoValue")
        head.addWidget(head_label)
        head.addStretch()
        layout.addLayout(head)

        for number, heading, detail in steps:
            row = QHBoxLayout()
            row.setSpacing(10)
            badge = QLabel(number)
            badge.setFixedSize(26, 26)
            badge.setAlignment(Qt.AlignCenter)
            badge.setObjectName("StepBadge")
            row.addWidget(badge, 0, Qt.AlignTop)
            text_column = QVBoxLayout()
            text_column.setSpacing(2)
            heading_label = QLabel(heading)
            heading_label.setObjectName("InfoValue")
            detail_label = QLabel(detail)
            detail_label.setObjectName("Caption")
            detail_label.setWordWrap(True)
            text_column.addWidget(heading_label)
            text_column.addWidget(detail_label)
            row.addLayout(text_column, 1)
            layout.addLayout(row)
        return card

    def _tips_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("SettingsSection")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        head = QHBoxLayout()
        head.setSpacing(8)
        head_icon = QLabel()
        head_icon.setPixmap(icon("help", COLORS["accent_hover"], 18).pixmap(18, 18))
        head.addWidget(head_icon)
        head_label = QLabel("常见问题与技巧")
        head_label.setObjectName("InfoValue")
        head.addWidget(head_label)
        head.addStretch()
        layout.addLayout(head)

        for heading, detail in _TIPS:
            row = QVBoxLayout()
            row.setSpacing(2)
            heading_label = QLabel(f"· {heading}")
            heading_label.setObjectName("InfoValue")
            detail_label = QLabel(detail)
            detail_label.setObjectName("Caption")
            detail_label.setWordWrap(True)
            row.addWidget(heading_label)
            row.addWidget(detail_label)
            layout.addLayout(row)
        return card
