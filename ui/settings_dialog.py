from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.device_info import DeviceInfo
from core.parameter_optimizer import recommend_bitrate
from ui.components.toggle import ToggleSwitch
from utils.config_manager import ConfigManager


class SettingsDialog(QDialog):
    """Compatibility dialog; the full settings experience lives in SettingsPage."""

    def __init__(self, config: ConfigManager, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("SmartCast 设置")
        self.resize(620, 420)
        self.config = config
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)
        title = QLabel("SmartCast 设置")
        title.setObjectName("PageTitle")
        subtitle = QLabel("完整的分类设置请在主窗口右上角打开设置页。")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        card = QFrame()
        card.setObjectName("Card")
        form = QFormLayout(card)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(10)
        self.adb_edit = QLineEdit(config.settings.get("adb_path", ""))
        self.scrcpy_edit = QLineEdit(config.settings.get("scrcpy_path", ""))
        self.interval = QSpinBox()
        self.interval.setRange(1, 60)
        self.interval.setValue(int(config.settings.get("scan_interval", 2)))
        self.casting_interval = QSpinBox()
        self.casting_interval.setRange(5, 120)
        self.casting_interval.setValue(int(config.settings.get("casting_scan_interval", 15)))
        self.auto_scan = ToggleSwitch(bool(config.settings.get("auto_scan", True)))
        self.adb_edit.setPlaceholderText("留空则使用内置 resources/adb/adb.exe")
        self.scrcpy_edit.setPlaceholderText("留空则使用内置 resources/scrcpy/scrcpy.exe")
        form.addRow("ADB 路径", self.adb_edit)
        form.addRow("scrcpy 路径", self.scrcpy_edit)
        form.addRow("空闲扫描间隔（秒）", self.interval)
        form.addRow("投屏扫描间隔（秒）", self.casting_interval)
        form.addRow("自动扫描", self.auto_scan)
        layout.addWidget(card)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("保存")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save(self) -> None:
        self.config.settings.update({
            "adb_path": self.adb_edit.text().strip(),
            "scrcpy_path": self.scrcpy_edit.text().strip(),
            "scan_interval": self.interval.value(),
            "casting_scan_interval": self.casting_interval.value(),
            "auto_scan": self.auto_scan.isChecked(),
        })
        self.config.save()
        self.accept()


class DeviceSettingsDialog(QDialog):
    def __init__(self, parameters: dict, codecs=None, parent=None, *, device: DeviceInfo | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("设备投屏设置")
        self.resize(560, 520)
        self._codecs = codecs or []
        self._device = device
        self._recommended_mbps: int | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)
        title = QLabel("设备投屏设置")
        title.setObjectName("PageTitle")
        subtitle = QLabel("参数只对本次选择的设备生效，保存后下次投屏使用。")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        card = QFrame()
        card.setObjectName("Card")
        form = QFormLayout(card)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(10)
        available = {item.codec for item in (codecs or [])}
        codec_options = ["auto"]
        codec_options += [codec for codec in ("H.265", "H.264") if not available or codec in available]
        if len(codec_options) == 1:
            codec_options += ["H.264"]
        self.codec = QComboBox()
        self.codec.addItems(codec_options)
        current_codec = str(parameters.get("video_codec", "auto"))
        self.codec.setCurrentText(current_codec if current_codec in codec_options else "auto")
        self.resolution = QComboBox()
        self.resolution.addItems(["auto", "original", "720", "1080", "1440", "2560"])
        current_resolution = str(parameters.get("resolution", "original")).lower().replace("p", "")
        if current_resolution not in {"auto", "original", "720", "1080", "1440", "2560"}:
            current_resolution = "original"
        self.resolution.setCurrentText(current_resolution)
        self.fps = QComboBox()
        self.fps.addItems(["0", "30", "60", "90", "120"])
        self.fps.setCurrentText(str(parameters.get("fps", 0)))
        if self.fps.currentIndex() < 0:
            self.fps.setCurrentIndex(0)
        self.bitrate = QSpinBox()
        self.bitrate.setRange(1, 128)
        self.bitrate.setSuffix(" Mbps")
        self.bitrate.setValue(int(parameters.get("bitrate_mbps", 8)))
        self.audio = ToggleSwitch(bool(parameters.get("audio", True)))
        form.addRow("视频编码", self.codec)
        form.addRow("分辨率上限（长边）", self.resolution)
        form.addRow("帧率（0 为不限，推荐）", self.fps)
        form.addRow("视频码率", self.bitrate)
        recommend_widget = QWidget()
        recommend_layout = QHBoxLayout(recommend_widget)
        recommend_layout.setContentsMargins(0, 0, 0, 0)
        recommend_layout.setSpacing(8)
        self.recommendation_label = QLabel("连接设备后显示推荐码率")
        self.recommendation_label.setObjectName("Caption")
        self.recommendation_label.setWordWrap(True)
        self.recommend_button = QPushButton("使用推荐")
        self.recommend_button.setObjectName("LinkButton")
        self.recommend_button.setEnabled(False)
        self.recommend_button.clicked.connect(self._use_recommended_bitrate)
        recommend_layout.addWidget(self.recommendation_label, 1)
        recommend_layout.addWidget(self.recommend_button, 0)
        form.addRow("推荐码率", recommend_widget)
        form.addRow("音频转发", self.audio)
        hint = QLabel("编码器选项来自当前设备的实际检测结果。帧率 0 为不限，过高会掉帧。")
        hint.setObjectName("Caption")
        form.addRow(hint)
        layout.addWidget(card)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("保存")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.codec.currentIndexChanged.connect(self._refresh_recommendation)
        self.resolution.currentIndexChanged.connect(self._refresh_recommendation)
        self.bitrate.valueChanged.connect(self._refresh_recommendation)
        self._refresh_recommendation()

    def _refresh_recommendation(self) -> None:
        if self._device is None:
            self.recommendation_label.setText("连接设备后显示推荐码率")
            self.recommend_button.setEnabled(False)
            return
        recommendation = recommend_bitrate(
            self._device,
            self._codecs,
            self.codec.currentText(),
            self.resolution.currentText(),
        )
        if recommendation is None:
            self._recommended_mbps = None
            self.recommendation_label.setText("当前编码/分辨率在该设备上不可用")
            self.recommend_button.setEnabled(False)
            return
        self._recommended_mbps = recommendation.mbps
        text = f"{recommendation.summary}：{recommendation.detail}"
        if self.bitrate.value() < recommendation.mbps:
            text += "。当前码率偏低，动态画面可能模糊。"
        else:
            text += "。当前码率已满足推荐。"
        self.recommendation_label.setText(text)
        self.recommend_button.setText(f"使用推荐（{recommendation.mbps} Mbps）")
        self.recommend_button.setEnabled(self.bitrate.value() != recommendation.mbps)

    def _use_recommended_bitrate(self) -> None:
        if self._recommended_mbps is not None:
            self.bitrate.setValue(self._recommended_mbps)

    def parameters(self) -> dict:
        return {
            "video_codec": self.codec.currentText(),
            "resolution": self.resolution.currentText(),
            "fps": int(self.fps.currentText()),
            "bitrate_mbps": self.bitrate.value(),
            "audio": self.audio.isChecked(),
        }
