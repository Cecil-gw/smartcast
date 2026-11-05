from __future__ import annotations

import html
import re
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QGridLayout,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.components.toggle import ToggleSwitch
from ui.icons import icon
from ui.theme import COLORS

_LEVEL_COLORS = {
    "ERROR": "#D93D4B",
    "WARNING": "#A56C00",
    "INFO": "#5F7185",
}
_DARK_LEVEL_COLORS = {
    "ERROR": COLORS["error"],
    "WARNING": COLORS["warning"],
    "INFO": COLORS["muted"],
}
_LINE_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2} )?(?P<time>\d{2}:\d{2}:\d{2})\s+(?P<level>[A-Z]+)\s+(?P<message>.*)$")


class LogPage(QWidget):
    back_requested = Signal()
    open_logs_requested = Signal()
    clear_logs_requested = Signal()
    export_logs_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._lines: list[str] = []
        self._theme = "light"
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, max(16, int(self.width() * 0.3)), 16)
        root.setSpacing(14)

        header_box = QVBoxLayout()
        header_box.setSpacing(8)
        header = QHBoxLayout()
        header.setSpacing(10)
        back = QPushButton("返回设备")
        back.setObjectName("GhostButton")
        back.setIcon(icon("back", COLORS["muted"], 15))
        back.setIconSize(QSize(15, 15))
        back.setCursor(Qt.PointingHandCursor)
        back.clicked.connect(self.back_requested)
        header.addWidget(back)

        title_column = QVBoxLayout()
        title_column.setSpacing(3)
        title = QLabel("运行日志")
        title.setObjectName("PageTitle")
        subtitle = QLabel("实时查看投屏、扫描和工具检测结果；完整日志保留在本地文件中")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        header.addLayout(title_column, 1)
        header_box.addLayout(header)

        # 操作按钮单独一行，避免挤压标题文字
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        self.open_button = QPushButton("打开目录")
        self.open_button.setIcon(icon("folder", COLORS["muted"], 15))
        self.open_button.setIconSize(QSize(15, 15))
        self.open_button.setCursor(Qt.PointingHandCursor)
        self.open_button.clicked.connect(self.open_logs_requested)
        self.open_button.setMinimumHeight(30)
        actions_row.addWidget(self.open_button)

        self.export_button = QPushButton("导出")
        self.export_button.setIcon(icon("export", COLORS["muted"], 15))
        self.export_button.setIconSize(QSize(15, 15))
        self.export_button.setCursor(Qt.PointingHandCursor)
        self.export_button.clicked.connect(self.export_logs_requested)
        self.export_button.setMinimumHeight(30)
        actions_row.addWidget(self.export_button)

        self.clear_button = QPushButton("清空界面")
        self.clear_button.setObjectName("GhostButton")
        self.clear_button.setIcon(icon("trash", COLORS["muted"], 15))
        self.clear_button.setIconSize(QSize(15, 15))
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.clicked.connect(self.clear_logs_requested)
        self.clear_button.setMinimumHeight(30)
        actions_row.addWidget(self.clear_button)
        actions_row.addStretch(1)
        header_box.addLayout(actions_row)
        root.addLayout(header_box)

        filter_card = QFrame()
        filter_card.setObjectName("ConfigCard")
        filter_layout = QGridLayout(filter_card)
        filter_layout.setContentsMargins(13, 11, 13, 11)
        filter_layout.setHorizontalSpacing(10)
        filter_layout.setVerticalSpacing(8)

        level_title = QLabel("级别")
        level_title.setObjectName("InfoLabel")
        filter_layout.addWidget(level_title, 0, 0)
        self.level_filter = QComboBox()
        for label, value in (("全部", "ALL"), ("INFO", "INFO"), ("WARNING", "WARNING"), ("ERROR", "ERROR")):
            self.level_filter.addItem(label, value)
        self.level_filter.setCurrentIndex(0)
        self.level_filter.currentIndexChanged.connect(self.refresh_view)
        filter_layout.addWidget(self.level_filter, 0, 1)

        search_title = QLabel("搜索")
        search_title.setObjectName("InfoLabel")
        filter_layout.addWidget(search_title, 1, 0)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索序列号、编码器或关键词")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self.refresh_view)
        filter_layout.addWidget(self.search_edit, 1, 1)
        filter_layout.setColumnStretch(1, 1)

        auto_title = QLabel("自动滚动")
        auto_title.setObjectName("InfoValue")
        self.auto_scroll = ToggleSwitch(True)
        filter_layout.addWidget(auto_title, 0, 2)
        filter_layout.addWidget(self.auto_scroll, 0, 3, Qt.AlignVCenter)

        self.count_label = QLabel("0 条")
        self.count_label.setObjectName("Caption")
        self.count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        filter_layout.addWidget(self.count_label, 1, 2, 1, 2)
        root.addWidget(filter_card)

        self.log_view = QTextEdit()
        self.log_view.setObjectName("LogView")
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("等待运行事件…")
        root.addWidget(self.log_view, 1)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.path_label = QLabel("logs/smartcast.log")
        self.path_label.setObjectName("Caption")
        footer.addWidget(self.path_label)
        footer.addStretch()
        tip = QLabel("界面最多保留 500 条，导出时使用当前筛选结果")
        tip.setObjectName("Caption")
        footer.addWidget(tip)
        root.addLayout(footer)

    def set_theme(self, theme: str) -> None:
        self.refresh_view()

    def append_log(self, line: str) -> None:
        line = line.rstrip()
        self._lines.append(line)
        if len(self._lines) > 500:
            self._lines = self._lines[-500:]
        self.refresh_view(only_append=True)

    def load_recent(self, path: Path, count: int = 200) -> None:
        try:
            if not path.exists():
                return
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                lines = handle.readlines()
            self._lines = [line.rstrip() for line in lines[-count:]]
            self.refresh_view()
        except OSError:
            return

    def clear_log(self) -> None:
        self._lines.clear()
        self.log_view.clear()
        self.count_label.setText("0 条")

    def visible_lines(self) -> list[str]:
        keyword = self.search_edit.text().strip().lower()
        level = self.level_filter.currentData()
        result = []
        for line in self._lines:
            if level != "ALL" and f" {level} " not in f" {line} ":
                continue
            if keyword and keyword not in line.lower():
                continue
            result.append(line)
        return result

    def to_plain_text(self) -> str:
        return "\n".join(self.visible_lines())

    def refresh_view(self, only_append: bool = False) -> None:
        lines = self.visible_lines()
        self.count_label.setText(f"{len(lines)} 条")
        if only_append and len(lines) == len(self._lines):
            line = lines[-1] if lines else ""
            self._append_html(line)
            return
        self.log_view.clear()
        for line in lines[-500:]:
            self._append_html(line)
        self._scroll_to_bottom()

    def _append_html(self, line: str) -> None:
        match = _LINE_RE.match(line)
        if match:
            level = match.group("level")
            color = (_DARK_LEVEL_COLORS if self._theme == "dark" else _LEVEL_COLORS).get(level, "#98A5B5")
            if self._theme == "dark" and level == "INFO":
                color = COLORS["muted"]
            message = html.escape(match.group("message"))
            time_text = html.escape(((match.group("date") or "") + match.group("time")).strip())
            level_text = html.escape(level)
            html_line = (
                f'<span style="color:#98A5B5;">{time_text}</span> '
                f'<span style="color:{color}; font-weight:700;">{level_text}</span> '
                f'<span style="color:{"#F4F7FC" if self._theme == "dark" else "#1D2939"};">{message}</span>'
            )
        else:
            color = "#9AA9BC" if self._theme == "dark" else "#66758A"
            html_line = f'<span style="color:{color};">{html.escape(line)}</span>'
        self.log_view.append(html_line)
        cursor = self.log_view.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_view.setTextCursor(cursor)

    def _scroll_to_bottom(self) -> None:
        if not self.auto_scroll.isChecked():
            return
        bar = self.log_view.verticalScrollBar()
        bar.setValue(bar.maximum())




