
from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QDrag, QPainter
from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from core.file_transfer import FileTransferManager
from ui.icons import icon
from ui.theme import COLORS


def _fmt_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / 1024 / 1024:.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size} B"


class PhoneFileBrowserDialog(QDialog):
    """浏览手机文件：双击进入目录，多选后可拖到电脑或点「取回所选」。"""

    def __init__(self, manager: FileTransferManager, serial: str,
                 device_name: str = "", parent=None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.serial = serial
        self.device_name = device_name
        self._remote_dir = "/"

        self.setWindowTitle("手机文件 — 发送到电脑")
        self.setMinimumSize(620, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(10)

        title = QLabel("手机文件")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        subtitle = QLabel("选择文件后可直接拖到桌面或文件夹；也可以点「取回所选」保存到电脑")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        nav = QHBoxLayout()
        nav.setSpacing(8)
        up_btn = QPushButton("上一级")
        up_btn.setObjectName("GhostButton")
        up_btn.setIcon(icon("back", COLORS["muted"], 14))
        up_btn.setIconSize(QSize(14, 14))
        up_btn.clicked.connect(self._go_up)
        nav.addWidget(up_btn)

        refresh_btn = QPushButton("刷新")
        refresh_btn.setObjectName("GhostButton")
        refresh_btn.setIcon(icon("refresh", COLORS["muted"], 14))
        refresh_btn.setIconSize(QSize(14, 14))
        refresh_btn.clicked.connect(self.refresh)
        nav.addWidget(refresh_btn)

        self.path_label = QLabel("/")
        self.path_label.setObjectName("MonoLabel")
        nav.addWidget(self.path_label, 1)
        layout.addLayout(nav)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list_widget.itemDoubleClicked.connect(self._on_double_clicked)
        self.list_widget.startDrag = self._start_drag  # type: ignore[method-assign]
        layout.addWidget(self.list_widget, 1)

        bottom = QHBoxLayout()
        hint = QLabel("拖动所选文件到电脑即可复制")
        hint.setObjectName("Caption")
        bottom.addWidget(hint)
        bottom.addStretch()

        self.save_btn = QPushButton("取回所选到电脑…")
        save_btn.setObjectName("PrimaryButton")
        save_btn.setIcon(icon("folder", "#FFFFFF", 14))
        save_btn.setIconSize(QSize(14, 14))
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save_selected)
        bottom.addWidget(save_btn)
        layout.addLayout(bottom)

        self.status_label = QLabel("")
        self.status_label.setObjectName("Caption")
        layout.addWidget(self.status_label)

        self.refresh()

    # ------------------------------------------------------------------
    def _serial_dir(self, remote_dir: str) -> str:
        return "/storage/self/primary/" + remote_dir.lstrip("/")

    def refresh(self) -> None:
        self.path_label.setText(self._remote_dir or "/")
        self.list_widget.clear()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            entries = self.manager.list_dir(self.serial, self._remote_dir)
            for entry in entries:
                item = QListWidgetItem(entry["name"])
                item.setData(Qt.UserRole, entry)
                if entry["is_dir"]:
                    item.setIcon(icon("folder", COLORS["accent_hover"], 18))
                    item.setText(entry["name"] + "/")
                else:
                    item.setIcon(icon("copy", COLORS["muted"], 18))
                    item.setText(f"{entry['name']}  ({_fmt_size(entry['size'])})")
                self.list_widget.addItem(item)
        except Exception as error:
            self.status_label.setText(f"读取失败：{error}")
        finally:
            QApplication.restoreOverrideCursor()

    def _on_double_clicked(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.UserRole)
        if data and data.get("is_dir"):
            name = data["name"]
            self._remote_dir = (self._remote_dir.rstrip("/") + "/" + name) if self._remote_dir else "/" + name
            self.refresh()

    def _go_up(self) -> None:
        if self._remote_dir and self._remote_dir != "/":
            self._remote_dir = self._remote_dir.rsplit("/", 1)[0] or "/"
            self.refresh()

    def _selected_paths(self) -> list[str]:
        paths = []
        for item in self.list_widget.selectedItems():
            data = item.data(Qt.UserRole)
            if data and not data.get("is_dir"):
                base = self._remote_dir.rstrip("/")
                paths.append(f"{base}/{data['name']}")
        return paths

    # -- 取回所选 -------------------------------------------------------
    def _save_selected(self) -> None:
        paths = self._selected_paths()
        if not paths:
            self.status_label.setText("请先选择要取回的文件")
            return
        target = QFileDialog.getExistingDirectory(self, "选择保存到电脑的目录")
        if not target:
            return
        result = self.manager.pull_files(self.serial, paths, target)
        if result.ok:
            self.status_label.setText(f"已取回 {result.succeeded} 个文件到 {target}")
        else:
            self.status_label.setText("取回失败：" + "；".join(result.messages[:2]))

    # -- 拖到电脑 -------------------------------------------------------
    def _start_drag(self, actions) -> None:
        """拖动所选文件到电脑：先把文件取回本地临时目录，再启动系统拖拽。"""
        selected = self.list_widget.selectedItems()
        remote_paths = []
        for item in selected:
            data = item.data(Qt.UserRole)
            if data and not data.get("is_dir"):
                base = self._remote_dir.rstrip("/")
                remote_paths.append(f"{base}/{data['name']}")
        if not remote_paths:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        temp_dir = Path(tempfile.gettempdir()) / "SmartCastDrag"
        temp_dir.mkdir(parents=True, exist_ok=True)
        result = self.manager.pull_files(self.serial, remote_paths, str(temp_dir))
        QApplication.restoreOverrideCursor()

        local_files = []
        for name in result.succeeded_names:
            local = temp_dir / Path(name).name
            if local.is_file():
                local_files.append(local)
        if not local_files:
            self.status_label.setText("拖动准备失败，请改用「取回所选到电脑…」")
            return

        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(f)) for f in local_files])
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction)
