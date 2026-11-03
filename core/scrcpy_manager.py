from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal

from core.cast_session import (
    SESSION_DEVICE_OFFLINE,
    SESSION_ERROR,
    SESSION_RUNNING,
    SESSION_STARTING,
    SESSION_STOPPED,
    SESSION_STOPPING,
    CastSession,
)
from core.device_info import CONNECTION_USB, DeviceInfo, connection_type_for_serial
from utils.logger import setup_logger
from utils.system_utils import resolve_tool


class ScrcpyManager(QObject):
    casting_started = Signal(str)
    sessions_changed = Signal()
    casting_failed = Signal(str, str)
    casting_stopped = Signal(str, int)

    def __init__(self, configured_path: str = "", adb_path: str = "", render_driver: str = "opengl") -> None:
        super().__init__()
        self.scrcpy_path = resolve_tool(configured_path, "resources/scrcpy", "scrcpy")
        self.adb_path = resolve_tool(adb_path, "resources/adb", "adb")
        self.render_driver = render_driver or "opengl"
        self.logger = setup_logger()
        self.processes: dict[str, QProcess] = {}
        self._started: set[str] = set()
        self._failed: set[str] = set()
        self._stopping: set[str] = set()
        self._retried_opengl: set[str] = set()
        self._activated: set[str] = set()
        self._start_requests: dict[str, dict] = {}
        self._device_models: dict[str, str] = {}
        self._fullscreen: set[int] = set()
        self.sessions: dict[str, CastSession] = {}

    def build_command(
        self,
        serial: str,
        codec: str,
        resolution: str,
        fps: int,
        bitrate_mbps: int,
        audio: bool = True,
        render_driver: str | None = None,
        window_title: str | None = None,
        turn_screen_off: bool = False,
    ) -> list[str]:
        command = ["-s", serial]
        if turn_screen_off:
            command += ["--turn-screen-off"]
        if codec and codec.lower() != "auto":
            command += ["--video-codec", codec.lower().replace(".", "")]
        command += ["--video-bit-rate", f"{bitrate_mbps}M"]
        if fps > 0:
            command += ["--max-fps", str(fps)]
        if resolution.isdigit():
            command += ["--max-size", resolution]
        if not audio:
            command += ["--no-audio"]
        driver = self.render_driver if render_driver is None else render_driver
        if driver and driver != "auto":
            command += ["--render-driver", driver]
        if window_title:
            command += ["--window-title", window_title]
        return command

    def start(
        self,
        device: DeviceInfo,
        codec: str,
        resolution: str,
        fps: int,
        bitrate_mbps: int,
        audio: bool = True,
        render_driver: str | None = None,
        turn_screen_off: bool = False,
    ) -> bool:
        serial = device.serial
        existing = self.processes.get(serial)
        if existing and existing.state() in (QProcess.Starting, QProcess.Running):
            return True
        if device.state != "device" or not Path(self.scrcpy_path).is_file():
            return False
        driver = render_driver or self.render_driver
        model = device.model if device.model and device.model != "未知" else "SmartCast"
        title = f"{model} · {serial[-4:]}"
        command = self.build_command(serial, codec, resolution, fps, bitrate_mbps, audio, driver, title, turn_screen_off)
        self.logger.info("Starting scrcpy for %s: %s", serial, command)
        self._device_models[serial] = device.model
        self.sessions[serial] = CastSession(
            serial=serial,
            model=device.model,
            connection_type=device.connection_type or connection_type_for_serial(serial),
            state=SESSION_STARTING,
            codec=codec,
            bitrate_mbps=bitrate_mbps,
            resolution=resolution,
            fps=fps,
            audio=audio,
            turn_screen_off=turn_screen_off,
        )
        self.sessions_changed.emit()
        self._start_requests[serial] = {
            "device": device,
            "codec": codec,
            "resolution": resolution,
            "fps": fps,
            "bitrate_mbps": bitrate_mbps,
            "audio": audio,
            "render_driver": driver,
        }
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.SeparateChannels)
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("ADB", self.adb_path)
        process.setProcessEnvironment(environment)
        process.readyReadStandardOutput.connect(lambda: self._consume_output(serial, process, False))
        process.readyReadStandardError.connect(lambda: self._consume_output(serial, process, True))
        process.started.connect(lambda: self._on_started(serial, process))
        process.finished.connect(lambda code, status: self._finished(serial, process, code, status))
        process.errorOccurred.connect(lambda error: self._error(serial, process, error))
        self.processes[serial] = process
        self._stopping.discard(serial)
        self._failed.discard(serial)
        self._started.discard(serial)
        self._retried_opengl.discard(serial)
        self._activated.discard(serial)
        process.start(self.scrcpy_path, command)
        return True

    def stop(self, serial: str) -> None:
        process = self.processes.get(serial)
        if not process or process.state() == QProcess.NotRunning:
            # No live process: converge the session state so it never
            # stays in starting/stopping forever.
            session = self.sessions.get(serial)
            if session is not None and session.state not in (SESSION_STOPPED, SESSION_ERROR, SESSION_DEVICE_OFFLINE):
                session.state = SESSION_STOPPED
                self.sessions_changed.emit()
            return
        self.logger.info("Stopping scrcpy for %s", serial)
        session = self.sessions.get(serial)
        if session is not None and session.state in (SESSION_STARTING, SESSION_RUNNING):
            session.state = SESSION_STOPPING
            self.sessions_changed.emit()
        self._stopping.add(serial)
        process.terminate()

        def force_kill() -> None:
            try:
                if self.processes.get(serial) is process and process.state() != QProcess.NotRunning:
                    process.kill()
            except RuntimeError:
                pass

        QTimer.singleShot(2500, force_kill)

    def _on_started(self, serial: str, process: QProcess) -> None:
        session = self.sessions.get(serial)
        if session is not None:
            session.state = SESSION_RUNNING
            session.pid = process.processId()
            session.started_monotonic = __import__("time").monotonic()
            self.sessions_changed.emit()
        if self.processes.get(serial) is not process:
            return
        self._started.add(serial)
        self._failed.discard(serial)
        self._retried_opengl.discard(serial)
        self.logger.info("scrcpy started for %s", serial)
        self._boost_pid(process.processId())
        for delay in (500, 1200, 2200, 3500, 5500, 8000):
            QTimer.singleShot(delay, lambda s=serial: self._activate_window(s))
        self.casting_started.emit(serial)

    def _error(self, serial: str, process: QProcess, error) -> None:
        session = self.sessions.get(serial)
        if session is not None:
            session.state = SESSION_ERROR
            session.error = self._error_message(error)
            self.sessions_changed.emit()
        if self.processes.get(serial) is not process:
            return
        message = self._error_message(error)
        self.logger.error("scrcpy %s error: %s", serial, message)
        if serial in self._stopping or serial in self._started:
            return
        request = self._start_requests.get(serial)
        if request and request.get("render_driver") == "opengl" and serial not in self._retried_opengl:
            self._retried_opengl.add(serial)
            self.logger.warning("OpenGL 渲染启动失败，正在回退到自动渲染后端")
            self.processes.pop(serial, None)
            self._failed.discard(serial)
            fallback = dict(request)
            fallback["render_driver"] = "auto"
            self.start(**fallback)
            return
        if serial in self._failed:
            return
        self._failed.add(serial)
        self.processes.pop(serial, None)
        self.casting_failed.emit(serial, message)

    def _finished(self, serial: str, process: QProcess, code: int, status) -> None:
        if self.processes.get(serial) is not process:
            return
        self.processes.pop(serial, None)
        self._started.discard(serial)
        self._start_requests.pop(serial, None)
        self._activated.discard(serial)
        self._retried_opengl.discard(serial)
        self._device_models.pop(serial, None)
        failed = serial in self._failed
        self._failed.discard(serial)
        intentional = serial in self._stopping
        self._stopping.discard(serial)
        level = self.logger.info if code == 0 else self.logger.error
        level("scrcpy %s exited code=%s status=%s", serial, code, status)
        session = self.sessions.get(serial)
        if session is not None:
            session.state = SESSION_ERROR if (failed and not intentional) else SESSION_STOPPED
            if failed and not intentional:
                session.error = f"进程异常退出（代码 {code}）"
            self.sessions_changed.emit()
        if not failed or intentional:
            self.casting_stopped.emit(serial, 0 if intentional else code)

    def _consume_output(self, serial: str, process: QProcess, is_error: bool) -> None:
        raw = process.readAllStandardError() if is_error else process.readAllStandardOutput()
        text = bytes(raw).decode("utf-8", errors="replace").strip()
        if text:
            (self.logger.error if is_error else self.logger.info)("scrcpy %s: %s", serial, text)

    def _boost_pid(self, pid: int) -> None:
        if sys.platform != "win32" or not pid:
            return
        try:
            import ctypes

            handle = ctypes.windll.kernel32.OpenProcess(0x0200 | 0x0400, False, int(pid))
            if handle:
                ctypes.windll.kernel32.SetPriorityClass(handle, 0x00008000)
                ctypes.windll.kernel32.CloseHandle(handle)
                self.logger.info("Raised scrcpy process priority for pid %s", pid)
        except Exception as error:
            self.logger.debug("Unable to raise scrcpy priority: %s", error)

    def _activate_window(self, serial: str) -> None:
        """Bring the scrcpy window to front and raise its priority."""
        if sys.platform != "win32" or serial in self._activated:
            return
        hwnd = self._find_window(serial)
        if not hwnd:
            return
        try:
            import ctypes

            user32 = ctypes.windll.user32

            class_name = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, class_name)
            length = user32.GetWindowTextLengthW(hwnd)
            title = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, title, length + 1)
            owner = wintypes_pid = None
            import ctypes.wintypes as wt
            owner = wt.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            self._boost_pid(int(owner.value))
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, 9)
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0043)
            user32.BringWindowToTop(hwnd)
            activated = bool(user32.SetForegroundWindow(hwnd))
            if not activated:
                user32.SwitchToThisWindow(hwnd, True)
            self._activated.add(serial)
            self.logger.info("Activated scrcpy window for %s (pid %s)", serial, int(owner.value))
        except Exception as error:
            self.logger.debug("Unable to activate scrcpy window: %s", error)

    def toggle_fullscreen(self, serial: str) -> bool:
        """Toggle borderless fullscreen on the scrcpy window of *serial*."""
        if sys.platform != "win32":
            return False
        hwnd = self._find_window(serial)
        if not hwnd:
            return False
        import ctypes

        GWL_STYLE = -16
        SWP_FRAMECHANGED = 0x0020
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        WS_CAPTION = 0x00C00000
        WS_THICKFRAME = 0x00040000
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        if style & WS_CAPTION:
            user32.SetWindowLongW(hwnd, GWL_STYLE, style & ~(WS_CAPTION | WS_THICKFRAME))
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_FRAMECHANGED)
            user32.SetWindowPos(hwnd, 0, 0, 0,
                                user32.GetSystemMetrics(0), user32.GetSystemMetrics(1),
                                SWP_FRAMECHANGED)
            self._fullscreen.add(hwnd)
        else:
            user32.SetWindowLongW(hwnd, GWL_STYLE, style | WS_CAPTION | WS_THICKFRAME)
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_FRAMECHANGED)
            self._fullscreen.discard(hwnd)
        return True

    def is_fullscreen(self, serial: str) -> bool:
        hwnd = self._find_window(serial)
        return hwnd in getattr(self, "_fullscreen", set())

    def _find_window(self, serial: str) -> int:
        """Locate the scrcpy main window for *serial*.

        Primary: match by process PID (works regardless of window class,
        e.g. scrcpy 5 uses SDL3 instead of SDL_app). Fallback: title match.
        """
        import ctypes
        from ctypes import wintypes

        if sys.platform != "win32":
            return 0
        user32 = ctypes.windll.user32
        session = self.sessions.get(serial)
        pid = session.pid if session is not None else None

        result = [0]
        enum_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        def by_pid(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            owner = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == pid:
                result[0] = hwnd
                return False
            return True

        if pid:
            user32.EnumWindows(enum_type(by_pid), 0)
            if result[0]:
                return result[0]

        # fallback: legacy title/class matching
        suffix = serial[-4:]
        model = self._device_models.get(serial, "")

        def by_title(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            class_name = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, class_name)
            if class_name.value != "SDL_app":
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            title = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, title, length + 1)
            if suffix in title.value or (model and model not in {"未知", ""} and model in title.value):
                result[0] = hwnd
                return False
            return True

        user32.EnumWindows(enum_type(by_title), 0)
        return result[0]

    def mark_device_offline(self, serial: str) -> None:
        session = self.sessions.get(serial)
        if session is not None and session.state not in (SESSION_STOPPED, SESSION_ERROR):
            session.state = SESSION_DEVICE_OFFLINE
            session.error = "设备离线"
            self.sessions_changed.emit()

    def active_sessions(self) -> list[CastSession]:
        return [
            s for s in self.sessions.values()
            if s.state not in (SESSION_STOPPED, SESSION_ERROR, SESSION_DEVICE_OFFLINE)
        ]

    def is_running(self, serial: str) -> bool:
        process = self.processes.get(serial)
        return bool(process and process.state() == QProcess.Running)

    def stop_all(self) -> None:
        for serial in list(self.processes):
            self.stop(serial)

    def shutdown(self) -> None:
        for process in list(self.processes.values()):
            try:
                if process.state() != QProcess.NotRunning:
                    process.kill()
                    process.waitForFinished(1000)
            except RuntimeError:
                pass
        self.processes.clear()
        self._started.clear()
        self._failed.clear()
        self._stopping.clear()
        self._retried_opengl.clear()
        self._activated.clear()
        self._start_requests.clear()
