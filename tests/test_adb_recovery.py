
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
vendor = Path(__file__).resolve().parents[1] / "vendor"
if vendor.is_dir():
    sys.path.insert(0, str(vendor))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from core.adb_manager import AdbError, is_server_fault
from core.adb_manager import RawDevice
from workers.device_worker import DeviceWorker


class ServerFaultDetectionTests(unittest.TestCase):
    def test_recognizes_common_faults(self) -> None:
        messages = [
            "adb.exe: failed to check server version: protocol fault (couldn't read status): connection reset",
            "cannot connect to daemon",
            "error: protocol fault (couldn't read status)",
            "failed to start daemon",
        ]
        for message in messages:
            self.assertTrue(is_server_fault(message), message)

    def test_ignores_normal_errors(self) -> None:
        self.assertFalse(is_server_fault("device offline"))
        self.assertFalse(is_server_fault("adb devices failed (1)"))
        self.assertFalse(is_server_fault(""))


class WorkerRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])
        self.adb = mock.MagicMock()
        self.worker = DeviceWorker(self.adb, interval=2)

    def test_recovers_and_retries(self) -> None:
        fault = AdbError(
            "adb.exe: failed to check server version: protocol fault (couldn't read status): connection reset"
        )
        self.adb.devices.side_effect = [fault, [RawDevice("S1", "device")]]
        self.adb.recover_server.return_value = True

        with mock.patch.object(self.worker.reader, "read") as reader:
            from core.device_info import DeviceInfo

            reader.return_value = DeviceInfo("S1", "device")
            self.worker.scan()

        self.adb.recover_server.assert_called_once()
        self.assertEqual(self.adb.devices.call_count, 2)

    def test_recovery_rate_limited(self) -> None:
        fault = AdbError("cannot connect to daemon")
        self.adb.devices.side_effect = fault
        self.adb.recover_server.return_value = True

        self.worker.scan()
        first_calls = self.adb.recover_server.call_count
        self.worker.scan()
        # 30 秒内不重复恢复
        self.assertEqual(self.adb.recover_server.call_count, first_calls)

    def test_timeout_also_triggers_recovery(self) -> None:
        """持续超时同样视为服务端异常，必须自动恢复（用户要求免手动）。"""
        self.adb.devices.side_effect = [
            AdbError("Command timed out"),
            [RawDevice("S1", "device")],
        ]
        self.adb.recover_server.return_value = True
        with mock.patch.object(self.worker.reader, "read") as reader:
            from core.device_info import DeviceInfo

            reader.return_value = DeviceInfo("S1", "device")
            self.worker.scan()
        self.adb.recover_server.assert_called_once()
        self.assertEqual(self.adb.devices.call_count, 2)

    def test_second_failure_escalates_to_hard_reset(self) -> None:
        """一级恢复没解决时，下一次自动升级为彻底重置。"""
        self.adb.devices.side_effect = AdbError("protocol fault (couldn't read status)")
        self.adb.recover_server.return_value = True
        self.adb.hard_reset_server = mock.MagicMock(return_value=True)

        self.worker.scan()          # 一级恢复
        self.worker._last_recovery = 0.0   # 解除时间限频，模拟 12 秒后
        self.worker.scan()          # 升级为彻底重置

        self.adb.recover_server.assert_called_once()
        self.adb.hard_reset_server.assert_called_once()


if __name__ == "__main__":
    unittest.main()

class ForeignProcessCleanupTests(unittest.TestCase):
    def test_skips_own_adb_and_kills_others(self) -> None:
        from core.adb_manager import kill_foreign_adb_processes

        own = r"C:\Tools\SmartCast\resources\adb\adb.exe"
        procs = [
            (111, own),
            (222, r"C:\Android\platform-tools\adb.exe"),
            (333, ""),
        ]
        with mock.patch("core.adb_manager.list_adb_processes", return_value=procs), \
                mock.patch("subprocess.run") as runner:
            killed = kill_foreign_adb_processes(own)

        self.assertEqual(killed, [222, 333])
        self.assertEqual(runner.call_count, 2)
        called_pids = [call.args[0][3] for call in runner.call_args_list]
        self.assertEqual(called_pids, ["222", "333"])

    def test_case_insensitive_own_path(self) -> None:
        from core.adb_manager import kill_foreign_adb_processes

        own = r"C:\Tools\adb.exe"
        procs = [(111, r"c:\tools\ADB.EXE")]
        with mock.patch("core.adb_manager.list_adb_processes", return_value=procs), \
                mock.patch("subprocess.run") as runner:
            killed = kill_foreign_adb_processes(own)

        self.assertEqual(killed, [])
        runner.assert_not_called()

    def test_recovery_kills_foreign_before_restart(self) -> None:
        from core.adb_manager import AdbManager

        manager = AdbManager("adb")
        with mock.patch("core.adb_manager.kill_foreign_adb_processes", return_value=[123]) as killer, \
                mock.patch("core.adb_manager.run_command", return_value=(0, "", "")):
            ok = manager.recover_server()
        self.assertTrue(ok)
        killer.assert_called_once()

