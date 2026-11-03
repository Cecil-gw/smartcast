from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QWidget

from ui.components.common import repolish
from ui.icons import icon
from ui.theme import COLORS


class Toast(QFrame):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 9, 16, 9)
        layout.setSpacing(9)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(16, 16)
        self.text_label = QLabel("")
        self.text_label.setObjectName("ToastLabel")
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._effect.setOpacity(0.0)
        self._animation = QPropertyAnimation(self._effect, b"opacity", self)
        self._animation.setDuration(170)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.finished.connect(self._on_animation_finished)
        self._hiding = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self.hide()

    def show_message(self, text: str, tone: str = "info", duration: int = 2800) -> None:
        self._timer.stop()
        self._animation.stop()
        self._hiding = False
        colors = {"success": COLORS["success"], "error": COLORS["error"], "warning": COLORS["warning"]}
        names = {"success": "check", "error": "alert", "warning": "alert", "info": "info"}
        color = colors.get(tone, COLORS["accent_hover"])
        self.setProperty("tone", tone)
        repolish(self)
        self.text_label.setText(text)
        self.icon_label.setPixmap(icon(names.get(tone, "info"), color, 16).pixmap(16, 16))
        self.adjustSize()
        self.reposition()
        self.show()
        self.raise_()
        self._animation.setStartValue(self._effect.opacity())
        self._animation.setEndValue(1.0)
        self._animation.start()
        self._timer.start(duration)

    def reposition(self) -> None:
        parent = self.parentWidget()
        if not parent:
            return
        self.adjustSize()
        x = max(12, (parent.width() - self.width()) // 2)
        y = max(12, parent.height() - self.height() - 54)
        self.move(x, y)

    def _fade_out(self) -> None:
        self._hiding = True
        self._animation.stop()
        self._animation.setStartValue(self._effect.opacity())
        self._animation.setEndValue(0.0)
        self._animation.start()

    def _on_animation_finished(self) -> None:
        if self._hiding:
            self.hide()
            self._hiding = False
