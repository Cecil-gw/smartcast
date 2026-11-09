
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
vendor = Path(__file__).resolve().parents[1] / "vendor"
if vendor.is_dir():
    sys.path.insert(0, str(vendor))

from core.file_transfer import FileTransferManager, TransferResult


class PushTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.file1 = self.base / "a.txt"
        self.file1.write_text("hello", encoding="utf-8")
        self.manager = FileTransferManager("adb")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_push_creates_dir_and_transfers(self) -> None:
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            class R:
                returncode = 0
                stdout = "1 file pushed"
                stderr = ""
            return R()

        with mock.patch("core.file_transfer.subprocess.run", side_effect=fake_run):
            result = self.manager.push_files("S1", [str(self.file1)])

        self.assertTrue(result.ok)
        self.assertEqual(result.succeeded, 1)
        # 先 mkdir 再 push
        self.assertIn("shell", calls[0])
        self.assertIn("mkdir -p", calls[0][-1])
        self.assertEqual(calls[1][:4], ["adb", "-s", "S1", "push"])
        self.assertTrue(calls[1][5].endswith("/a.txt"))

    def test_push_failure_collects_message(self) -> None:
        def fake_run(cmd, **kwargs):
            class R:
                returncode = 1
                stdout = ""
                stderr = "adb: error: failed to copy"
            return R()

        with mock.patch("core.file_transfer.subprocess.run", side_effect=fake_run):
            result = self.manager.push_files("S1", [str(self.file1)])

        self.assertFalse(result.ok)
        self.assertEqual(result.failed, 1)
        self.assertIn("failed to copy", result.messages[0])

    def test_no_valid_files(self) -> None:
        result = self.manager.push_files("S1", [str(self.base / "missing.txt")])
        self.assertFalse(result.ok)
        self.assertEqual(result.total, 0)

    def test_serial_isolation(self) -> None:
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            class R:
                returncode = 0
                stdout = ""
                stderr = ""
            return R()

        with mock.patch("core.file_transfer.subprocess.run", side_effect=fake_run):
            self.manager.push_files("192.168.1.9:5555", [str(self.file1)])
        self.assertEqual(calls[1][2], "192.168.1.9:5555")


class PullTests(unittest.TestCase):
    def test_pull_success(self) -> None:
        manager = FileTransferManager("adb")
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("core.file_transfer.subprocess.run") as runner:
                runner.return_value.returncode = 0
                runner.return_value.stdout = ""
                runner.return_value.stderr = ""
                result = manager.pull_files("S1", ["/sdcard/a.txt"], tmp)
        self.assertTrue(result.ok)
        cmd = runner.call_args[0][0]
        self.assertEqual(cmd[:5], ["adb", "-s", "S1", "pull", "/sdcard/a.txt"])


if __name__ == "__main__":
    unittest.main()
