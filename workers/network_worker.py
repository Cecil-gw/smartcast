from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from concurrent.futures import ThreadPoolExecutor

from core.adb_network_manager import AdbNetworkError, AdbNetworkManager, NetworkResult
from core.network_scanner import COMMON_PORTS, discover_serials


class NetworkConnectThread(QThread):
    finished_with_result = Signal(object)

    def __init__(self, manager: AdbNetworkManager, ip: str, port: int, parent=None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.ip = ip
        self.port = port

    def run(self) -> None:
        try:
            result = self.manager.connect(self.ip, self.port)
        except AdbNetworkError as error:
            result = NetworkResult(False, message=str(error))
        except Exception as error:  # never leave the caller waiting forever
            result = NetworkResult(False, message=f"连接过程发生异常：{error}")
        self.finished_with_result.emit(result)


class NetworkDisconnectThread(QThread):
    finished_with_result = Signal(object)

    def __init__(self, manager: AdbNetworkManager, ip: str, port: int, parent=None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.ip = ip
        self.port = port

    def run(self) -> None:
        try:
            result = self.manager.disconnect(self.ip, self.port)
        except AdbNetworkError as error:
            result = NetworkResult(False, message=str(error))
        except Exception as error:  # never leave the caller waiting forever
            result = NetworkResult(False, message=f"断开过程发生异常：{error}")
        self.finished_with_result.emit(result)


class LanScanThread(QThread):
    """Probe the local subnet across common ports, then connect in parallel.

    ``recent`` carries previously connected ``ip:port`` serials; they are
    probed first-class so devices on non-default ports (or Android 11+
    random wireless-debugging ports) reconnect instantly.
    """

    finished_with_result = Signal(list, list)  # found serials, connect results

    def __init__(
        self,
        manager: AdbNetworkManager,
        port: int = 5555,
        parent=None,
        recent: list[str] | None = None,
        ports: list[int] | None = None,
    ) -> None:
        super().__init__(parent)
        self.manager = manager
        self.port = port
        self.recent = [s for s in (recent or []) if isinstance(s, str)]
        self.ports = ports or COMMON_PORTS

    def run(self) -> None:
        try:
            serials = discover_serials(ports=self.ports, recent=self.recent)
        except Exception:
            serials = []
        results: list[NetworkResult] = []
        if serials:
            def connect_one(serial: str) -> NetworkResult:
                host, _, port_text = serial.rpartition(":")
                try:
                    return self.manager.connect(host, int(port_text))
                except AdbNetworkError as error:
                    return NetworkResult(False, serial=serial, message=str(error))
                except Exception as error:
                    return NetworkResult(False, serial=serial, message=f"连接过程发生异常：{error}")

            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(connect_one, serials))
        self.finished_with_result.emit(serials, results)


class ServerRestartThread(QThread):
    """User-triggered controlled ADB server restart (never automatic)."""

    finished_with_result = Signal(bool, str)

    def __init__(self, manager: AdbNetworkManager, parent=None) -> None:
        super().__init__(parent)
        self.manager = manager

    def run(self) -> None:
        try:
            ok, message = self.manager.restart_server()
        except Exception as error:
            ok, message = False, str(error)
        self.finished_with_result.emit(ok, message)
