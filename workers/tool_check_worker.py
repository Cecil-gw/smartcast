from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from utils.system_utils import resolve_tool, run_command


class ToolCheckThread(QThread):
    result = Signal(str, bool, str)

    def __init__(self, tool: str, configured_path: str = "") -> None:
        super().__init__()
        self.tool = tool
        self.configured_path = configured_path.strip()

    def run(self) -> None:
        if self.tool == "adb":
            self._check_adb()
        else:
            self._check_scrcpy()

    def _check_adb(self) -> None:
        path = self.configured_path or resolve_tool("", "resources/adb", "adb")
        if not Path(path).is_file():
            self.result.emit("adb", False, f"找不到 ADB：{path}")
            return
        code, output, error = run_command([path, "version"], 5.0)
        if code != 0:
            self.result.emit("adb", False, (error or output or "ADB 无法执行").strip())
            return
        version = next((line.strip() for line in output.splitlines() if "Android Debug Bridge" in line), "ADB 可用")
        server_code, _, server_error = run_command([path, "start-server"], 10.0)
        if server_code not in (0, 1):
            self.result.emit("adb", False, f"ADB Server 启动失败：{(server_error or str(server_code)).strip()}")
            return
        self.result.emit("adb", True, f"{version} · 服务正常")

    def _check_scrcpy(self) -> None:
        path = self.configured_path or resolve_tool("", "resources/scrcpy", "scrcpy")
        if not Path(path).is_file():
            self.result.emit("scrcpy", False, f"找不到 scrcpy：{path}")
            return
        code, output, error = run_command([path, "--version"], 5.0)
        if code != 0:
            self.result.emit("scrcpy", False, (error or output or "scrcpy 无法执行").strip())
            return
        version = next((line.strip() for line in output.splitlines() if line.strip().startswith("scrcpy ")), "scrcpy 可用")
        self.result.emit("scrcpy", True, version)
