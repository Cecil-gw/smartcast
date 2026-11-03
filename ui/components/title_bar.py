from __future__ import annotations

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QWidget

from ui.icons import icon
from ui.theme import COLORS


class TitleBar(QFrame):
    """Custom light-themed title bar: app icon, title, and window controls."""

    minimize_requested = Signal()
    maximize_toggled = Signal()
    close_requested = Signal()

    def __init__(self, title: str = "SmartCast", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(40)
        self._drag_pos: QPoint | None = None
        self._maximized = False

        # No app icon or title text here: the icon lives on the taskbar and
        # the bar itself blends into the page background.
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch()

        self.min_button = self._control_button("minus", "最小化", self.minimize_requested)
        self.max_button = self._control_button("maximize", "最大化", self.maximize_toggled)
        self.close_button = self._control_button("close", "关闭", self.close_requested)
        self.min_button.installEventFilter(self)
        self.max_button.installEventFilter(self)
        self.close_button.installEventFilter(self)
        layout.addWidget(self.min_button)
        layout.addWidget(self.max_button)
        layout.addWidget(self.close_button)

    def _control_button(self, icon_name: str, tooltip: str, signal: Signal) -> QPushButton:
        button = QPushButton()
        button.setObjectName("TitleControlButton")
        button.setIcon(icon(icon_name, COLORS["muted"], 14))
        button.setIconSize(QSize(14, 14))
        button.setToolTip(tooltip)
        button.setCursor(Qt.PointingHandCursor)
        button.setFixedSize(44, 36)
        button.clicked.connect(signal)
        return button

    def eventFilter(self, watched, event) -> bool:
        hover_in = event.type() == event.Type.HoverEnter
        hover_out = event.type() == event.Type.HoverLeave
        if hover_in or hover_out:
            color = COLORS["muted"]
            if hover_in:
                color = COLORS["error"] if watched is self.close_button else COLORS["text"]
            for button in (self.min_button, self.max_button, self.close_button):
                if watched is button:
                    name = "close" if button is self.close_button else ("minus" if button is self.min_button else ("restore" if self._maximized else "maximize"))
                    button.setIcon(icon(name, color, 14))
        return super().eventFilter(watched, event)

    # ------------------------------------------------------------------
    def set_maximized(self, maximized: bool) -> None:
        self._maximized = maximized
        self.max_button.setIcon(icon("restore" if maximized else "maximize", COLORS["muted"], 14))
        self.max_button.setToolTip("还原" if maximized else "最大化")

    # Drag handling -----------------------------------------------------
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton and not self._maximized:
            window = self.window()
            window.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.maximize_toggled.emit()
        super().mouseDoubleClickEvent(event)
