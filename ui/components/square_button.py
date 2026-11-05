
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ui.components.common import repolish
from ui.icons import icon
from ui.theme import COLORS


class SquareActionButton(QWidget):
    """正方形操作按钮：图标严格居中，文字在下方，整体垂直居中。

    用 QWidget + 布局实现，保证图标与文字都在方块正中间，
    不受 QToolButton 文本对齐策略影响。
    """

    clicked = Signal()

    def __init__(self, text: str, icon_name: str, size: int = 64, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SquareAction")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(text)
        self._icon_name = icon_name

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(8)  # 图标与文字之间 8px 间隙
        layout.addStretch(1)

        self._icon_label = QLabel()
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setFixedHeight(18)
        layout.addWidget(self._icon_label)

        self._text_label = QLabel(text)
        self._text_label.setObjectName("SquareActionText")
        self._text_label.setAlignment(Qt.AlignCenter)
        self._text_label.setWordWrap(True)
        layout.addWidget(self._text_label)

        layout.addStretch(1)
        self.setEnabled(False)

    # -- API -----------------------------------------------------------
    def text(self) -> str:
        return self._text_label.text()

    def setText(self, text: str) -> None:
        self._text_label.setText(text)
        self.setToolTip(text)

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self.setProperty("disabled", not enabled)
        self._text_label.setProperty("disabled", not enabled)
        repolish(self)
        repolish(self._text_label)
        self._refresh_icon()

    def _refresh_icon(self) -> None:
        color = COLORS["accent_hover"] if self.isEnabled() else COLORS["faint"]
        self._icon_label.setPixmap(icon(self._icon_name, color, 18).pixmap(18, 18))

    # -- interaction ---------------------------------------------------
    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.isEnabled():
            self.clicked.emit()
        super().mouseReleaseEvent(event)
