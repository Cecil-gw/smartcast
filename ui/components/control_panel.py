
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QVBoxLayout

from ui.icons import icon
from ui.theme import COLORS

ACTIONS = (
    ("back", "返回", "back"),
    ("home", "主页", "home"),
    ("recent", "多任务", "list"),
    ("volume_up", "音量+", "bolt"),
    ("volume_down", "音量-", "moon"),
    ("mute", "静音", "close"),
    ("lock", "锁屏", "screen"),
    ("power_menu", "电源菜单", "bolt"),
)


class ControlPanelCard(QFrame):
    """手机控制按钮面板；跟随当前主设备。"""

    control_requested = Signal(str, str)  # serial, action

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SettingsSection")
        self.serial: str | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        self.hint = QLabel("未连接设备")
        self.hint.setObjectName("Caption")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        grid = QGridLayout()
        grid.setSpacing(8)
        self.buttons: list[QPushButton] = []
        for index, (action, text, icon_name) in enumerate(ACTIONS):
            button = QPushButton(text)
            button.setObjectName("GhostButton")
            button.setIcon(icon(icon_name, COLORS["muted"], 14))
            button.setIconSize(QSize(14, 14))
            button.setCursor(Qt.PointingHandCursor)
            button.setEnabled(False)
            button.clicked.connect(
                lambda checked=False, a=action: self.serial and self.control_requested.emit(self.serial, a)
            )
            grid.addWidget(button, index // 4, index % 4)
            self.buttons.append(button)
        layout.addLayout(grid)

        note = QLabel("提示：电源菜单会调出系统电源选项，可能导致熄屏")
        note.setObjectName("Caption")
        note.setWordWrap(True)
        layout.addWidget(note)

    def set_device(self, serial: str | None, device_name: str = "") -> None:
        self.serial = serial
        enabled = bool(serial)
        for button in self.buttons:
            button.setEnabled(enabled)
        self.hint.setText(
            f"当前设备：{device_name}" if enabled else "连接设备后可在此直接控制手机"
        )


class ScreenControlCard(QFrame):
    """屏幕控制：亮度 / 旋转 / 常亮 / 恢复 / 投屏增强。"""

    screen_op_requested = Signal(str, str, object)  # serial, op, value
    control_requested = Signal(str, str)  # serial, "wakeup"
    screen_off_cast_requested = Signal(str)
    fullscreen_requested = Signal(str)
    screenshot_requested = Signal(str)
    record_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QSlider

        self.setObjectName("SettingsSection")
        self.serial: str | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        brightness_row = QHBoxLayout()
        brightness_row.setSpacing(8)
        self.auto_box = QCheckBox("自动亮度")
        self.auto_box.toggled.connect(self._emit_auto)
        brightness_row.addWidget(self.auto_box)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(1, 255)
        self.slider.setPageStep(16)
        self.slider.setEnabled(False)
        self.slider.sliderReleased.connect(self._emit_brightness)
        brightness_row.addWidget(self.slider, 1)
        self.value_label = QLabel("—")
        self.value_label.setObjectName("InfoValue")
        brightness_row.addWidget(self.value_label)
        restore = QPushButton("恢复原始亮度")
        restore.setObjectName("GhostButton")
        restore.setCursor(Qt.PointingHandCursor)
        restore.clicked.connect(lambda: self._emit_op("restore_all", None))
        brightness_row.addWidget(restore)
        layout.addLayout(brightness_row)

        from PySide6.QtWidgets import QGridLayout

        rotation_row = QGridLayout()
        rotation_row.setHorizontalSpacing(8)
        rotation_row.setVerticalSpacing(6)
        self._rotation_buttons = []
        for index, (mode, text) in enumerate((("auto", "自动旋转"), ("portrait", "竖屏"), ("landscape", "横屏"))):
            button = QPushButton(text)
            button.setObjectName("GhostButton")
            button.setCursor(Qt.PointingHandCursor)
            button.setEnabled(False)
            button.setMinimumHeight(30)
            button.clicked.connect(lambda checked=False, m=mode: self._emit_op("set_rotation", m))
            rotation_row.addWidget(button, 0, index)
            self._rotation_buttons.append(button)
        always = QPushButton("屏幕常亮")
        always.setObjectName("GhostButton")
        always.setCursor(Qt.PointingHandCursor)
        always.setEnabled(False)
        always.setMinimumHeight(30)
        always.clicked.connect(lambda: self._emit_op("always_on", None))
        rotation_row.addWidget(always, 1, 0)
        self._timeout_button = always
        restore_timeout = QPushButton("恢复休眠时间")
        restore_timeout.setObjectName("GhostButton")
        restore_timeout.setCursor(Qt.PointingHandCursor)
        restore_timeout.setEnabled(False)
        restore_timeout.setMinimumHeight(30)
        restore_timeout.clicked.connect(lambda: self._emit_op("restore_timeout", None))
        rotation_row.addWidget(restore_timeout, 1, 1)
        self._restore_timeout_button = restore_timeout
        wakeup = QPushButton("唤醒屏幕")
        wakeup.setObjectName("GhostButton")
        wakeup.setIcon(icon("sun", COLORS["muted"], 14))
        wakeup.setIconSize(QSize(14, 14))
        wakeup.setCursor(Qt.PointingHandCursor)
        wakeup.setEnabled(False)
        wakeup.setMinimumHeight(30)
        wakeup.clicked.connect(
            lambda: self.serial and self.control_requested.emit(self.serial, "wakeup")
        )
        rotation_row.addWidget(wakeup, 1, 2)
        self._wakeup_button = wakeup
        for column in range(3):
            rotation_row.setColumnStretch(column, 1)
        layout.addLayout(rotation_row)

        cast_note = QLabel("投屏增强（需投屏会话运行中）：")
        cast_note.setObjectName("Caption")
        cast_note.setWordWrap(True)
        layout.addWidget(cast_note)
        cast_row = QGridLayout()
        cast_row.setHorizontalSpacing(8)
        cast_row.setVerticalSpacing(6)
        off_cast = QPushButton("熄屏投屏")
        off_cast.setObjectName("GhostButton")
        off_cast.setCursor(Qt.PointingHandCursor)
        off_cast.setEnabled(False)
        off_cast.clicked.connect(lambda: self.serial and self.screen_off_cast_requested.emit(self.serial))
        off_cast.setMinimumHeight(30)
        cast_row.addWidget(off_cast, 0, 0)
        self._off_cast_button = off_cast
        fullscreen = QPushButton("全屏切换")
        fullscreen.setObjectName("GhostButton")
        fullscreen.setCursor(Qt.PointingHandCursor)
        fullscreen.clicked.connect(lambda: self.serial and self.fullscreen_requested.emit(self.serial))
        fullscreen.setMinimumHeight(30)
        cast_row.addWidget(fullscreen, 0, 1)
        screenshot = QPushButton("截图")
        screenshot.setObjectName("GhostButton")
        screenshot.setIcon(icon("copy", COLORS["muted"], 14))
        screenshot.setIconSize(QSize(14, 14))
        screenshot.setCursor(Qt.PointingHandCursor)
        screenshot.setEnabled(False)
        screenshot.clicked.connect(lambda: self.serial and self.screenshot_requested.emit(self.serial))
        screenshot.setMinimumHeight(30)
        cast_row.addWidget(screenshot, 1, 0)
        self._screenshot_button = screenshot
        self.record_button = QPushButton("开始录屏")
        self.record_button.setObjectName("GhostButton")
        self.record_button.setIcon(icon("bolt", COLORS["muted"], 14))
        self.record_button.setIconSize(QSize(14, 14))
        self.record_button.setCursor(Qt.PointingHandCursor)
        self.record_button.setEnabled(False)
        self.record_button.clicked.connect(lambda: self.serial and self.record_requested.emit(self.serial))
        self.record_button.setMinimumHeight(30)
        cast_row.addWidget(self.record_button, 1, 1)
        cast_row.setColumnStretch(0, 1)
        cast_row.setColumnStretch(1, 1)
        layout.addLayout(cast_row)

        self._extra_buttons = [
            self.slider, restore, always, restore_timeout, wakeup,
            off_cast, screenshot, self.record_button,
        ] + self._rotation_buttons

    def _enabled(self) -> bool:
        return bool(self.serial)

    def _emit_op(self, op: str, value) -> None:
        if self.serial:
            self.screen_op_requested.emit(self.serial, op, value)

    def _emit_brightness(self) -> None:
        self._emit_op("set_brightness", self.slider.value())

    def _emit_auto(self, on: bool) -> None:
        if self.serial:
            self.screen_op_requested.emit(
                self.serial, "set_auto_brightness" if on else "get_info", None
            )

    def set_device(self, serial: str | None) -> None:
        self.serial = serial
        enabled = bool(serial)
        for widget in self._extra_buttons:
            widget.setEnabled(enabled)
        if not enabled:
            self.slider.setValue(1)
            self.value_label.setText("—")
            self.auto_box.blockSignals(True)
            self.auto_box.setChecked(False)
            self.auto_box.blockSignals(False)

    def set_screen_info(self, info: dict) -> None:
        self.auto_box.blockSignals(True)
        self.auto_box.setChecked(bool(info.get("auto")))
        self.auto_box.blockSignals(False)
        value = info.get("brightness")
        if value is not None:
            self.slider.blockSignals(True)
            self.slider.setValue(int(value))
            self.slider.blockSignals(False)
            self.slider.setEnabled(True)
            self.value_label.setText(str(value))
        else:
            self.value_label.setText("未知")

    def set_recording(self, recording: bool) -> None:
        self.record_button.setText("停止录屏" if recording else "开始录屏")
