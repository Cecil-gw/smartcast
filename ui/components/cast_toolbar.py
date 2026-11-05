
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ui.icons import icon
from ui.theme import COLORS


class CastToolBar(QWidget):
    """Compact control bar that floats under a scrcpy window."""

    action_requested = Signal(str, str)  # serial, action
    screen_op_requested = Signal(str, str, object)
    fullscreen_requested = Signal(str)
    screenshot_requested = Signal(str)
    record_requested = Signal(str)

    BUTTONS = (
        ("back", "返回", "back"),
        ("home", "主页", "home"),
        ("recent", "多任务", "list"),
        ("volume_up", "音量+", "bolt"),
        ("volume_down", "音量-", "moon"),
        ("mute", "静音", "close"),
        ("wakeup", "唤醒", "sun"),
        ("lock", "锁屏", "screen"),
    )

    def __init__(self, serial: str, recording: bool = False, parent=None) -> None:
        super().__init__(
            parent,
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus,
        )
        # Do not activate/hide when the user clicks the scrcpy window.
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.serial = serial
        self.setObjectName("CastToolBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            f"#CastToolBar {{ background: {COLORS['surface']};"
            f" border: 1px solid {COLORS['border']}; border-radius: 8px; }}"
        )

        from PySide6.QtWidgets import QCheckBox, QSlider

        column = QVBoxLayout(self)
        column.setContentsMargins(8, 5, 8, 5)
        column.setSpacing(4)

        # row 1: keys + cast enhancements
        row1 = QHBoxLayout()
        row1.setSpacing(4)
        label = QLabel("控制")
        label.setObjectName("Caption")
        row1.addWidget(label)

        for action, text, icon_name in self.BUTTONS:
            row1.addWidget(self._button(action, text, icon_name,
                                        lambda checked=False, a=action: self.action_requested.emit(self.serial, a)))

        fullscreen = self._button("fullscreen", "全屏", "screen",
                                  lambda checked=False: self.fullscreen_requested.emit(self.serial))
        fullscreen.setMinimumWidth(56)
        row1.addWidget(fullscreen)
        record_text = "停止录屏" if recording else "录屏"
        self.record_button = self._button("record", record_text, "bolt",
                                          lambda checked=False: self.record_requested.emit(self.serial))
        self.record_button.setMinimumWidth(84)
        row1.addWidget(self.record_button)
        screenshot = self._button("screenshot", "截图", "copy",
                                  lambda checked=False: self.screenshot_requested.emit(self.serial))
        screenshot.setMinimumWidth(64)
        row1.addWidget(screenshot)
        column.addLayout(row1)

        # row 2: screen controls
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        screen_label = QLabel("屏幕")
        screen_label.setObjectName("Caption")
        row2.addWidget(screen_label)

        self.auto_box = QCheckBox("自动")
        self.auto_box.toggled.connect(
            lambda on: self.screen_op_requested.emit(
                self.serial, "set_auto_brightness" if on else "get_info", None)
        )
        row2.addWidget(self.auto_box)

        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(1, 255)
        self.brightness_slider.setPageStep(16)
        self.brightness_slider.setFixedWidth(150)
        self.brightness_slider.sliderReleased.connect(
            lambda: self.screen_op_requested.emit(
                self.serial, "set_brightness", self.brightness_slider.value())
        )
        row2.addWidget(self.brightness_slider)

        self.brightness_value = QLabel("—")
        self.brightness_value.setObjectName("Caption")
        self.brightness_value.setFixedWidth(28)
        row2.addWidget(self.brightness_value)

        for mode, text in (("auto", "自动旋转"), ("portrait", "竖屏"), ("landscape", "横屏")):
            button = self._button(f"rot_{mode}", text, "refresh",
                                  lambda checked=False, m=mode: self.screen_op_requested.emit(
                                      self.serial, "set_rotation", m))
            button.setMinimumWidth(78)
            row2.addWidget(button)

        always = self._button("always_on", "常亮", "sun",
                              lambda checked=False: self.screen_op_requested.emit(self.serial, "always_on", None))
        always.setMinimumWidth(64)
        row2.addWidget(always)
        restore = self._button("restore_all", "恢复", "refresh",
                               lambda checked=False: self.screen_op_requested.emit(self.serial, "restore_all", None))
        restore.setMinimumWidth(64)
        restore.setToolTip("恢复全部原始屏幕设置")
        row2.addWidget(restore)
        column.addLayout(row2)

        self.setMinimumSize(len(self.BUTTONS) * 38 + 420, 84)
        self.adjustSize()
        self.setWindowModality(Qt.NonModal)

    def _button(self, action: str, text: str, icon_name: str, handler) -> QPushButton:
        from PySide6.QtWidgets import QPushButton

        button = QPushButton(text)
        button.setObjectName("GhostButton")
        button.setIcon(icon(icon_name, COLORS["muted"], 13))
        button.setIconSize(QSize(13, 13))
        button.setCursor(Qt.PointingHandCursor)
        button.setFixedWidth(38 if len(text) <= 2 else 62)
        button.clicked.connect(handler)
        return button

    def set_recording(self, recording: bool) -> None:
        self.record_button.setText("停止录屏" if recording else "录屏")

    def set_screen_info(self, info: dict) -> None:
        self.auto_box.blockSignals(True)
        self.auto_box.setChecked(bool(info.get("auto")))
        self.auto_box.blockSignals(False)
        value = info.get("brightness")
        if value is not None:
            self.brightness_slider.blockSignals(True)
            self.brightness_slider.setValue(int(value))
            self.brightness_slider.blockSignals(False)
            self.brightness_value.setText(str(value))
