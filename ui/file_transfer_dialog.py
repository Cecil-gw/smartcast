
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QDialog,
)

from ui.icons import icon
from ui.theme import COLORS


DEFAULT_REMOTE_DIR = "/sdcard/Download/SmartCast"


class FileTransferDialog(QDialog):
    """文件传输：电脑 → 手机 / 手机 → 电脑。"""

    push_requested = Signal(list)      # 本地文件列表
    pull_requested = Signal(str)       # 手机路径

    def __init__(self, device_name: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("文件传输")
        self.setMinimumWidth(460)
        self._device_name = device_name

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        title = QLabel("文件传输")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        subtitle = QLabel(f"当前设备：{device_name}" if device_name else "未选择设备")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(subtitle)

        # ---- 电脑 → 手机 ----
        send_card = QFrame()
        send_card.setObjectName("SettingsSection")
        send_layout = QVBoxLayout(send_card)
        send_layout.setContentsMargins(16, 14, 16, 14)
        send_layout.setSpacing(8)
        send_title = QLabel("发送到手机")
        send_title.setObjectName("InfoValue")
        send_layout.addWidget(send_title)
        send_desc = QLabel(f"文件会保存到手机的 {DEFAULT_REMOTE_DIR}")
        send_desc.setObjectName("Caption")
        send_desc.setWordWrap(True)
        send_layout.addWidget(send_desc)
        send_row = QHBoxLayout()
        send_row.addStretch()
        choose_btn = QPushButton("选择文件并发送…")
        choose_btn.setObjectName("PrimaryButton")
        choose_btn.setIcon(icon("export", "#FFFFFF", 14))
        choose_btn.setIconSize(QSize(14, 14))
        choose_btn.setCursor(Qt.PointingHandCursor)
        choose_btn.clicked.connect(self._choose_and_push)
        send_row.addWidget(choose_btn)
        send_layout.addLayout(send_row)
        layout.addWidget(send_card)

        # ---- 手机 → 电脑 ----
        pull_card = QFrame()
        pull_card.setObjectName("SettingsSection")
        pull_layout = QVBoxLayout(pull_card)
        pull_layout.setContentsMargins(16, 14, 16, 14)
        pull_layout.setSpacing(8)
        pull_title = QLabel("从手机取回")
        pull_title.setObjectName("InfoValue")
        pull_layout.addWidget(pull_title)
        pull_desc = QLabel("填写手机上的文件或文件夹路径，例如 /sdcard/Download/SmartCast")
        pull_desc.setObjectName("Caption")
        pull_desc.setWordWrap(True)
        pull_layout.addWidget(pull_desc)
        self.path_edit = QLineEdit(DEFAULT_REMOTE_DIR)
        self.path_edit.setPlaceholderText("/sdcard/DCIM/Camera/IMG_0001.jpg")
        pull_layout.addWidget(self.path_edit)
        pull_row = QHBoxLayout()
        pull_row.addStretch()
        pull_btn = QPushButton("选择保存目录并取回…")
        pull_btn.setObjectName("PrimaryButton")
        pull_btn.setIcon(icon("folder", "#FFFFFF", 14))
        pull_btn.setIconSize(QSize(14, 14))
        pull_btn.setCursor(Qt.PointingHandCursor)
        pull_btn.clicked.connect(self._choose_and_pull)
        pull_row.addWidget(pull_btn)
        pull_layout.addLayout(pull_row)
        layout.addWidget(pull_card)

        self.status_label = QLabel("")
        self.status_label.setObjectName("Caption")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        actions = QHBoxLayout()
        actions.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.reject)
        actions.addWidget(close_btn)
        layout.addLayout(actions)

    # ------------------------------------------------------------------
    def _choose_and_push(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "选择要发送到手机的文件")
        if files:
            self.push_requested.emit(files)

    def _choose_and_pull(self) -> None:
        remote = self.path_edit.text().strip()
        if not remote:
            self.show_status("请填写手机上的文件路径", error=True)
            return
        target = QFileDialog.getExistingDirectory(self, "选择保存到电脑的目录")
        if target:
            self.pull_requested.emit(f"{remote}|{target}")

    def show_status(self, message: str, error: bool = False) -> None:
        self.status_label.setText(("⚠ " if error else "✓ ") + message)
        self.status_label.setStyleSheet(
            f"color: {COLORS['error'] if error else COLORS['success']};"
        )
