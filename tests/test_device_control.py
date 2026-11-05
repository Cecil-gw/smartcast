
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
vendor = Path(__file__).resolve().parents[1] / "vendor"
if vendor.is_dir():
    sys.path.insert(0, str(vendor))

from core.adb_manager import AdbError
from core.device_control import DeviceControlManager


class ControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = DeviceControlManager("adb")
        self.manager.adb = mock.MagicMock()

    def test_back_uses_serial_and_code(self) -> None:
        result = self.manager.run_action("192.168.1.5:5555", "back")
        self.assertTrue(result.success)
        self.assertEqual(self.manager.adb.shell.call_args[0][0], "192.168.1.5:5555")
        self.assertEqual(self.manager.adb.shell.call_args[0][1], "input keyevent 4")

    def test_home_and_recent(self) -> None:
        self.manager.run_action("S1", "home")
        self.assertEqual(self.manager.adb.shell.call_args[0][1], "input keyevent 3")
        self.manager.run_action("S1", "recent")
        self.assertEqual(self.manager.adb.shell.call_args[0][1], "input keyevent 187")

    def test_volume_codes(self) -> None:
        self.manager.run_action("S1", "volume_up")
        self.assertIn("keyevent 24", self.manager.adb.shell.call_args[0][1])
        self.manager.run_action("S1", "volume_down")
        self.assertIn("keyevent 25", self.manager.adb.shell.call_args[0][1])

    def test_power_menu_uses_longpress(self) -> None:
        self.manager.run_action("S1", "power_menu")
        self.assertIn("keyevent --longpress 26", self.manager.adb.shell.call_args[0][1])

    def test_mute(self) -> None:
        self.manager.run_action("S1", "mute")
        self.assertIn("keyevent 164", self.manager.adb.shell.call_args[0][1])

    def test_lock(self) -> None:
        self.manager.run_action("S1", "lock")
        self.assertIn("keyevent 26", self.manager.adb.shell.call_args[0][1])

    def test_adb_error_returns_failure(self) -> None:
        self.manager.adb.shell.side_effect = AdbError("offline")
        result = self.manager.run_action("S1", "home")
        self.assertFalse(result.success)
        self.assertIn("失败", result.message)
        self.assertIn("offline", result.message)

    def test_unknown_action(self) -> None:
        result = self.manager.run_action("S1", "hack")
        self.assertFalse(result.success)
        self.manager.adb.shell.assert_not_called()

    def test_usb_and_wifi_isolation(self) -> None:
        self.manager.run_action("USB1", "back")
        first = self.manager.adb.shell.call_args[0][0]
        self.manager.run_action("192.168.1.9:5556", "back")
        second = self.manager.adb.shell.call_args[0][0]
        self.assertEqual((first, second), ("USB1", "192.168.1.9:5556"))


class ControlWorkerTests(unittest.TestCase):
    def test_thread_swallows_unexpected_errors(self) -> None:
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        from workers.control_worker import ControlCommandThread

        app = QApplication.instance() or QApplication([])
        manager = mock.MagicMock()
        manager.run_action.side_effect = RuntimeError("boom")
        captured = {}
        thread = ControlCommandThread(manager, "S1", "back")
        thread.finished_with_result.connect(lambda r: (captured.update(r=r), app.quit()))
        thread.start()
        app.exec()
        self.assertFalse(captured["r"].success)
        self.assertIn("boom", captured["r"].message)


if __name__ == "__main__":
    unittest.main()

def tearDownModule() -> None:
    """清理 Qt 对象，避免解释器退出阶段析构崩溃。"""
    import gc

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is not None:
        for widget in list(app.topLevelWidgets()):
            try:
                widget.close()
                widget.deleteLater()
            except RuntimeError:
                pass
        app.processEvents()
    gc.collect()
