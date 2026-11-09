
from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
vendor = Path(__file__).resolve().parents[1] / "vendor"
if vendor.is_dir():
    sys.path.insert(0, str(vendor))

from core.cast_session import (
    SESSION_DEVICE_OFFLINE,
    SESSION_RUNNING,
    SESSION_STOPPED,
    CastSession,
    format_duration,
)
from core.device_info import DeviceInfo


class SessionModelTests(unittest.TestCase):
    def test_duration_formatting(self) -> None:
        self.assertEqual(format_duration(0), "00:00:00")
        self.assertEqual(format_duration(754), "00:12:34")
        self.assertEqual(format_duration(37235), "10:20:35")

    def test_session_states_and_labels(self) -> None:
        session = CastSession(serial="S1", state=SESSION_RUNNING)
        self.assertEqual(session.state_label(), "投屏中")
        session.state = SESSION_DEVICE_OFFLINE
        self.assertEqual(session.state_label(), "设备离线")

    def test_duration_counts_only_when_active(self) -> None:
        session = CastSession(serial="S1", state=SESSION_RUNNING)
        session.started_monotonic = time.monotonic() - 10
        self.assertGreaterEqual(session.duration_seconds(), 9.5)
        session.state = SESSION_STOPPED
        self.assertEqual(session.duration_seconds(), 0.0)

    def test_params_text_uses_config_values(self) -> None:
        session = CastSession(serial="S1", codec="h264", bitrate_mbps=8, resolution="720", fps=60, audio=False)
        text = session.params_text()
        self.assertIn("h264", text)
        self.assertIn("8Mbps", text)
        self.assertIn("无声", text)

    def test_connection_label(self) -> None:
        self.assertEqual(CastSession(serial="1.2.3.4:5555", connection_type="wifi").connection_label(), "Wi-Fi")
        self.assertEqual(CastSession(serial="usb1", connection_type="usb").connection_label(), "USB")


class SessionManagerTests(unittest.TestCase):
    """scrcpy_manager keeps per-serial sessions; multiple devices stay isolated."""

    def _manager(self):
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        self.app = QApplication.instance() or QApplication([])
        from core.scrcpy_manager import ScrcpyManager

        return ScrcpyManager()

    def test_start_creates_starting_session(self) -> None:
        manager = self._manager()
        device = DeviceInfo(serial="S1", state="device")
        with mock.patch.object(manager, "_find_window", return_value=0):
            with mock.patch("core.scrcpy_manager.QProcess.start") as fake_start:
                ok = manager.start(device, "h264", "720", 60, 8)
        self.assertTrue(ok)
        session = manager.sessions["S1"]
        self.assertEqual(session.state, "starting")
        self.assertEqual(session.bitrate_mbps, 8)
        self.assertEqual(session.resolution, "720")

    def test_multi_device_isolation(self) -> None:
        manager = self._manager()
        d1 = DeviceInfo(serial="USB1", state="device", connection_type="usb")
        d2 = DeviceInfo(serial="1.2.3.4:5555", state="device", connection_type="wifi")
        with mock.patch("core.scrcpy_manager.QProcess.start"):
            manager.start(d1, "h264", "original", 0, 8)
            manager.start(d2, "h265", "720", 60, 32)
        self.assertEqual(len(manager.sessions), 2)
        self.assertEqual(manager.sessions["USB1"].connection_type, "usb")
        self.assertEqual(manager.sessions["1.2.3.4:5555"].connection_type, "wifi")
        self.assertEqual(manager.sessions["1.2.3.4:5555"].bitrate_mbps, 32)
        # stopping one leaves the other untouched
        manager.sessions["USB1"].state = SESSION_RUNNING
        manager.stop("USB1")
        self.assertEqual(manager.sessions["USB1"].state, "stopped")
        self.assertEqual(manager.sessions["1.2.3.4:5555"].state, "starting")

    def test_mark_device_offline(self) -> None:
        manager = self._manager()
        manager.sessions["S1"] = CastSession(serial="S1", state=SESSION_RUNNING)
        manager.mark_device_offline("S1")
        self.assertEqual(manager.sessions["S1"].state, SESSION_DEVICE_OFFLINE)
        manager.mark_device_offline("UNKNOWN")

    def test_active_sessions_filter(self) -> None:
        manager = self._manager()
        manager.sessions = {
            "a": CastSession(serial="a", state=SESSION_RUNNING),
            "b": CastSession(serial="b", state=SESSION_STOPPED),
            "c": CastSession(serial="c", state=SESSION_DEVICE_OFFLINE),
        }
        self.assertEqual([s.serial for s in manager.active_sessions()], ["a"])

    def test_start_rejects_non_running_device(self) -> None:
        manager = self._manager()
        device = DeviceInfo(serial="S1", state="offline")
        self.assertFalse(manager.start(device, "h264", "original", 0, 8))
        self.assertNotIn("S1", manager.sessions)


class AutoTuneTests(unittest.TestCase):
    def test_normal_phone_keeps_native_resolution(self) -> None:
        from core.device_info import DeviceInfo
        from core.parameter_optimizer import auto_tune

        device = DeviceInfo("S", "device", resolution="1080x2400", density="400")
        tuning = auto_tune(device, "auto", 0)
        self.assertEqual(tuning.resolution, "original")
        self.assertEqual(tuning.fps, 60)

    def test_4k_device_capped(self) -> None:
        from core.device_info import DeviceInfo
        from core.parameter_optimizer import auto_tune

        device = DeviceInfo("S", "device", resolution="1440x3200", density="500")
        tuning = auto_tune(device, "auto", 0)
        self.assertEqual(tuning.resolution, "1920")

    def test_explicit_values_respected(self) -> None:
        from core.device_info import DeviceInfo
        from core.parameter_optimizer import auto_tune

        device = DeviceInfo("S", "device", resolution="1080x2400", density="400")
        tuning = auto_tune(device, "720", 120)
        self.assertEqual(tuning.resolution, "720")
        # >90fps 自动收敛到 60
        self.assertEqual(tuning.fps, 60)


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
