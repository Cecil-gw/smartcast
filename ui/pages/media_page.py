
from __future__ import annotations

import os
import subprocess
from datetime import datetime

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.media_manager import MediaRecord
from ui.components.common import StatusPill
from ui.icons import icon
from ui.theme import COLORS


class MediaRecordRow(QFrame):
    open_requested = Signal(object)
    open_folder_requested = Signal(object)
    delete_record_requested = Signal(object)
    delete_file_requested = Signal(object)

    def __init__(self, record: MediaRecord, parent=None) -> None:
        super().__init__(parent)
        self.record = record
        self.setObjectName("DeviceCard")
        # 文字在上、操作按钮在下：窗口变窄时文字自动换行，不会被按钮挤压裁切
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 10, 16, 10)
        outer.setSpacing(8)

        row = QHBoxLayout()
        row.setSpacing(10)
        icon_name = "screen" if record.media_type == "screenshot" else "bolt"
        icon_label = QLabel()
        icon_label.setPixmap(icon(icon_name, COLORS["accent_hover"], 20).pixmap(20, 20))
        row.addWidget(icon_label, 0, Qt.AlignTop)

        info = QVBoxLayout()
        info.setSpacing(2)
        name = QLabel(record.file_name)
        name.setObjectName("InfoValue")
        name.setWordWrap(True)
        exists = record.exists()
        detail = f"{record.device_name} · {record.serial} · {record.created} · {record.size / 1024:.0f} KB"
        status_text = "" if exists else " · 文件不存在"
        detail += status_text
        detail_label = QLabel(detail)
        detail_label.setObjectName("Caption")
        detail_label.setWordWrap(True)
        info.addWidget(name)
        info.addWidget(detail_label)
        row.addLayout(info, 1)

        self.status_pill = StatusPill("存在" if exists else "缺失", "success" if exists else "warning")
        row.addWidget(self.status_pill, 0, Qt.AlignTop)
        outer.addLayout(row)

        actions = QHBoxLayout()
        actions.setSpacing(6)
        actions.addStretch(1)
        for text, icon_name2, cb in (
            ("打开", "screen", self.open_requested),
            ("打开目录", "folder", self.open_folder_requested),
            ("删除记录", "trash", self.delete_record_requested),
            ("删除文件", "trash", self.delete_file_requested),
        ):
            button = QPushButton(text)
            button.setObjectName("GhostButton")
            button.setIcon(icon(icon_name2, COLORS["muted"], 13))
            button.setIconSize(QSize(13, 13))
            button.setCursor(Qt.PointingHandCursor)
            button.setEnabled(exists or cb is not self.delete_file_requested)
            button.clicked.connect(lambda checked=False, c=cb, r=record: c.emit(r))
            actions.addWidget(button)
        outer.addLayout(actions)


class MediaPage(QWidget):
    open_file_requested = Signal(object)
    open_folder_requested = Signal(object)
    delete_record_requested = Signal(object)
    delete_file_requested = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._records: list[MediaRecord] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        header_row = QHBoxLayout()
        title_column = QVBoxLayout()
        title_column.setSpacing(3)
        title = QLabel("媒体管理")
        title.setObjectName("PageTitle")
        subtitle = QLabel("截图与录屏的历史记录，按设备和类型筛选")
        subtitle.setObjectName("PageSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        header_row.addLayout(title_column, 1)

        self.filter_device = QComboBox()
        self.filter_device.setMinimumWidth(160)
        self.filter_type = QComboBox()
        self.filter_type.addItems(["全部类型", "截图", "录屏"])
        self.filter_device.currentIndexChanged.connect(self.refresh)
        self.filter_type.currentIndexChanged.connect(self.refresh)
        header_row.addWidget(self.filter_device)
        header_row.addWidget(self.filter_type)
        root.addLayout(header_row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.host = QWidget()
        self.rows_layout = QVBoxLayout(self.host)
        self.rows_layout.setContentsMargins(0, 0, 4, 0)
        self.rows_layout.setSpacing(10)
        self.empty_label = QLabel("暂无媒体记录。在设备详情页使用截图/录屏功能。")
        self.empty_label.setObjectName("Caption")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.rows_layout.addWidget(self.empty_label)
        self.rows_layout.addStretch(1)
        self.scroll.setWidget(self.host)
        root.addWidget(self.scroll, 1)

        self.rows: dict[str, MediaRecordRow] = {}

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.scroll.setMaximumWidth(max(360, int(self.width() * 0.7)))

    def set_records(self, records: list[MediaRecord]) -> None:
        self._records = records
        devices = sorted({r.device_name for r in records})
        current = self.filter_device.currentText()
        self.filter_device.blockSignals(True)
        self.filter_device.clear()
        self.filter_device.addItem("全部设备")
        self.filter_device.addItems(devices)
        if current in devices:
            self.filter_device.setCurrentText(current)
        self.filter_device.blockSignals(False)
        self.refresh()

    def refresh(self) -> None:
        for row in self.rows.values():
            self.rows_layout.removeWidget(row)
            row.deleteLater()
        self.rows.clear()

        type_index = self.filter_type.currentIndex()
        type_filter = {0: None, 1: "screenshot", 2: "recording"}.get(type_index)
        device_filter = None if self.filter_device.currentIndex() <= 0 else self.filter_device.currentText()

        records = sorted(
            (r for r in self._records
             if (type_filter is None or r.media_type == type_filter)
             and (device_filter is None or r.device_name == device_filter)),
            key=lambda r: r.created,
            reverse=True,
        )
        self.empty_label.setVisible(not records)
        for record in records:
            key = record.path + "|" + record.created
            row = MediaRecordRow(record)
            row.open_requested.connect(self.open_file_requested)
            row.open_folder_requested.connect(self.open_folder_requested)
            row.delete_record_requested.connect(self.delete_record_requested)
            row.delete_file_requested.connect(self.delete_file_requested)
            self.rows[key] = row
            self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)
