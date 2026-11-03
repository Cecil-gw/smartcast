
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
vendor = Path(__file__).resolve().parents[1] / "vendor"
if vendor.is_dir():
    sys.path.insert(0, str(vendor))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QComboBox, QSpinBox, QWidget

from ui.components.wheel_guard import WheelGuard


def wheel_event():
    return QWheelEvent(
        QPointF(10, 10), QPointF(10, 10),
        QPoint(0, -120), QPoint(0, 120),
        Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False,
    )


class WheelGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])
        self.guard = WheelGuard(self.app)

    def test_combo_wheel_filtered(self) -> None:
        combo = QComboBox()
        combo.addItems(["a", "b", "c"])
        combo.setCurrentIndex(1)
        # guard consumes the wheel event -> value must not change
        self.assertTrue(self.guard.eventFilter(combo, wheel_event()))
        self.assertEqual(combo.currentIndex(), 1)

    def test_spin_wheel_filtered(self) -> None:
        spin = QSpinBox()
        spin.setRange(1, 100)
        spin.setValue(50)
        self.assertTrue(self.guard.eventFilter(spin, wheel_event()))
        self.assertEqual(spin.value(), 50)

    def test_other_widgets_not_filtered(self) -> None:
        widget = QWidget()
        # guard passes non-option widgets through to the default handler
        self.assertFalse(self.guard.eventFilter(widget, wheel_event()))

    def test_non_wheel_events_pass(self) -> None:
        combo = QComboBox()
        self.assertFalse(self.guard.eventFilter(combo, QEvent(QEvent.MouseButtonPress)))


if __name__ == "__main__":
    unittest.main()

