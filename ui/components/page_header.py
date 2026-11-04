from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


class PageHeader(QWidget):
    """统一页面标题区：标题 + 说明 + 右侧操作区。

    所有页面共用同一套层级与间距，保证视觉一致，也为后续背景层
    （标题淡入动画）预留统一的挂载点。
    """

    def __init__(self, title: str, subtitle: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("PageHeader")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        text_column = QVBoxLayout()
        text_column.setSpacing(3)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("PageTitle")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("PageSubtitle")
        self.subtitle_label.setWordWrap(True)
        text_column.addWidget(self.title_label)
        text_column.addWidget(self.subtitle_label)
        layout.addLayout(text_column, 1)

        self._actions = QHBoxLayout()
        self._actions.setSpacing(8)
        self._actions.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addLayout(self._actions)

    # ------------------------------------------------------------------
    def add_action(self, widget: QWidget) -> QWidget:
        self._actions.addWidget(widget, 0, Qt.AlignVCenter)
        return widget

    def add_layout(self, layout) -> None:
        self._actions.addLayout(layout)

    def set_subtitle(self, text: str) -> None:
        self.subtitle_label.setText(text)

    def set_title(self, text: str) -> None:
        self.title_label.setText(text)
