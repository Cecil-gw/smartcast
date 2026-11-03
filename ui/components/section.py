from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from ui.icons import icon
from ui.theme import COLORS


class SettingsSection(QFrame):
    def __init__(self, title: str, description: str, icon_name: str = "settings", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SettingsSection")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(13)
        header = QHBoxLayout()
        header.setSpacing(10)
        icon_tile = QFrame()
        icon_tile.setObjectName("IconBadge")
        icon_tile.setFixedSize(32, 32)
        icon_layout = QHBoxLayout(icon_tile)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel()
        icon_label.setPixmap(icon(icon_name, COLORS["accent_hover"], 17).pixmap(17, 17))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(icon_label)
        header.addWidget(icon_tile)
        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        description_label = QLabel(description)
        description_label.setObjectName("SectionDescription")
        description_label.setWordWrap(True)
        title_column.addWidget(title_label)
        title_column.addWidget(description_label)
        header.addLayout(title_column, 1)
        outer.addLayout(header)
        divider = QFrame()
        divider.setObjectName("Divider")
        divider.setFixedHeight(1)
        outer.addWidget(divider)
        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        outer.addLayout(self.body)
