
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ui.components.square_button import SquareActionButton
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


class ResponsiveButtonGrid(QWidget):
    """按宽度自动换行的按钮网格。

    使用逐行 QHBoxLayout + 末尾弹簧，保证按钮间距恒定为 4px，
    窗口放大会留白在右侧而不是把按钮拉开。
    """

    def __init__(self, cell: int = 64, h_gap: int = 15, v_gap: int = 4,
                 max_columns: int = 4, parent=None) -> None:
        super().__init__(parent)
        self.cell = cell
        self.h_gap = h_gap
        self.v_gap = v_gap
        self.max_columns = max_columns
        self._widgets: list = []
        self._columns = 0
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(v_gap)
        self._rows: list[QHBoxLayout] = []

    def set_widgets(self, widgets: list) -> None:
        self._widgets = list(widgets)
        self._relayout(force=True)

    def relayout_for_width(self, width: int) -> None:
        self._relayout(available=width)

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            sub = item.layout()
            if sub is not None:
                while sub.count():
                    sub.takeAt(0)
                sub.deleteLater()
        self._rows.clear()

    def _relayout(self, force: bool = False, available: int | None = None) -> None:
        if not self._widgets:
            return
        if available is None:
            available = self.width() or 400
        columns = max(1, min(self.max_columns, len(self._widgets),
                             max(1, (available + self.h_gap) // (self.cell + self.h_gap))))
        if not force and columns == self._columns:
            return
        self._columns = columns
        self._clear()
        for start in range(0, len(self._widgets), columns):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(self.h_gap)
            for widget in self._widgets[start:start + columns]:
                row.addWidget(widget)
            row.addStretch(1)
            self._layout.addLayout(row)
            self._rows.append(row)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout(available=self.width())


class ControlPanelCard(QFrame):
    """手机控制：方形图标按钮，自适应换行。"""

    control_requested = Signal(str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SettingsSection")
        self.serial: str | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        self.hint = QLabel("未连接设备")
        self.hint.setObjectName("Caption")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        self.buttons: list[SquareActionButton] = []
        for action, text, icon_name in ACTIONS:
            button = SquareActionButton(text, icon_name)
            button.clicked.connect(
                lambda checked=False, a=action: self.serial and self.control_requested.emit(self.serial, a)
            )
            self.buttons.append(button)

        self.grid = ResponsiveButtonGrid(cell=64, h_gap=30, v_gap=4, max_columns=4)
        self.grid.set_widgets(self.buttons)
        layout.addWidget(self.grid, 0, Qt.AlignLeft)

        note = QLabel("提示：电源菜单会调出系统电源选项，可能导致熄屏")
        note.setObjectName("Caption")
        note.setWordWrap(True)
        layout.addWidget(note)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.grid.relayout_for_width(self.width() - 32)

    def set_device(self, serial: str | None, device_name: str = "") -> None:
        self.serial = serial
        enabled = bool(serial)
        for button in self.buttons:
            button.setEnabled(enabled)
        self.hint.setText(
            f"当前设备：{device_name}" if enabled else "连接设备后可在此直接控制手机"
        )


class ScreenControlCard(QFrame):
    """屏幕控制：亮度滑杆 + 方形操作按钮网格。"""

    screen_op_requested = Signal(str, str, object)
    control_requested = Signal(str, str)
    screen_off_cast_requested = Signal(str)
    fullscreen_requested = Signal(str)
    screenshot_requested = Signal(str)
    record_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SettingsSection")
        self.serial: str | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # ---- 亮度 ----
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
        self.value_label.setMinimumWidth(30)
        brightness_row.addWidget(self.value_label)
        layout.addLayout(brightness_row)

        # ---- 操作按钮（图标在上、文字在下） ----
        self._rotation_buttons: list[SquareActionButton] = []
        for mode, text, icon_name in (
            ("auto", "自动旋转", "refresh"),
            ("portrait", "竖屏", "phone"),
            ("landscape", "横屏", "screen"),
        ):
            button = SquareActionButton(text, icon_name)
            button.clicked.connect(lambda checked=False, m=mode: self._emit_op("set_rotation", m))
            self._rotation_buttons.append(button)

        self._always_button = SquareActionButton("屏幕常亮", "sun")
        self._always_button.clicked.connect(lambda: self._emit_op("always_on", None))
        self._wakeup_button = SquareActionButton("唤醒屏幕", "sun")
        self._wakeup_button.clicked.connect(
            lambda: self.serial and self.control_requested.emit(self.serial, "wakeup")
        )
        self._off_cast_button = SquareActionButton("熄屏投屏", "screen")
        self._off_cast_button.clicked.connect(
            lambda: self.serial and self.screen_off_cast_requested.emit(self.serial)
        )
        self._fullscreen_button = SquareActionButton("全屏切换", "monitor")
        self._fullscreen_button.clicked.connect(
            lambda: self.serial and self.fullscreen_requested.emit(self.serial)
        )
        self._screenshot_button = SquareActionButton("截图", "copy")
        self._screenshot_button.clicked.connect(
            lambda: self.serial and self.screenshot_requested.emit(self.serial)
        )
        self.record_button = SquareActionButton("开始录屏", "bolt")
        self.record_button.clicked.connect(
            lambda: self.serial and self.record_requested.emit(self.serial)
        )
        self._restore_button = SquareActionButton("恢复亮度", "refresh")
        self._restore_button.clicked.connect(lambda: self._emit_op("restore_all", None))

        self._action_widgets = (
            self._rotation_buttons
            + [
                self._always_button,
                self._wakeup_button,
                self._off_cast_button,
                self._fullscreen_button,
                self._screenshot_button,
                self.record_button,
                self._restore_button,
            ]
        )
        self.grid = ResponsiveButtonGrid(cell=64, h_gap=30, v_gap=4, max_columns=5)
        self.grid.set_widgets(self._action_widgets)
        layout.addWidget(self.grid, 0, Qt.AlignLeft)

        self._extra_widgets = list(self._action_widgets) + [self.slider]

    # ------------------------------------------------------------------
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.grid.relayout_for_width(self.width() - 32)

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
        for widget in self._extra_widgets:
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
