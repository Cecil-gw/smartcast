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


_INTRO = (
    "SmartCast 是一款面向 Windows 的 Android 投屏与设备管理工具。"
    "它把 ADB 设备连接、scrcpy 投屏、手机控制、屏幕调节、截图录屏整合在同一个界面，"
    "并针对多设备场景做了完整隔离：每台设备用 ADB 序列号独立识别、独立配置、独立投屏，"
    "USB 与 Wi-Fi（ADB TCP/IP）设备统一管理。"
)

_MODULES = [
    ("home", "首页", "投放常用操作的工作台：设备概览、手机控制、屏幕控制、运行概况与快捷入口。"),
    ("devices", "设备管理", "所有已连接设备的卡片列表，可开始/停止投屏、查看详情、修改设备投屏设置、断开无线设备，右上角可发起网络连接。"),
    ("monitor", "投屏中心", "统一查看每个投屏会话的状态、实时运行时长、编码器/码率/分辨率，可单独停止或全屏。"),
    ("screen", "投屏设置", "设置默认投屏参数（编码、分辨率、帧率、码率、音频），保存后应用到已连接设备。"),
    ("folder", "媒体管理", "集中管理截图与录屏文件：按设备和类型筛选，打开文件或所在目录，删除记录或文件。"),
    ("list", "日志", "实时查看运行日志，支持按级别筛选、搜索、清空界面、导出与打开日志目录。"),
    ("settings", "设置", "配置 ADB / scrcpy 工具路径、扫描间隔、默认参数、渲染后端等全局选项。"),
]

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
    ("悬浮控制条", "投屏运行时，投屏窗口下方会出现控制条：返回/主页/音量等按键、全屏切换、截图、录屏、亮度与旋转调节，跟随窗口移动。"),
    ("投屏中心", "侧边栏「投屏中心」查看所有会话的状态、实时运行时长和投屏参数，可单独停止或全屏。"),
    ("媒体管理", "侧边栏「媒体管理」集中管理截图与录屏文件，支持按设备和类型筛选、打开文件或目录、删除。"),
    ("传文件到手机", "在电脑上复制文件（Ctrl+C），在 SmartCast 窗口按 Ctrl+V 即可发送到手机的 Download/SmartCast 目录；也可以直接把文件拖进窗口。"),
    ("从手机取回文件", "在设备卡片点「传文件」打开传输窗口，填写手机路径即可取回到电脑；也可复制形如 /sdcard/Download/xx 的路径后在 SmartCast 按 Ctrl+V。"),
    ("断开连接", "Wi-Fi 设备卡片上的「断开」按钮只断开该设备，不影响其他设备与正在运行的投屏。"),
    ("无线调试端口不固定", "Android 11+ 的「无线调试」端口是随机的（如 39401），扫描无法直接发现，但连接过一次后 SmartCast 会记住地址，下次秒连。"),
    ("设备未授权", "手机弹出授权时请点允许；已拒绝可在开发者选项中「撤销 USB 调试授权」后重试。"),
    ("设备 offline / 掉线", "网络波动后设备会显示 offline，恢复 Wi-Fi 后重新连接即可，独立投屏设置不会丢失。"),
    ("连接失败排查", "依次检查：是否同一 Wi-Fi → 手机 ADB 网络调试是否开启 → 端口是否正确 → Windows 防火墙是否拦截（错误 10013）。"),
    ("ADB 报 protocol fault / 超时", "通常是多个工具（Android Studio、手机助手等）自带的 adb 互相抢占服务。SmartCast 会自动关闭其它 adb 进程并重启服务，无需手动处理。"),
    ("投屏黑屏或花屏", "在「设置」中切换渲染后端（OpenGL / Direct3D / software）后重试；也可在设备设置里更换视频编码器。"),
    ("亮度 / 旋转改不了", "部分 Android 11+ 机型由厂商策略保护这些系统设置，属于系统限制，界面会给出明确提示。"),
    ("录屏没有声音", "当前录屏为无声录制，避免各厂商音频权限差异导致录制失败。"),
    ("窗口位置或大小异常", "SmartCast 会记忆上次关闭时的窗口位置与尺寸；若显示器发生变化导致位置越界，会自动回退到默认尺寸。"),
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
        subtitle = QLabel("软件简介、功能模块说明、连接方式与常见问题")
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

        layout.addWidget(self._intro_card())
        layout.addWidget(self._modules_card())
        layout.addWidget(self._section("USB 有线连接", "phone", _STEPS_USB))
        layout.addWidget(self._section("Wi-Fi 网络连接（ADB TCP/IP）", "wifi", _STEPS_WIFI))
        layout.addWidget(self._tips_card())
        layout.addStretch(1)

        page_layout.addWidget(content)
        page_layout.addStretch(1)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "content"):
            self.content.setMaximumWidth(max(460, int(self.width() * 0.7)))

    def _intro_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("SettingsSection")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(9)
        head_icon = QLabel()
        head_icon.setPixmap(icon("bolt", COLORS["accent_hover"], 20).pixmap(20, 20))
        head.addWidget(head_icon)
        head_label = QLabel("软件简介")
        head_label.setObjectName("GuideSectionTitle")
        head.addWidget(head_label)
        head.addStretch()
        layout.addLayout(head)

        text = QLabel(_INTRO)
        text.setObjectName("Caption")
        text.setWordWrap(True)
        layout.addWidget(text)
        return card

    def _modules_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("SettingsSection")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(9)
        head_icon = QLabel()
        head_icon.setPixmap(icon("list", COLORS["accent_hover"], 20).pixmap(20, 20))
        head.addWidget(head_icon)
        head_label = QLabel("功能模块")
        head_label.setObjectName("GuideSectionTitle")
        head.addWidget(head_label)
        head.addStretch()
        layout.addLayout(head)

        for icon_name, name, description in _MODULES:
            row = QHBoxLayout()
            row.setSpacing(12)
            badge = QLabel()
            badge.setFixedSize(30, 30)
            badge.setAlignment(Qt.AlignCenter)
            badge.setPixmap(icon(icon_name, COLORS["accent_hover"], 18).pixmap(18, 18))
            row.addWidget(badge, 0, Qt.AlignTop)
            text_column = QVBoxLayout()
            text_column.setSpacing(2)
            name_label = QLabel(name)
            name_label.setObjectName("InfoValue")
            desc_label = QLabel(description)
            desc_label.setObjectName("Caption")
            desc_label.setWordWrap(True)
            text_column.addWidget(name_label)
            text_column.addWidget(desc_label)
            row.addLayout(text_column, 1)
            layout.addLayout(row)
        return card

    def _section(self, title: str, icon_name: str, steps) -> QFrame:
        card = QFrame()
        card.setObjectName("SettingsSection")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(9)
        head_icon = QLabel()
        head_icon.setPixmap(icon(icon_name, COLORS["accent_hover"], 20).pixmap(20, 20))
        head.addWidget(head_icon)
        head_label = QLabel(title)
        head_label.setObjectName("GuideSectionTitle")
        head.addWidget(head_label)
        head.addStretch()
        layout.addLayout(head)

        for number, heading, detail in steps:
            row = QHBoxLayout()
            row.setSpacing(12)
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
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(9)
        head_icon = QLabel()
        head_icon.setPixmap(icon("help", COLORS["accent_hover"], 20).pixmap(20, 20))
        head.addWidget(head_icon)
        head_label = QLabel("常见问题与技巧")
        head_label.setObjectName("GuideSectionTitle")
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
