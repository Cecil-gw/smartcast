
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from ui.components.quick_config import QuickConfigPanel


class CastSettingsPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("SettingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        root.addWidget(scroll)

        page = QWidget()
        page.setObjectName("CastSettingsContent")
        scroll.setWidget(page)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(20, 16, 20, 16)
        page_layout.setSpacing(14)

        title_column = QVBoxLayout()
        title_column.setSpacing(3)
        title = QLabel("投屏设置")
        title.setObjectName("PageTitle")
        subtitle = QLabel("设置默认投屏参数，保存后应用到已连接设备")
        subtitle.setObjectName("PageSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        page_layout.addLayout(title_column)

        content = QWidget()
        content.setMinimumWidth(560)
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self.quick_config = QuickConfigPanel()
        self.quick_config.setMinimumWidth(0)
        self.quick_config.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.quick_config)
        page_layout.addWidget(content)
        page_layout.addStretch(1)

        self.content = content

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "content"):
            self.content.setMaximumWidth(max(420, int(self.width() * 0.7)))

    def load_defaults(self, parameters: dict) -> None:
        self.quick_config.load(parameters)
