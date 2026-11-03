from dataclasses import dataclass

from utils.system_utils import resolve_tool, run_command
from utils.logger import setup_logger


@dataclass(frozen=True)
class RawDevice:
    serial: str
    state: str


class AdbError(Exception):
    pass


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
