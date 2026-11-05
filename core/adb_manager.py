from dataclasses import dataclass

from utils.system_utils import resolve_tool, run_command
from utils.logger import setup_logger


@dataclass(frozen=True)
class RawDevice:
    serial: str
    state: str


class AdbError(Exception):
    pass


# ADB 服务端异常（客户端/服务端握手失败、服务未运行、端口被占用等）
SERVER_FAULT_MARKERS = (
    "protocol fault",
    "failed to check server version",
    "couldn't read status",
    "connection reset",
    "cannot connect to daemon",
    "failed to start daemon",
    "daemon not running",
    "connection refused",
)


def is_server_fault(message: str) -> bool:
    """判断错误是否属于 ADB 服务端故障（可尝试重启服务恢复）。"""
    text = (message or "").lower()
    return any(marker in text for marker in SERVER_FAULT_MARKERS)


def list_adb_processes() -> list[tuple[int, str]]:
    """列出系统中正在运行的 adb.exe 进程（PID, 可执行文件路径）。"""
    import json
    import subprocess

    try:
        completed = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "Get-CimInstance Win32_Process -Filter \"Name='adb.exe'\" | "
                "Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=12,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        text = (completed.stdout or "").strip()
        if not text:
            return []
        data = json.loads(text)
        if isinstance(data, dict):
            data = [data]
        result: list[tuple[int, str]] = []
        for item in data:
            try:
                result.append((int(item.get("ProcessId")), str(item.get("ExecutablePath") or "")))
            except (TypeError, ValueError):
                continue
        return result
    except Exception:
        return []


def kill_foreign_adb_processes(own_path: str) -> list[int]:
    """关闭不是本程序自带 adb 的其它 adb 进程。

    其它工具（Android Studio、手机助手等）自带的 adb 版本不同，
    会与本程序的服务端互相踢，导致 protocol fault / connection reset。
    """
    import os
    import subprocess

    own = os.path.normcase(os.path.abspath(own_path)) if own_path else ""
    killed: list[int] = []
    for pid, exe_path in list_adb_processes():
        path = os.path.normcase(os.path.abspath(exe_path)) if exe_path else ""
        if path and own and path == own:
            continue
        try:
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True,
                timeout=8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            killed.append(pid)
        except Exception:
            continue
    return killed


class AdbManager:
    def __init__(self, configured_path: str = "") -> None:
        self.logger = setup_logger()
        self.adb_path = resolve_tool(configured_path, "resources/adb", "adb")

    def start_server(self) -> None:
        code, _, error = run_command([self.adb_path, "start-server"], 10)
        if code == 127:
            raise AdbError(f"找不到 ADB：{self.adb_path}")
        if code not in (0, 1):
            raise AdbError(f"ADB Server 启动失败：{error or code}")

    def recover_server(self) -> bool:
        """受控重启 ADB Server（仅在检测到服务端故障时调用）。

        注意：重启会影响所有 ADB 连接，因此必须由调用方限制频率，
        不能每次扫描失败都执行。
        """
        self.logger.warning("ADB 服务端异常，尝试重启服务")
        try:
            killed = kill_foreign_adb_processes(self.adb_path)
            if killed:
                self.logger.warning("已关闭其它 adb 进程：%s", killed)
            run_command([self.adb_path, "kill-server"], 8)
            import time

            time.sleep(0.6)
            code, _, error = run_command([self.adb_path, "start-server"], 12)
            if code not in (0, 1):
                self.logger.error("ADB Server 重启失败：%s", (error or "").strip())
                return False
            self.logger.info("ADB Server 已重启")
            return True
        except Exception as exc:  # 恢复失败不应影响主流程
            self.logger.error("ADB Server 重启异常：%s", exc)
            return False

    def devices(self) -> list[RawDevice]:
        code, output, error = run_command([self.adb_path, "devices", "-l"], 5)
        if code != 0:
            raise AdbError(error or f"ADB devices failed ({code})")
        result: list[RawDevice] = []
        for line in output.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2:
                result.append(RawDevice(parts[0], parts[1]))
        return result

    def shell(self, serial: str, command: str, timeout: float = 5.0) -> str:
        code, output, error = run_command([self.adb_path, "-s", serial, "shell", command], timeout)
        if code != 0:
            raise AdbError(f"ADB shell {command} failed: {error or code}")
        return output.strip()
