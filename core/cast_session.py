from __future__ import annotations

import time
from dataclasses import dataclass, field


SESSION_STARTING = "starting"
SESSION_RUNNING = "running"
SESSION_STOPPING = "stopping"
SESSION_STOPPED = "stopped"
SESSION_ERROR = "error"
SESSION_DEVICE_OFFLINE = "device_offline"

STATE_LABELS = {
    SESSION_STARTING: "启动中",
    SESSION_RUNNING: "投屏中",
    SESSION_STOPPING: "停止中",
    SESSION_STOPPED: "已停止",
    SESSION_ERROR: "错误",
    SESSION_DEVICE_OFFLINE: "设备离线",
}


def format_duration(seconds: float) -> str:
    total = int(max(0, seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


@dataclass
class CastSession:
    """One scrcpy casting session; state is independent of ADB state."""

    serial: str
    model: str = "未知"
    connection_type: str = "usb"
    state: str = SESSION_STARTING
    pid: int | None = None
    started_monotonic: float = field(default_factory=time.monotonic)
    codec: str = "未知"
    bitrate_mbps: int | None = None
    resolution: str = "original"
    fps: int | None = None
    audio: bool = True
    turn_screen_off: bool = False
    error: str = ""

    def duration_seconds(self) -> float:
        if self.state in (SESSION_STOPPED, SESSION_ERROR, SESSION_DEVICE_OFFLINE):
            return 0.0
        return time.monotonic() - self.started_monotonic

    def duration_text(self) -> str:
        return format_duration(self.duration_seconds())

    def params_text(self) -> str:
        codec = self.codec or "未知"
        bitrate = f"{self.bitrate_mbps}Mbps" if self.bitrate_mbps else "未知"
        resolution = "原始" if self.resolution in ("original", "auto") else self.resolution
        fps = f"{self.fps}fps" if self.fps else "不限制"
        extras = []
        if not self.audio:
            extras.append("无声")
        if self.turn_screen_off:
            extras.append("熄屏")
        tail = (" · " + " · ".join(extras)) if extras else ""
        return f"{codec} · {bitrate} · {resolution} · {fps}{tail}"

    def connection_label(self) -> str:
        return "Wi-Fi" if self.connection_type == "wifi" else ("模拟器" if self.connection_type == "emulator" else "USB")

    def state_label(self) -> str:
        return STATE_LABELS.get(self.state, self.state)
