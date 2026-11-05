from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.device_info import DeviceInfo
from core.parameter_optimizer import recommend_bitrate
from ui.components.common import StatusDot, repolish
from ui.components.section import SettingsSection
from ui.components.toggle import ToggleSwitch
from ui.icons import icon
from ui.theme import COLORS


class SettingsPage(QWidget):
    back_requested = Signal()
    save_requested = Signal(dict)
    reset_requested = Signal()
    detect_adb_requested = Signal(str)
    detect_scrcpy_requested = Signal(str)
    open_logs_requested = Signal()
    clear_logs_requested = Signal()
    export_logs_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._log_lines: list[str] = []
        self._device_context: list[tuple[DeviceInfo, list]] = []
        self._recommended_mbps: int | None = None
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(11)
        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        title = QLabel("设置")
        title.setObjectName("PageTitle")
        subtitle = QLabel("管理 ADB、scrcpy、默认投屏参数与设备扫描行为")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        header.addLayout(title_column, 1)
        top_save = QPushButton("保存设置")
        top_save.setObjectName("PrimaryButton")
        top_save.setIcon(icon("check", "#FFFFFF", 15))
        top_save.setIconSize(QSize(15, 15))
        top_save.setCursor(Qt.PointingHandCursor)
        top_save.clicked.connect(self._emit_save)
        header.addWidget(top_save)
        root.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content_host = QWidget()
        center = QHBoxLayout(content_host)
        center.setContentsMargins(0, 0, 4, 0)
        content = QWidget()
        content.setMaximumWidth(980)
        content.setMinimumWidth(460)
        self.content = content
        content_layout = QVBoxLayout(content)
        content_layout.addWidget(self._build_adb_section())
        content_layout.addWidget(self._build_scrcpy_section())
        content_layout.addWidget(self._build_parameters_section())
        content_layout.addWidget(self._build_scan_section())
        content_layout.addStretch(1)
        center.addWidget(content, 1)
        center.addStretch(1)
        scroll.setWidget(content_host)
        root.addWidget(scroll, 1)

        footer = QHBoxLayout()
        footer.setSpacing(10)
        reset = QPushButton("恢复默认设置")
        reset.setObjectName("GhostButton")
        reset.setCursor(Qt.PointingHandCursor)
        reset.clicked.connect(self.reset_requested)
        footer.addWidget(reset)
        self.footer_status = QLabel("")
        self.footer_status.setObjectName("FooterStatus")
        footer.addWidget(self.footer_status)
        footer.addStretch()
        footer_save = QPushButton("保存并应用")
        footer_save.setObjectName("PrimaryButton")
        footer_save.setIcon(icon("check", "#FFFFFF", 15))
        footer_save.setIconSize(QSize(15, 15))
        footer_save.setCursor(Qt.PointingHandCursor)
        footer_save.clicked.connect(self._emit_save)
        footer.addWidget(footer_save)
        root.addLayout(footer)
        content_layout.setContentsMargins(0, 1, 0, 1)
        content_layout.setSpacing(14)

    def _build_adb_section(self) -> QWidget:
        section = SettingsSection("ADB 配置", "留空时使用内置 resources/adb/adb.exe。修改后可先检测再保存。", "usb")
        row = QHBoxLayout()
        row.setSpacing(8)
        self.adb_edit = QLineEdit()
        self.adb_edit.setPlaceholderText("内置 ADB（推荐）")
        self.adb_detect_button = QPushButton("检测 ADB")
        self.adb_detect_button.setIcon(icon("refresh", COLORS["muted"], 14))
        self.adb_detect_button.setIconSize(QSize(14, 14))
        self.adb_detect_button.setCursor(Qt.PointingHandCursor)
        self.adb_detect_button.clicked.connect(lambda: self.detect_adb_requested.emit(self.adb_edit.text().strip()))
        row.addWidget(self.adb_edit, 1)
        row.addWidget(self.adb_detect_button)
        section.body.addLayout(row)
        status_row = QHBoxLayout()
        status_row.setSpacing(7)
        self.adb_dot = StatusDot(COLORS["faint"], 7)
        self.adb_status = QLabel("尚未检测")
        self.adb_status.setObjectName("Caption")
        status_row.addWidget(self.adb_dot)
        status_row.addWidget(self.adb_status)
        status_row.addStretch()
        section.body.addLayout(status_row)
        return section

    def _build_scrcpy_section(self) -> QWidget:
        section = SettingsSection("scrcpy 配置", "留空时使用内置 resources/scrcpy/scrcpy.exe。投屏窗口由 scrcpy 独立进程提供。", "play")
        row = QHBoxLayout()
        row.setSpacing(8)
        self.scrcpy_edit = QLineEdit()
        self.scrcpy_edit.setPlaceholderText("内置 scrcpy（推荐）")
        self.scrcpy_detect_button = QPushButton("检测 scrcpy")
        self.scrcpy_detect_button.setIcon(icon("refresh", COLORS["muted"], 14))
        self.scrcpy_detect_button.setIconSize(QSize(14, 14))
        self.scrcpy_detect_button.setCursor(Qt.PointingHandCursor)
        self.scrcpy_detect_button.clicked.connect(lambda: self.detect_scrcpy_requested.emit(self.scrcpy_edit.text().strip()))
        row.addWidget(self.scrcpy_edit, 1)
        row.addWidget(self.scrcpy_detect_button)
        section.body.addLayout(row)
        status_row = QHBoxLayout()
        status_row.setSpacing(7)
        self.scrcpy_dot = StatusDot(COLORS["faint"], 7)
        self.scrcpy_status = QLabel("尚未检测")
        self.scrcpy_status.setObjectName("Caption")
        status_row.addWidget(self.scrcpy_dot)
        status_row.addWidget(self.scrcpy_status)
        status_row.addStretch()
        section.body.addLayout(status_row)
        render_row = QHBoxLayout()
        render_row.setSpacing(10)
        render_label = QLabel("渲染后端")
        render_label.setObjectName("InfoLabel")
        self.render_driver = QComboBox()
        for label, value in (
            ("OpenGL（推荐，最流畅）", "opengl"),
            ("自动选择", "auto"),
            ("Direct3D", "direct3d"),
            ("软件渲染", "software"),
        ):
            self.render_driver.addItem(label, value)
        render_row.addWidget(render_label)
        render_row.addWidget(self.render_driver, 1)
        section.body.addLayout(render_row)
        render_hint = QLabel("OpenGL 在当前设备上实测帧率更高；启动失败时会自动回退到自动渲染。")
        render_hint.setObjectName("Caption")
        render_hint.setWordWrap(True)
        section.body.addWidget(render_hint)
        return section

    def _build_parameters_section(self) -> QWidget:
        section = SettingsSection("投屏默认参数", "新连接设备默认采用这些参数；单台设备仍可在设备卡片中单独设置。", "chip")
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        self.codec = QComboBox()
        for label, value in (("自动选择编码器", "auto"), ("H.264", "H.264"), ("H.265", "H.265")):
            self.codec.addItem(label, value)
        self.resolution = QComboBox()
        for label, value in (("原始分辨率（推荐）", "original"), ("自动", "auto"), ("1080p", "1080"), ("720p", "720"), ("1440p", "1440"), ("2560", "2560")):
            self.resolution.addItem(label, value)
        self.fps = QComboBox()
        for label, value in (("不限（推荐）", 0), ("30 FPS", 30), ("60 FPS", 60), ("90 FPS", 90), ("120 FPS", 120)):
            self.fps.addItem(label, value)
        self.fps.setToolTip("超过设备刷新率或编码能力会掉帧；建议 0（不限）或 60。")
        self.bitrate = QSpinBox()
        self.bitrate.setRange(1, 128)
        self.bitrate.setSuffix(" Mbps")
        controls = [
            ("视频编码", self.codec, 0, 0),
            ("分辨率", self.resolution, 0, 1),
            ("最大帧率", self.fps, 1, 0),
            ("视频码率", self.bitrate, 1, 1),
        ]
        for label, widget, row, column in controls:
            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(5)
            text = QLabel(label)
            text.setObjectName("InfoLabel")
            cell_layout.addWidget(text)
            cell_layout.addWidget(widget)
            grid.addWidget(cell, row, column)
        section.body.addLayout(grid)
        recommend_row = QHBoxLayout()
        recommend_row.setSpacing(8)
        self.bitrate_hint = QLabel("连接设备后显示推荐码率")
        self.bitrate_hint.setObjectName("BitrateHint")
        self.bitrate_hint.setWordWrap(True)
        self.recommend_button = QPushButton("使用推荐")
        self.recommend_button.setObjectName("LinkButton")
        self.recommend_button.setEnabled(False)
        self.recommend_button.clicked.connect(self._use_recommended_bitrate)
        recommend_row.addWidget(self.bitrate_hint, 1)
        recommend_row.addWidget(self.recommend_button, 0)
        section.body.addLayout(recommend_row)
        audio_row = QHBoxLayout()
        audio_column = QVBoxLayout()
        audio_column.setSpacing(2)
        audio_title = QLabel("音频转发")
        audio_title.setObjectName("InfoValue")
        audio_hint = QLabel("默认开启；关闭后仅投屏画面")
        audio_hint.setObjectName("Caption")
        audio_column.addWidget(audio_title)
        audio_column.addWidget(audio_hint)
        self.audio = ToggleSwitch(True)
        audio_row.addLayout(audio_column, 1)
        audio_row.addWidget(self.audio, 0, Qt.AlignVCenter)
        section.body.addLayout(audio_row)
        hint = QLabel("自动编码会根据每台设备自己的检测结果选择，不会复用其他设备的编码器。")
        hint.setObjectName("Caption")
        hint.setWordWrap(True)
        section.body.addWidget(hint)
        fps_hint = QLabel("帧率 0 表示不限。120 FPS 只有在设备屏幕和编码器都支持时才更流畅，否则会增加掉帧和卡顿。")
        fps_hint.setObjectName("Caption")
        fps_hint.setWordWrap(True)
        section.body.addWidget(fps_hint)
        self.codec.currentIndexChanged.connect(self._refresh_recommendation)
        self.resolution.currentIndexChanged.connect(self._refresh_recommendation)
        self.bitrate.valueChanged.connect(self._refresh_recommendation)
        return section

    def _build_scan_section(self) -> QWidget:
        section = SettingsSection("设备扫描", "投屏期间自动降低扫描频率，避免 ADB 轮询与视频数据通道争用。", "list")
        toggle_row = QHBoxLayout()
        toggle_column = QVBoxLayout()
        toggle_column.setSpacing(2)
        toggle_title = QLabel("自动扫描设备")
        toggle_title.setObjectName("InfoValue")
        toggle_hint = QLabel("关闭后仍可使用设备页的刷新按钮手动扫描")
        toggle_hint.setObjectName("Caption")
        toggle_column.addWidget(toggle_title)
        toggle_column.addWidget(toggle_hint)
        self.auto_scan = ToggleSwitch(True)
        toggle_row.addLayout(toggle_column, 1)
        toggle_row.addWidget(self.auto_scan, 0, Qt.AlignVCenter)
        section.body.addLayout(toggle_row)
        intervals = QHBoxLayout()
        intervals.setSpacing(12)
        idle_cell = QVBoxLayout()
        idle_label = QLabel("空闲状态扫描间隔")
        idle_label.setObjectName("InfoLabel")
        self.idle_interval = QSpinBox()
        self.idle_interval.setRange(1, 60)
        self.idle_interval.setSuffix(" 秒")
        idle_cell.addWidget(idle_label)
        idle_cell.addWidget(self.idle_interval)
        casting_cell = QVBoxLayout()
        casting_label = QLabel("投屏期间扫描间隔（0 = 暂停）")
        casting_label.setObjectName("InfoLabel")
        self.casting_interval = QSpinBox()
        self.casting_interval.setRange(0, 120)
        self.casting_interval.setSuffix(" 秒")
        self.casting_interval.setSpecialValueText("暂停（推荐）")
        casting_cell.addWidget(casting_label)
        casting_cell.addWidget(self.casting_interval)
        intervals.addLayout(idle_cell)
        intervals.addLayout(casting_cell)
        section.body.addLayout(intervals)
        return section

    def _build_log_section(self) -> QWidget:
        section = SettingsSection("日志", "界面日志最多保留 300 行；完整日志同步写入 logs/smartcast.log。", "folder")
        actions = QHBoxLayout()
        actions.setSpacing(8)
        open_button = QPushButton("打开日志目录")
        open_button.setIcon(icon("folder", COLORS["muted"], 14))
        open_button.clicked.connect(self.open_logs_requested)
        clear_button = QPushButton("清空界面日志")
        clear_button.setIcon(icon("trash", COLORS["muted"], 14))
        clear_button.clicked.connect(self.clear_logs_requested)
        export_button = QPushButton("导出日志")
        export_button.setIcon(icon("export", COLORS["muted"], 14))
        export_button.clicked.connect(self.export_logs_requested)
        for button in (open_button, clear_button, export_button):
            button.setCursor(Qt.PointingHandCursor)
            actions.addWidget(button)
        actions.addStretch()
        section.body.addLayout(actions)
        self.log_view = QTextEdit()
        self.log_view.setObjectName("LogView")
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(130)
        self.log_view.setMaximumHeight(190)
        self.log_view.setPlaceholderText("运行日志会显示在这里")
        section.body.addWidget(self.log_view)
        return section

    def load(self, settings: dict) -> None:
        self.adb_edit.setText(settings.get("adb_path", ""))
        self.scrcpy_edit.setText(settings.get("scrcpy_path", ""))
        self._set_combo_data(self.render_driver, settings.get("render_driver", "opengl"))
        defaults = settings.get("default_parameters", {})
        self._set_combo_data(self.codec, defaults.get("video_codec", "auto"))
        resolution = str(defaults.get("resolution", "original")).lower().replace("p", "")
        if resolution not in {"original", "auto", "720", "1080", "1440", "2560"}:
            resolution = "original"
        self._set_combo_data(self.resolution, resolution)
        self._set_combo_data(self.fps, int(defaults.get("fps", 0)))
        self.bitrate.setValue(int(defaults.get("bitrate_mbps", 8)))
        self.audio.setChecked(bool(defaults.get("audio", True)))
        self.auto_scan.setChecked(bool(settings.get("auto_scan", True)))
        self.idle_interval.setValue(int(settings.get("scan_interval", 2)))
        self.casting_interval.setValue(int(settings.get("casting_scan_interval", 0)))
        self.footer_status.setText("")
        self._refresh_recommendation()

    def set_device_context(self, devices: list[DeviceInfo], codecs_by_serial: dict[str, list]) -> None:
        self._device_context = [
            (device, codecs_by_serial.get(device.serial, []))
            for device in devices
            if device.state == "device"
        ]
        self._refresh_recommendation()

    def _refresh_recommendation(self) -> None:
        recommendations = []
        for device, codecs in self._device_context:
            recommendation = recommend_bitrate(
                device,
                codecs,
                str(self.codec.currentData()),
                str(self.resolution.currentData()),
            )
            if recommendation is not None:
                recommendations.append((device, recommendation))
        if not recommendations:
            self._recommended_mbps = None
            if self._device_context:
                self.bitrate_hint.setText("当前编码/分辨率在已连接设备上不可用")
            else:
                self.bitrate_hint.setText("连接设备后显示推荐码率")
            self.bitrate_hint.setProperty("tone", "muted")
            repolish(self.bitrate_hint)
            self.recommend_button.setEnabled(False)
            return
        device, recommendation = max(recommendations, key=lambda item: item[1].mbps)
        self._recommended_mbps = recommendation.mbps
        text = f"{recommendation.summary} · {recommendation.detail}（{device.manufacturer} {device.model}）"
        if len(recommendations) > 1:
            text += " · 按最高需求"
        if self.bitrate.value() < recommendation.mbps:
            text += " · 当前偏低"
            self.bitrate_hint.setProperty("tone", "warning")
            repolish(self.bitrate_hint)
        else:
            text += " · 当前已满足"
            self.bitrate_hint.setProperty("tone", "success")
            repolish(self.bitrate_hint)
        self.bitrate_hint.setText(text)
        self.recommend_button.setText(f"使用推荐（{recommendation.mbps} Mbps）")
        self.recommend_button.setEnabled(self.bitrate.value() != recommendation.mbps)

    def _use_recommended_bitrate(self) -> None:
        if self._recommended_mbps is not None:
            self.bitrate.setValue(self._recommended_mbps)

    def collect(self) -> dict:
        return {
            "adb_path": self.adb_edit.text().strip(),
            "scrcpy_path": self.scrcpy_edit.text().strip(),
            "scan_interval": self.idle_interval.value(),
            "casting_scan_interval": self.casting_interval.value(),
            "auto_scan": self.auto_scan.isChecked(),
            "render_driver": self.render_driver.currentData(),
            "default_parameters": {
                "video_codec": self.codec.currentData(),
                "resolution": self.resolution.currentData(),
                "fps": int(self.fps.currentData()),
                "bitrate_mbps": self.bitrate.value(),
                "audio": self.audio.isChecked(),
            },
        }

    def focus_logs(self) -> None:
        self.scroll.ensureWidgetVisible(self.log_section, 20, 20)

    def set_adb_status(self, ok: bool, text: str) -> None:
        self.adb_dot.set_color(COLORS["success"] if ok else COLORS["error"])
        self.adb_status.setText(text)

    def set_scrcpy_status(self, ok: bool, text: str) -> None:
        self.scrcpy_dot.set_color(COLORS["success"] if ok else COLORS["error"])
        self.scrcpy_status.setText(text)

    def set_tool_busy(self, tool: str, busy: bool) -> None:
        button = self.adb_detect_button if tool == "adb" else self.scrcpy_detect_button
        label = "检测中…" if busy else ("检测 ADB" if tool == "adb" else "检测 scrcpy")
        button.setText(label)
        button.setEnabled(not busy)

    def set_saved(self, text: str = "设置已保存并应用") -> None:
        self.footer_status.setText(text)
        self.footer_status.setProperty("tone", "success")
        repolish(self.footer_status)

    def set_error(self, text: str) -> None:
        self.footer_status.setText(text)
        self.footer_status.setProperty("tone", "error")
        repolish(self.footer_status)

    def set_hint(self, text: str) -> None:
        self.footer_status.setText(text)
        self.footer_status.setProperty("tone", "muted")
        repolish(self.footer_status)

    def append_log(self, line: str) -> None:
        self._log_lines.append(line)
        if len(self._log_lines) > 300:
            self._log_lines = self._log_lines[-300:]
        self.log_view.setPlainText("\n".join(self._log_lines))
        bar = self.log_view.verticalScrollBar()
        bar.setValue(bar.maximum())

    def clear_log(self) -> None:
        self._log_lines.clear()
        self.log_view.clear()

    def _emit_save(self) -> None:
        self.save_requested.emit(self.collect())

    @staticmethod
    def _set_combo_data(combo: QComboBox, value) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)


    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "content"):
            # 最大宽度不得小于最小宽度，否则布局挤压导致内容被裁
            cap = int(self.width() * 0.7)
            self.content.setMaximumWidth(max(self.content.minimumWidth(), cap))
