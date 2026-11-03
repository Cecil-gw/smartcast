
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

from core.media_manager import (
    MediaManager,
    MediaRecord,
    sanitize_dir_name,
)


class SanitizeTests(unittest.TestCase):
    def test_safe_names_kept(self) -> None:
        self.assertEqual(sanitize_dir_name("W201DS"), "W201DS")
        self.assertEqual(sanitize_dir_name("Pixel-7"), "Pixel-7")

    def test_unsafe_characters_replaced(self) -> None:
        self.assertEqual(sanitize_dir_name("Mi 11 Ultra"), "Mi_11_Ultra")
        self.assertEqual(sanitize_dir_name('bad/../name:*?"<>|'), "bad_name")
        self.assertEqual(sanitize_dir_name(""), "UnknownDevice")
        self.assertEqual(sanitize_dir_name("///"), "UnknownDevice")

    def test_long_name_truncated(self) -> None:
        self.assertLessEqual(len(sanitize_dir_name("x" * 100)), 40)


class MediaManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.manager = MediaManager("adb", media_dir=str(self.base / "media"))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_screenshot_saves_png_and_record(self) -> None:
        class FakeResult:
            returncode = 0
            stdout = b"\x89PNG fake data"
            stderr = b""

        payload = {"record": None}

        def fake_run(cmd, **kwargs):
            payload["cmd"] = cmd
            return FakeResult()

        with mock.patch("core.media_manager.subprocess.run", side_effect=fake_run):
            record = self.manager.screenshot("192.168.1.5:5555", "W201DS")
        self.assertTrue(Path(record.path).is_file())
        self.assertEqual(Path(record.path).read_bytes(), b"\x89PNG fake data")
        # serial passed to adb
        self.assertEqual(payload["cmd"][1:4], ["-s", "192.168.1.5:5555", "exec-out"])
        # stored under screenshots/model dir
        self.assertIn("screenshots", record.path)
        self.assertIn("W201DS", record.path)
        # persisted in history json
        history = self.manager.load_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].file_name, record.file_name)

    def test_screenshot_failure_raises_with_adb_message(self) -> None:
        class FakeResult:
            returncode = 1
            stdout = b""
            stderr = b"device offline"

        with mock.patch("core.media_manager.subprocess.run", return_value=FakeResult()):
            with self.assertRaises(RuntimeError) as ctx:
                self.manager.screenshot("S1", "Model")
        self.assertIn("offline", str(ctx.exception))

    def test_unique_names_avoid_conflicts(self) -> None:
        directory = self.manager.device_media_dir("screenshot", "M")
        first = self.manager.unique_path(directory, "SmartCast", ".png")
        first.write_bytes(b"x")
        second = self.manager.unique_path(directory, "SmartCast", ".png")
        self.assertNotEqual(first, second)

    def test_recording_start_and_stop(self) -> None:
        class FakePopen:
            def __init__(self):
                self.terminated = False
                self.killed = False
            def wait(self, timeout=None):
                import subprocess
                raise subprocess.TimeoutExpired(cmd="scrcpy", timeout=timeout)
            def terminate(self):
                self.terminated = True
            def kill(self):
                self.killed = True

        fake = FakePopen()
        with mock.patch("core.media_manager.subprocess.Popen", return_value=fake):
            record = self.manager.start_recording("S1", "M", "scrcpy.exe")
        self.assertIn("recordings", record.path)
        self.assertEqual(self.manager.recording_processes["S1"], fake)
        # start twice must fail
        with mock.patch("core.media_manager.subprocess.Popen", return_value=fake):
            with self.assertRaises(RuntimeError):
                self.manager.start_recording("S1", "M", "scrcpy.exe")
        # write a fake recording file, then stop finalizes its size
        Path(record.path).write_bytes(b"0" * 12345)
        stopped = self.manager.stop_recording("S1")
        self.assertTrue(fake.terminated)
        self.assertEqual(stopped.size, 12345)
        self.assertNotIn("S1", self.manager.recording_processes)

    def test_stop_without_recording_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            self.manager.stop_recording("S1")

    def test_history_persistence_and_missing_file(self) -> None:
        record = MediaRecord(
            file_name="a.png", path=str(self.base / "a.png"), media_type="screenshot",
            device_name="M", serial="S1", created="2026-11-03 10:00:00", size=10,
        )
        self.manager.add_record(record)
        reloaded = MediaManager("adb", media_dir=str(self.base / "media"))
        history = reloaded.load_history()
        self.assertEqual(len(history), 1)
        self.assertFalse(history[0].exists())  # file never created -> missing

    def test_delete_record_keeps_file(self) -> None:
        target = self.base / "keep.png"
        target.write_bytes(b"data")
        record = MediaRecord(
            file_name="keep.png", path=str(target), media_type="screenshot",
            device_name="M", serial="S1", created="t", size=4,
        )
        self.manager.add_record(record)
        self.manager.delete_record(record)
        self.assertTrue(target.is_file())  # file untouched
        self.assertEqual(self.manager.load_history(), [])

    def test_delete_file_and_record(self) -> None:
        target = self.base / "gone.png"
        target.write_bytes(b"data")
        record = MediaRecord(
            file_name="gone.png", path=str(target), media_type="screenshot",
            device_name="M", serial="S1", created="t", size=4,
        )
        self.manager.add_record(record)
        self.manager.delete_file_and_record(record)
        self.assertFalse(target.is_file())
        self.assertEqual(self.manager.load_history(), [])


if __name__ == "__main__":
    unittest.main()
