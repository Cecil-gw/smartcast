from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class StatusDot(QWidget):
    def __init__(self, color: str = "#6F7A89", size: int = 8, parent=None) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedSize(size, size)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._color)
        painter.drawEllipse(self.rect())


class StatusPill(QLabel):
    def __init__(self, text: str = "", tone: str = "idle", parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("StatusPill")
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.set_tone(tone)

    def set_tone(self, tone: str) -> None:
        self.setProperty("tone", tone)
        repolish(self)


class MetaChip(QLabel):
    def __init__(self, text: str = "", tone: str = "idle", parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("Chip")
        self.setProperty("tone", tone)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

    def set_tone(self, tone: str) -> None:
        self.setProperty("tone", tone)
        repolish(self)


class InfoTile(QFrame):
    def __init__(self, label: str, value: str = "—", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("InfoTile")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(11, 9, 11, 9)
        layout.setSpacing(3)
        self.label = QLabel(label)
        self.label.setObjectName("InfoLabel")
        self.value = QLabel(value)
        self.value.setObjectName("InfoValue")
        self.value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.label)
        layout.addWidget(self.value)

    def set_value(self, value: str) -> None:
        self.value.setText(value or "—")


class ElidedLabel(QLabel):
    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(parent)
        self._full_text = text
        self.setToolTip(text)
        super().setText(text)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    def setText(self, text: str) -> None:
        self._full_text = text
        self.setToolTip(text)
        self._update_elide()

    def text(self) -> str:
        return self._full_text

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_elide()

    def _update_elide(self) -> None:
        if not self._full_text:
            super().setText("")
            return
        metrics = self.fontMetrics()
        available = max(0, self.width() - 2)
        super().setText(metrics.elidedText(self._full_text, Qt.ElideRight, available) if available > 8 else self._full_text)


class IconBadge(QFrame):
    def __init__(self, pixmap_icon, size: int = 34, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("IconBadge")
        self.setFixedSize(size, size)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel()
        label.setPixmap(pixmap_icon.pixmap(18, 18))
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
