from __future__ import annotations

import re
from dataclasses import dataclass

from utils.system_utils import run_command
from utils.logger import setup_logger


CONNECT_TIMEOUT = 10.0
DISCONNECT_TIMEOUT = 5.0
VERIFY_TIMEOUT = 4.0


@dataclass(frozen=True)
class NetworkResult:
    success: bool
    already_connected: bool = False
    serial: str = ""
    message: str = ""
    state: str = ""
    server_error: bool = False


class AdbNetworkError(Exception):
    """Raised when the ADB executable cannot be used at all."""


def validate_ip(value: str) -> str | None:
    """Return an error message when *value* is not a valid IPv4 address."""
    text = (value or "").strip()
    if not text:
        return "请输入 IP 地址"
    parts = text.split(".")
    if len(parts) != 4:
        return "IP 地址格式不正确，例如 192.168.1.23"
    for part in parts:
        if not part.isdigit() or not 0 <= int(part) <= 255 or (len(part) > 1 and part.startswith("0")):
            return "IP 地址格式不正确，例如 192.168.1.23"
    return None


def validate_port(value: str) -> tuple[int | None, str | None]:
    text = (value or "").strip()
    if not text:
        return None, "请输入端口"
    if not text.isdigit():
        return None, "端口必须是数字"
    port = int(text)
    if not 1 <= port <= 65535:
        return None, "端口范围为 1～65535"
    return port, None


def parse_address(text: str) -> tuple[str | None, int | None, str | None]:
    """Parse ``IP`` or ``IP:PORT`` input; returns (ip, port, error)."""
    raw = (text or "").strip()
    if not raw:
        return None, None, "请输入连接地址"
    if ":" in raw:
        host, _, port_text = raw.rpartition(":")
        if validate_ip(host):
            return None, None, validate_ip(host)
        port, port_error = validate_port(port_text)
        if port_error:
            return None, None, port_error
        return host, port, None
    if validate_ip(raw):
        return None, None, validate_ip(raw)
    return raw, None, None


class AdbNetworkManager:
    """Thin wrapper around ``adb connect`` / ``adb disconnect``."""

    def __init__(self, adb_path: str) -> None:
        self.adb_path = adb_path
        self.logger = setup_logger()

    # ------------------------------------------------------------------
    def connect(self, ip: str, port: int | str, timeout: float = CONNECT_TIMEOUT) -> NetworkResult:
        ip_error = validate_ip(str(ip))
        if ip_error:
            return NetworkResult(False, message=ip_error)
        port_value, port_error = validate_port(str(port))
        if port_error:
            return NetworkResult(False, message=port_error)
        serial = f"{str(ip).strip()}:{port_value}"
        self.logger.info("adb connect %s", serial)
        code, output, error = run_command([self.adb_path, "connect", serial], timeout)
        text = " ".join((output or "").split()) or " ".join((error or "").split())
        lowered = text.lower()

        if code == 127 or "executable not found" in lowered:
            raise AdbNetworkError(f"找不到 ADB：{self.adb_path}")
        if code == 124 or "command timed out" in lowered:
            return NetworkResult(False, serial=serial, message="连接超时，请确认手机与电脑处于同一局域网且已开启 ADB 网络调试")
        if "cannot connect to daemon" in lowered or "failed to start daemon" in lowered or "daemon not running" in lowered:
            return NetworkResult(False, serial=serial, message="ADB Server 未启动或异常，可尝试重启 ADB Server", server_error=True)

        already = "already connected to" in lowered
        reported = "connected to" in lowered
        if "failed to connect to" in lowered or "cannot connect to" in lowered:
            return NetworkResult(False, serial=serial, message=self._connect_failure_message(text, lowered))
        if "more than one" in lowered:
            return NetworkResult(False, serial=serial, message=text or "存在多个设备，请使用具体序列号")
        if lowered.startswith("error:") or lowered.startswith("adb: error"):
            return NetworkResult(False, serial=serial, message=text or "ADB 返回错误")

        if already or reported:
            # adb connect saying "connected" is not enough: confirm the device
            # actually shows up as usable before declaring success.
            return self._verify_state(serial, already_connected=already)
        if code == 0:
            if self._serial_present(serial):
                return self._verify_state(serial)
            return NetworkResult(
                False,
                serial=serial,
                state="disconnected",
                message="设备未出现在 ADB 列表中，连接未生效",
            )

        return NetworkResult(False, serial=serial, message=text or f"连接失败（退出码 {code}）")

    # ------------------------------------------------------------------
    def _connect_failure_message(self, text: str, lowered: str) -> str:
        if "10060" in lowered or "timed out" in lowered or "timeout" in lowered:
            return "连接超时（10060），请检查手机与电脑是否在同一 Wi-Fi 网络"
        if "10061" in lowered or "refused" in lowered:
            return "连接被拒绝（10061），请确认手机已开启 ADB 网络调试且端口正确"
        if "10013" in lowered:
            return "连接失败（10013）：端口被占用或防火墙拦截，请检查 Windows 防火墙设置"
        if "10065" in lowered or "unreachable" in lowered:
            return "网络不可达（10065），请确认手机与电脑处于同一局域网"
        return text or "连接失败，请确认手机已开启 ADB 网络调试"

    # ------------------------------------------------------------------
    def _verify_state(self, serial: str, already_connected: bool = False) -> NetworkResult:
        state = self._device_state(serial)
        if state == "unauthorized":
            return NetworkResult(False, already_connected=already_connected, serial=serial, state=state, message="设备未授权：请在手机上允许「USB 调试」授权弹窗")
        if state == "offline":
            return NetworkResult(False, already_connected=already_connected, serial=serial, state=state, message="设备显示 offline：请尝试在手机上撤销授权后重新连接")
        if state != "device":
            return NetworkResult(False, already_connected=already_connected, serial=serial, state=state or "disconnected", message="设备未出现在 ADB 列表中，连接可能已立即断开")
        # The device is listed as usable; double-check the shell actually responds.
        code, output, error = run_command([self.adb_path, "-s", serial, "shell", "echo smartcast_ok"], VERIFY_TIMEOUT)
        if code != 0 or "smartcast_ok" not in (output or ""):
            detail = " ".join((error or "").split())
            self.logger.warning("Shell check failed for %s: %s", serial, detail)
            return NetworkResult(
                False,
                serial=serial,
                state=state,
                message="设备已连接但无响应，请重新插拔或在手机上撤销 USB 调试授权后重试",
            )
        verb = "设备已连接" if already_connected else "连接成功"
        return NetworkResult(True, already_connected=already_connected, serial=serial, state=state, message=verb)

    # ------------------------------------------------------------------
    def _device_state(self, serial: str) -> str:
        code, output, _ = run_command([self.adb_path, "devices"], 5.0)
        if code != 0:
            return ""
        for line in output.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[0] == serial:
                return parts[1]
        return ""

    def _serial_present(self, serial: str) -> bool:
        return bool(self._device_state(serial))

    # ------------------------------------------------------------------
    def disconnect(self, ip: str, port: int | str, timeout: float = DISCONNECT_TIMEOUT) -> NetworkResult:
        ip_error = validate_ip(str(ip))
        if ip_error:
            return NetworkResult(False, message=ip_error)
        port_value, port_error = validate_port(str(port))
        if port_error:
            return NetworkResult(False, message=port_error)
        serial = f"{str(ip).strip()}:{port_value}"
        self.logger.info("adb disconnect %s", serial)
        code, output, error = run_command([self.adb_path, "disconnect", serial], timeout)
        text = " ".join((output or "").split()) or " ".join((error or "").split())
        lowered = text.lower()
        if code == 127 or "executable not found" in lowered:
            raise AdbNetworkError(f"找不到 ADB：{self.adb_path}")
        if "disconnected" in lowered:
            return NetworkResult(True, serial=serial, message=text or "已断开连接")
        if "not found" in lowered:
            return NetworkResult(True, serial=serial, message="设备本来就不在线")
        if code == 0:
            return NetworkResult(True, serial=serial, message=text or "已断开连接")
        return NetworkResult(False, serial=serial, message=text or f"断开失败（退出码 {code}）")

    def restart_server(self, timeout: float = 10.0) -> tuple[bool, str]:
        """Controlled recovery: explicitly requested by the user only."""
        code, output, error = run_command([self.adb_path, "start-server"], timeout)
        if code == 127:
            return False, f"找不到 ADB：{self.adb_path}"
        if code not in (0, 1):
            return False, (error or output or f"ADB Server 重启失败（{code}）").strip()
        return True, "ADB Server 已启动（不会中断现有设备连接）"
