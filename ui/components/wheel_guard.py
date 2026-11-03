
from __future__ import annotations

from PySide6.QtCore import QObject, QEvent
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QSpinBox


class WheelGuard(QObject):
    """Blocks mouse-wheel changes on combo boxes and spin boxes.

    Values can only be changed by clicking or typing, so scrolling a page
    never accidentally edits parameters.
    """

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Wheel and isinstance(
            watched, (QComboBox, QSpinBox, QDoubleSpinBox)
        ):
            # let the scroll propagate to the page instead of changing values
            event.ignore()
            return True
        return super().eventFilter(watched, event)
