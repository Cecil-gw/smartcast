
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
from core.device_control import (
    BRIGHTNESS_MAX,
    BRIGHTNESS_MIN,
    ScreenBackup,
    ScreenControlError,
    ScreenControlManager,
)


class ScreenControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = ScreenControlManager("adb")
        self.manager.adb = mock.MagicMock()
        self.backup = ScreenBackup()

    def _commands(self) -> list[str]:
        return [c.args[1] for c in self.manager.adb.shell.call_args_list]

    def test_get_brightness_captures_original(self) -> None:
        self.manager.adb.shell.side_effect = ["0", "180"]
        info = self.manager.get_brightness("S1", self.backup)
        self.assertEqual((info["auto"], info["brightness"]), (False, 180))
        self.assertEqual((self.backup.auto_brightness, self.backup.brightness), ("0", "180"))

    def test_set_brightness_disables_auto_once(self) -> None:
        self.manager.adb.shell.side_effect = ["1", None, "200", None, None]
        self.manager.set_brightness("S1", self.backup, 200, auto=False)
        commands = self._commands()
        self.assertIn("settings put system screen_brightness_mode 0", commands)
        self.assertIn("settings put system screen_brightness 200", commands)
        self.assertEqual(self.backup.auto_brightness, "1")
        self.assertEqual(self.backup.brightness, "200")

    def test_brightness_range_check(self) -> None:
        with self.assertRaises(ScreenControlError):
            self.manager.set_brightness("S1", self.backup, BRIGHTNESS_MAX + 1)
        with self.assertRaises(ScreenControlError):
            self.manager.set_brightness("S1", self.backup, BRIGHTNESS_MIN - 1)

    def test_rotation_portrait_saves_original(self) -> None:
        self.manager.adb.shell.side_effect = ["1", "3"] + [None] * 2
        self.manager.set_rotation("S1", self.backup, "portrait")
        self.assertEqual(self.backup.accelerometer_rotation, "1")
        self.assertEqual(self.backup.user_rotation, "3")
        commands = self._commands()
        self.assertIn("settings put system accelerometer_rotation 0", commands)
        self.assertIn("settings put system user_rotation 0", commands)

    def test_rotation_auto_restores_auto_flag(self) -> None:
        self.manager.adb.shell.side_effect = [None] * 2 + [None]
        self.manager.set_rotation("S1", self.backup, "auto")
        self.assertIn("settings put system accelerometer_rotation 1", self._commands())

    def test_screen_always_on_and_restore(self) -> None:
        self.manager.adb.shell.side_effect = ["60000", None]
        original = self.manager.get_screen_off_timeout("S1", self.backup)
        self.assertEqual(original, 60000)
        self.manager.adb.shell.side_effect = [None, None]
        self.manager.set_screen_always_on("S1", self.backup)
        self.assertIn("settings put system screen_off_timeout 2147483647", self._commands())
        self.manager.adb.shell.side_effect = [None]
        restored = self.manager.restore_screen_timeout("S1", self.backup)
        self.assertEqual(restored, 60000)
        self.assertIn("settings put system screen_off_timeout 60000", self._commands())

    def test_restore_all_skips_uncaptured(self) -> None:
        self.backup.brightness = "100"
        restored = self.manager.restore_all("S1", self.backup)
        self.assertEqual(restored, {"screen_brightness": "100"})
        self.assertIn("settings put system screen_brightness 100", self._commands())
        self.assertNotIn("settings put system screen_off_timeout", self._commands())

    def test_read_error_raises_screen_error(self) -> None:
        self.manager.adb.shell.side_effect = AdbError("device offline")
        with self.assertRaises(ScreenControlError) as ctx:
            self.manager.get_brightness("S1", self.backup)
        self.assertIn("offline", str(ctx.exception))

    def test_backup_round_trip(self) -> None:
        self.backup.auto_brightness = "0"
        self.backup.brightness = "128"
        data = self.backup.to_dict()
        clone = ScreenBackup.from_dict(data)
        self.assertEqual(clone.brightness, "128")
        self.assertIsNone(clone.user_rotation)


class ScreenWorkerTests(unittest.TestCase):
    def test_thread_reports_errors_and_success(self) -> None:
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        from workers.screen_worker import ScreenCommandThread

        app = QApplication.instance() or QApplication([])
        manager = mock.MagicMock()
        captured = []

        def collect(serial, payload, error):
            captured.append((payload, error))
            app.quit()

        thread = ScreenCommandThread(manager, "S1", "get_info", ScreenBackup())
        thread.finished_with_result.connect(collect)
        thread.start()
        app.exec()
        self.assertEqual(captured[0][1], "")

        manager.get_brightness.side_effect = ScreenControlError("offline")
        thread2 = ScreenCommandThread(manager, "S1", "get_info", ScreenBackup())
        thread2.finished_with_result.connect(collect)
        thread2.start()
        app.exec()
        self.assertIn("offline", captured[1][1])


if __name__ == "__main__":
    unittest.main()



