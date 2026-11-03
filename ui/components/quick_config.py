from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ui.components.common import repolish
from ui.components.section import SettingsSection
from ui.components.toggle import ToggleSwitch
from ui.icons import icon
from ui.theme import COLORS


class QuickConfigPanel(QWidget):
    applied = Signal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("QuickPanel")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        self.parameters_section = SettingsSection(
            "投屏参数",
            "设置默认投屏参数；保存后应用到当前已连接设备。",
            "chip",
        )
        root.addWidget(self.parameters_section)
        self._build_parameters()
        self._build_presets()
        self._build_footer()
        root.addStretch(1)

    def _build_parameters(self) -> None:
        body = self.parameters_section.body

        self.param_grid = grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)
        self.param_cells = []
        self._compact_parameters: bool | None = None
        self.codec = self._combo([("自动选择", "auto"), ("H.264", "H.264"), ("H.265", "H.265")])
        self.codec.setMinimumWidth(230)
        self.resolution = self._combo([
            ("原始分辨率", "original"),
            ("自动", "auto"),
            ("1080p", "1080"),
            ("720p", "720"),
            ("1440p", "1440"),
            ("2560", "2560"),
        ])
        self.fps = self._combo([("不限制 (0)", 0), ("30 FPS", 30), ("60 FPS", 60), ("90 FPS", 90), ("120 FPS", 120)])
        self.fps.setMinimumWidth(230)
        self.fps.setToolTip("超过设备刷新率或编码能力会掉帧；建议 0（不限）或 60。")
        self.bitrate = QSpinBox()
        self.bitrate.setMinimumWidth(230)
        self.bitrate.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.bitrate.setRange(1, 128)
        self.bitrate.setSuffix(" Mbps")
        self.bitrate.setValue(8)
        self.param_cells = [
            (self._field("编码格式", self.codec), 0, 0),
            (self._field("分辨率", self.resolution), 0, 1),
            (self._field("最大帧率", self.fps), 1, 0),
            (self._field("视频码率", self.bitrate), 1, 1),
        ]
        self.resolution.setMinimumWidth(230)
        self._layout_parameters(False)
        body.addLayout(grid)

        audio_row = QHBoxLayout()
        audio_row.setSpacing(10)
        audio_column = QVBoxLayout()
        audio_column.setSpacing(2)
        audio_title = QLabel("音频转发")
        audio_title.setObjectName("InfoValue")
        audio_hint = QLabel("将手机媒体音频转发到电脑；关闭后仅投屏画面")
        audio_hint.setObjectName("Caption")
        audio_column.addWidget(audio_title)
        audio_column.addWidget(audio_hint)
        self.audio = ToggleSwitch(True)
        audio_row.addLayout(audio_column, 1)
        audio_row.addWidget(self.audio, 0, Qt.AlignVCenter)
        body.addLayout(audio_row)

        self.status_label = QLabel("")
        self.status_label.setObjectName("ConfigStatus")
        body.addWidget(self.status_label)

    def _build_presets(self) -> None:
        self.preset_section = SettingsSection(
            "快捷预设",
            "选择常用场景后参数会自动填入上方投屏参数。",
            "bolt",
        )
        root_layout = self.layout()
        root_layout.addWidget(self.preset_section)
        body = self.preset_section.body
        presets = (
            ("流畅优先", "自动编码 · 原始分辨率 · 不限帧率", {"video_codec": "auto", "resolution": "original", "fps": 0, "bitrate_mbps": 8, "audio": True}),
            ("均衡模式", "自动编码 · 1080p · 60 FPS · 12 Mbps", {"video_codec": "auto", "resolution": "1080", "fps": 60, "bitrate_mbps": 12, "audio": True}),
            ("清晰优先", "H.265 · 原始分辨率 · 60 FPS · 20 Mbps", {"video_codec": "H.265", "resolution": "original", "fps": 60, "bitrate_mbps": 20, "audio": True}),
        )
        for title, hint, params in presets:
            row = QHBoxLayout()
            row.setSpacing(12)
            text = QVBoxLayout()
            text.setSpacing(2)
            name = QLabel(title)
            name.setObjectName("InfoValue")
            note = QLabel(hint)
            note.setObjectName("Caption")
            text.addWidget(name)
            text.addWidget(note)
            use = QPushButton("使用")
            use.setObjectName("GhostButton")
            use.setCursor(Qt.PointingHandCursor)
            use.clicked.connect(lambda checked=False, p=params: self._use_preset(p))
            row.addLayout(text, 1)
            row.addWidget(use)
            body.addLayout(row)
            divider = QFrame()
            divider.setObjectName("Divider")
            divider.setFixedHeight(1)
            body.addWidget(divider)
        note = QLabel("使用预设后仍需点击“保存并应用”才会写入设备配置。")
        note.setObjectName("Caption")
        note.setWordWrap(True)
        body.addWidget(note)

    def _build_footer(self) -> None:
        root_layout = self.layout()
        footer = QHBoxLayout()
        footer.setSpacing(10)
        reset = QPushButton("恢复性能默认")
        reset.setObjectName("LinkButton")
        reset.setCursor(Qt.PointingHandCursor)
        reset.clicked.connect(self.reset_to_performance_defaults)
        footer.addWidget(reset)
        footer.addStretch(1)
        apply_button = QPushButton("保存并应用")
        apply_button.setObjectName("PrimaryButton")
        apply_button.setIcon(icon("check", "#FFFFFF", 15))
        apply_button.setIconSize(QSize(15, 15))
        apply_button.setCursor(Qt.PointingHandCursor)
        apply_button.clicked.connect(self._apply)
        footer.addWidget(apply_button)
        root_layout.addLayout(footer)

    @staticmethod
    def _combo(items) -> QComboBox:
        combo = QComboBox()
        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        for label, value in items:
            combo.addItem(label, value)
        return combo

    @staticmethod
    def _field(label: str, widget: QWidget) -> QWidget:
        cell = QWidget()
        layout = QVBoxLayout(cell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        text = QLabel(label)
        text.setObjectName("InfoLabel")
        layout.addWidget(text)
        layout.addWidget(widget)
        return cell

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._layout_parameters(self.width() < 780)

    def _layout_parameters(self, compact: bool) -> None:
        if compact == self._compact_parameters or not hasattr(self, "param_grid"):
            return
        self._compact_parameters = compact
        for cell, row, column in self.param_cells:
            self.param_grid.removeWidget(cell)
        if compact:
            for index, (cell, _row, _column) in enumerate(self.param_cells):
                self.param_grid.addWidget(cell, index, 0)
            self.param_grid.setColumnStretch(0, 1)
            self.param_grid.setColumnStretch(1, 0)
        else:
            for cell, row, column in self.param_cells:
                self.param_grid.addWidget(cell, row, column)
            self.param_grid.setColumnStretch(0, 1)
            self.param_grid.setColumnStretch(1, 1)

    def show_tab(self, index: int) -> None:
        # Compatibility for older callers. Settings-style pages show all sections.
        return

    def _use_preset(self, parameters: dict) -> None:
        self.load(parameters)
        self._set_status("预设已载入，点击“保存并应用”后生效", "muted")

    def load(self, parameters: dict) -> None:
        self._set_combo_data(self.codec, parameters.get("video_codec", "auto"))
        resolution = str(parameters.get("resolution", "original")).lower().replace("p", "")
        if resolution not in {"original", "auto", "720", "1080", "1440", "2560"}:
            resolution = "original"
        self._set_combo_data(self.resolution, resolution)
        self._set_combo_data(self.fps, int(parameters.get("fps", 0)))
        self.bitrate.setValue(int(parameters.get("bitrate_mbps", 8)))
        self.audio.setChecked(bool(parameters.get("audio", True)))

    def parameters(self) -> dict:
        return {
            "video_codec": self.codec.currentData(),
            "resolution": self.resolution.currentData(),
            "fps": int(self.fps.currentData()),
            "bitrate_mbps": self.bitrate.value(),
            "audio": self.audio.isChecked(),
        }

    def reset_to_performance_defaults(self) -> None:
        self.load({"video_codec": "auto", "resolution": "original", "fps": 0, "bitrate_mbps": 8, "audio": True})
        self._set_status("已恢复性能优先默认值，点击保存后生效", "muted")

    def _set_status(self, text: str, tone: str = "muted") -> None:
        self.status_label.setText(text)
        self.status_label.setProperty("tone", tone)
        repolish(self.status_label)

    def show_saved(self) -> None:
        self._set_status("已保存并应用", "success")

    def _apply(self) -> None:
        self.applied.emit(self.parameters())

    @staticmethod
    def _set_combo_data(combo: QComboBox, value) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)





