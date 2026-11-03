from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from utils.system_utils import writable_data_dir


MEDIA_TYPE_SCREENSHOT = "screenshot"
MEDIA_TYPE_RECORDING = "recording"

_SAFE_NAME_RE = re.compile(r"[^\w\-]+", re.UNICODE)


def sanitize_dir_name(name: str) -> str:
    """Only word chars/dashes survive; keeps directory paths safe."""
    cleaned = _SAFE_NAME_RE.sub("_", (name or "").strip())
    cleaned = cleaned.strip("._") or "UnknownDevice"
    return cleaned[:40]


def default_media_root() -> Path:
    return writable_data_dir() / "SmartCast"


@dataclass
class MediaRecord:
    file_name: str
    path: str
    media_type: str
    device_name: str
    serial: str
    created: str
    size: int

    def to_dict(self) -> dict:
        return {
            "file_name": self.file_name,
            "path": self.path,
            "type": self.media_type,
            "device_name": self.device_name,
            "serial": self.serial,
            "created": self.created,
            "size": self.size,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MediaRecord":
        return cls(
            file_name=data.get("file_name", ""),
            path=data.get("path", ""),
            media_type=data.get("type", ""),
            device_name=data.get("device_name", ""),
            serial=data.get("serial", ""),
            created=data.get("created", ""),
            size=int(data.get("size", 0)),
        )

    def exists(self) -> bool:
        return bool(self.path) and Path(self.path).is_file()


class MediaManager:
    """Screenshots, recordings and persisted media history."""

    def __init__(self, adb_path: str, media_dir: str = "") -> None:
        self.adb_path = adb_path
        self.media_root = Path(media_dir) if media_dir else default_media_root()
        self.history_path = self.media_root / "media_history.json"
        self._history: list[MediaRecord] | None = None
        self.recording_processes: dict[str, subprocess.Popen] = {}

    # ------------- directories -------------
    def device_media_dir(self, media_type: str, device_name: str) -> Path:
        sub = "screenshots" if media_type == MEDIA_TYPE_SCREENSHOT else "recordings"
        path = self.media_root / sub / sanitize_dir_name(device_name)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def unique_path(self, directory: Path, stem: str, ext: str) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        candidate = directory / f"{stem}_{stamp}{ext}"
        counter = 1
        while candidate.exists():
            candidate = directory / f"{stem}_{stamp}_{counter}{ext}"
            counter += 1
        return candidate

    # ------------- screenshot -------------
    def screenshot(self, serial: str, device_name: str, adb_path: str | None = None) -> MediaRecord:
        adb = adb_path or self.adb_path
        # exec-out screencap -p streams PNG bytes; subprocess must use bytes
        # mode because utils.run_command decodes text and corrupts binaries.
        result = subprocess.run(
            [adb, "-s", serial, "exec-out", "screencap", "-p"],
            capture_output=True,
            timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0 or not result.stdout:
            raise RuntimeError(
                "截图失败：" + (result.stderr.decode("utf-8", errors="replace").strip() or f"退出码 {result.returncode}")
            )
        directory = self.device_media_dir(MEDIA_TYPE_SCREENSHOT, device_name)
        path = self.unique_path(directory, "SmartCast", ".png")
        path.write_bytes(result.stdout)
        return self.add_record(
            MediaRecord(
                file_name=path.name,
                path=str(path),
                media_type=MEDIA_TYPE_SCREENSHOT,
                device_name=device_name,
                serial=serial,
                created=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                size=path.stat().st_size,
            )
        )

    # ------------- recording -------------
    def start_recording(self, serial: str, device_name: str, scrcpy_path: str) -> MediaRecord:
        if serial in self.recording_processes:
            raise RuntimeError("该设备已经在录制中")
        directory = self.device_media_dir(MEDIA_TYPE_RECORDING, device_name)
        path = self.unique_path(directory, "SmartCast", ".mp4")
        creation = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = subprocess.Popen(
            [
                scrcpy_path,
                "-s", serial,
                "--no-window",
                "--record", str(path),
                "--no-audio",  # device-only recording avoids audio permission issues
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation,
        )
        # give scrcpy a moment; a bad serial dies immediately
        try:
            process.wait(timeout=2)
            raise RuntimeError("录屏启动失败：请确认设备在线且未授权问题")
        except subprocess.TimeoutExpired:
            pass
        self.recording_processes[serial] = process
        return self.add_record(
            MediaRecord(
                file_name=path.name,
                path=str(path),
                media_type=MEDIA_TYPE_RECORDING,
                device_name=device_name,
                serial=serial,
                created=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                size=0,
            )
        )

    def stop_recording(self, serial: str) -> MediaRecord | None:
        process = self.recording_processes.pop(serial, None)
        if process is None:
            raise RuntimeError("该设备没有正在进行的录屏")
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        record = self.find_latest_pending_recording(serial)
        if record is not None:
            record.size = Path(record.path).stat().st_size if Path(record.path).is_file() else 0
            self.save_history()
        return record

    def find_latest_pending_recording(self, serial: str) -> MediaRecord | None:
        for record in reversed(self.load_history()):
            if record.serial == serial and record.media_type == MEDIA_TYPE_RECORDING and record.size == 0:
                return record
        return None

    # ------------- history -------------
    def add_record(self, record: MediaRecord) -> MediaRecord:
        history = self.load_history()
        history.append(record)
        self._history = history
        self.save_history()
        return record

    def load_history(self) -> list[MediaRecord]:
        if self._history is not None:
            return self._history
        try:
            data = json.loads(self.history_path.read_text(encoding="utf-8"))
            records = [MediaRecord.from_dict(item) for item in data if isinstance(item, dict)]
        except (OSError, ValueError):
            records = []
        self._history = records
        return records

    def save_history(self) -> None:
        self.media_root.mkdir(parents=True, exist_ok=True)
        self.history_path.write_text(
            json.dumps([r.to_dict() for r in self.load_history()], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def delete_record(self, record: MediaRecord) -> None:
        history = self.load_history()
        self._history = [r for r in history if r.path != record.path or r.file_name != record.file_name]
        self.save_history()

    def delete_file_and_record(self, record: MediaRecord) -> None:
        try:
            Path(record.path).unlink(missing_ok=True)
        except OSError as error:
            raise RuntimeError(f"删除文件失败：{error}") from error
        self.delete_record(record)
