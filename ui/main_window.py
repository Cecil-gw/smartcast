from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QThread, QTime, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QMainWindow, QMessageBox, QSizeGrip, QStackedWidget, QVBoxLayout, QWidget

from core.adb_manager import AdbManager
from core.adb_network_manager import AdbNetworkManager
from core.device_control import DeviceControlManager, ScreenBackup, ScreenControlManager
from core.device_info import DeviceInfo
from core.encoder_detector import EncoderDetector
from core.media_manager import MediaManager
from core.scrcpy_manager import ScrcpyManager
from ui.components.sidebar import Sidebar
from ui.components.cast_toolbar import CastToolBar
from ui.components.title_bar import TitleBar
from ui.components.status_bar import StatusBar
from ui.components.toast import Toast
from ui.dialogs import FaqDialog
from ui.network_connect_dialog import NetworkConnectDialog
from ui.log_bridge import LogEmitter, QtLogHandler
from ui.pages.cast_settings_page import CastSettingsPage
from ui.pages.device_page import DevicePage
from ui.pages.detail_page import DetailPage
from ui.pages.guide_page import GuidePage
from ui.pages.media_page import MediaPage
from ui.pages.sessions_page import SessionsPage
from ui.pages.log_page import LogPage
from ui.pages.overview_page import OverviewPage
from ui.pages.settings_page import SettingsPage
from ui.settings_dialog import DeviceSettingsDialog
from ui.theme import stylesheet_for
from utils.config_manager import ConfigManager
from utils.logger import LOG_DIR, setup_logger
from utils.system_utils import resolve_tool
from workers.detection_worker import EncoderDetectionThread
from workers.device_worker import DeviceWorker
from workers.network_worker import LanScanThread, NetworkConnectThread, NetworkDisconnectThread, ServerRestartThread
from workers.control_worker import ControlCommandThread
from workers.media_worker import RecordControlThread, ScreenshotThread
from workers.screen_worker import ScreenCommandThread
from workers.tool_check_worker import ToolCheckThread


class _NullHeaderBar(QObject):
    """Stub replacing the removed top status row (ADB chip / device count)."""

    settings_requested = Signal()

    class _DummyButton:
        def setEnabled(self, enabled: bool) -> None:
            pass

    def __init__(self) -> None:
        super().__init__()
        self.settings_button = self._DummyButton()

    def set_device_count(self, count: int) -> None:
        pass

    def set_adb_status(self, ok: bool, text: str) -> None:
        pass

    def set_context(self, text: str) -> None:
        pass


class MainWindow(QMainWindow):
    CASTING_SCAN_INTERVAL = 15

    def __init__(self, config: ConfigManager | None = None) -> None:
        super().__init__()
        self.logger = setup_logger()
        self.config = config or ConfigManager()
        self.adb = AdbManager(self.config.settings["adb_path"])
        self.detector = EncoderDetector(self.adb)
        self.scrcpy = ScrcpyManager(
            self.config.settings["scrcpy_path"],
            self.adb.adb_path,
            self.config.settings.get("render_driver", "opengl"),
        )
        self.base_scan_interval = int(self.config.settings["scan_interval"])
        self.casting_scan_interval = int(self.config.settings["casting_scan_interval"])
        self.auto_scan_enabled = bool(self.config.settings["auto_scan"])
        self.network = AdbNetworkManager(self.adb.adb_path)
        self.control = DeviceControlManager(self.adb)
        self.screen = ScreenControlManager(self.adb)
        self.media = MediaManager(self.adb.adb_path)
        self._media_threads: set = set()
        self._recording_serials: set[str] = set()
        self._screen_backups: dict[str, ScreenBackup] = {}
        self._screen_threads: dict[str, ScreenCommandThread] = {}
        self._control_threads: dict[str, ControlCommandThread] = {}
        self._network_dialog: NetworkConnectDialog | None = None
        self._network_threads: set = set()
        self.worker = DeviceWorker(self.adb, self.base_scan_interval)
        self.worker.enabled = self.auto_scan_enabled
        self.device_thread = QThread(self)
        self.worker.moveToThread(self.device_thread)
        self.current_devices: dict[str, DeviceInfo] = {}
        self.codecs: dict[str, list] = {}
        self.cast_states: dict[str, str] = {}
        self.pending_starts: set[str] = set()
        self.detection_threads: dict[str, EncoderDetectionThread] = {}
        self.tool_threads: dict[str, ToolCheckThread] = {}
        self._fallback_notices: dict[str, bool] = {}
        self._last_scan_ok: bool | None = None
        self.detail_serial: str | None = None
        self._log_handler: QtLogHandler | None = None
        self._build_ui()
        self.cards = self.device_page.cards
        self.status_label = self.status_bar.message_label
        self._connect_signals()
        self.apply_theme()
        self.log_page.load_recent(LOG_DIR / "smartcast.log")
        self._setup_log_bridge()
        self.cast_page.load_defaults(self.config.settings["default_parameters"])
        self.device_page.set_auto_scan(self.auto_scan_enabled, self.base_scan_interval)
        self.settings_page.load(self.config.settings)
        self.device_thread.start()
        QMetaObject.invokeMethod(self.worker, "start", Qt.QueuedConnection)
        self.logger.info("SmartCast UI ready")

    def _build_ui(self) -> None:
        self.setWindowTitle("SmartCast")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1280, 820)
        self.setMinimumSize(900, 640)
        central = QWidget()
        central.setObjectName("RootShell")
        shell = QHBoxLayout(central)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self.status_bar = StatusBar()
        self.sidebar = Sidebar(self.status_bar)
        shell.addWidget(self.sidebar)

        content = QWidget()
        root = QVBoxLayout(content)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.title_bar = TitleBar("SmartCast")
        root.addWidget(self.title_bar)
        self.header = _NullHeaderBar()

        self.stack = QStackedWidget()
        self.overview_page = OverviewPage()
        self.device_page = DevicePage()
        self.sessions_page = SessionsPage()
        self.media_page = MediaPage()
        self.cast_page = CastSettingsPage()
        self.guide_page = GuidePage()
        self.settings_page = SettingsPage()
        self.detail_page = DetailPage()
        self.log_page = LogPage()
        self.stack.addWidget(self.overview_page)
        self.stack.addWidget(self.device_page)
        self.stack.addWidget(self.sessions_page)
        self.stack.addWidget(self.media_page)
        self.stack.addWidget(self.cast_page)
        self.stack.addWidget(self.guide_page)
        self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self.detail_page)
        self.stack.addWidget(self.log_page)
        root.addWidget(self.stack, 1)
        shell.addWidget(content, 1)
        self.setCentralWidget(central)
        self._size_grip = QSizeGrip(central)
        self._size_grip.setFixedSize(16, 16)
        self._size_grip.raise_()
        self.toast = Toast(central)

    def _connect_signals(self) -> None:
        self.title_bar.minimize_requested.connect(self.showMinimized)
        self.title_bar.maximize_toggled.connect(self._toggle_maximize)
        self.title_bar.close_requested.connect(self.close)
        self.header.settings_requested.connect(self.open_settings)
        self.sidebar.navigation_requested.connect(self._navigate)
        self.overview_page.scan_requested.connect(self.request_scan)
        self.overview_page.screen_op_requested.connect(self._on_screen_op_routed)
        self.overview_page.screen_off_cast_requested.connect(self._start_screen_off_cast)
        self.overview_page.fullscreen_requested.connect(self._toggle_fullscreen)
        self.overview_page.screenshot_requested.connect(self._take_screenshot)
        self.overview_page.control_requested.connect(self._run_device_control)
        self.overview_page.record_requested.connect(self._toggle_recording)
        self.overview_page.help_requested.connect(self.show_help)
        self.overview_page.manage_requested.connect(self.show_device_page)
        self.overview_page.cast_requested.connect(lambda: self._navigate("cast"))
        self.overview_page.settings_requested.connect(self.open_settings)
        self.overview_page.start_requested.connect(self.start_cast)
        self.overview_page.stop_requested.connect(self.stop_cast)
        self.overview_page.details_requested.connect(self.show_details)
        self.overview_page.settings_for_device_requested.connect(self.save_device_defaults)
        self.overview_page.serial_copied.connect(self.copy_serial)
        self.device_page.start_requested.connect(self.start_cast)
        self.device_page.stop_requested.connect(self.stop_cast)
        self.device_page.details_requested.connect(self.show_details)
        self.device_page.settings_requested.connect(self.save_device_defaults)
        self.device_page.copy_requested.connect(self.copy_serial)
        self.device_page.refresh_requested.connect(self.request_scan)
        self.device_page.help_requested.connect(self.show_help)
        self.device_page.auto_scan_changed.connect(self._auto_scan_changed)
        self.device_page.network_connect_requested.connect(self.open_network_dialog)
        self.device_page.disconnect_requested.connect(self._disconnect_network_device)
        self.cast_page.quick_config.applied.connect(self.apply_default_parameters)
        self.settings_page.back_requested.connect(self.show_device_page)
        self.settings_page.save_requested.connect(self.save_settings)
        self.settings_page.reset_requested.connect(self.reset_settings)
        self.settings_page.detect_adb_requested.connect(lambda path: self.check_tool("adb", path, notify=True))
        self.settings_page.detect_scrcpy_requested.connect(lambda path: self.check_tool("scrcpy", path, notify=True))

        self.detail_page.back_requested.connect(self.show_device_page)
        self.detail_page.start_requested.connect(self.start_cast)
        self.detail_page.stop_requested.connect(self.stop_cast)
        self.detail_page.settings_requested.connect(self.save_device_defaults)
        self.detail_page.copy_requested.connect(self.copy_serial)
        self.detail_page.redetect_requested.connect(self.redetect_codecs)
        self.log_page.back_requested.connect(self.show_device_page)
        self.log_page.open_logs_requested.connect(self.open_logs)
        self.log_page.clear_logs_requested.connect(self.clear_interface_logs)
        self.log_page.export_logs_requested.connect(self.export_logs)
        self.worker.devices_changed.connect(self.refresh_devices)
        self.scrcpy.casting_started.connect(self._scrcpy_started)
        self.scrcpy.casting_failed.connect(self._scrcpy_failed)
        self.scrcpy.casting_stopped.connect(self._casting_stopped)
        self.scrcpy.sessions_changed.connect(self._on_sessions_changed)
        self.sessions_page.stop_requested.connect(self.stop_cast)
        self.sessions_page.fullscreen_requested.connect(self._toggle_fullscreen)
        self.media_page.open_file_requested.connect(self._open_media_file)
        self.media_page.open_folder_requested.connect(self._open_media_folder)
        self.media_page.delete_record_requested.connect(self._delete_media_record)
        self.media_page.delete_file_requested.connect(self._delete_media_file)

    def _setup_log_bridge(self) -> None:
        self.log_emitter = LogEmitter()
        self.log_emitter.message.connect(self._append_log)
        self._log_handler = QtLogHandler(self.log_emitter)
        self._log_handler.setLevel(logging.INFO)
        self.logger.addHandler(self._log_handler)

    def refresh_devices(self, devices, message: str) -> None:
        devices = list(devices)
        previous = self.current_devices
        current = {device.serial: device for device in devices}
        removed = [serial for serial in previous if serial not in current]
        self.current_devices = current
        self.device_page.set_devices(devices)
        self.overview_page.set_device_cards(devices, self.cast_states)

        if removed:
            for serial in removed:
                info = previous[serial]
                self.codecs.pop(serial, None)
                self.cast_states.pop(serial, None)
                self.pending_starts.discard(serial)
                self._fallback_notices.pop(serial, None)
                self.scrcpy.mark_device_offline(serial)
                self.scrcpy.stop(serial)
                self.toast.show_message(f"设备已断开：{info.manufacturer} {info.model}", "warning")
            if self.detail_serial in removed:
                self.show_device_page()

        for device in devices:
            state = self.cast_states.get(device.serial)
            if state == "running" and not self.scrcpy.is_running(device.serial):
                state = "idle"
            state = state or "idle"
            self.cast_states[device.serial] = state
            self.device_page.set_card_casting(device.serial, state)
            if device.serial in self.codecs:
                self.device_page.set_card_codecs(device.serial, self.codecs[device.serial])
            if device.state == "device" and device.serial not in self.codecs and device.serial not in self.detection_threads:
                self._detect_codecs(device)
            if self.detail_serial == device.serial and previous.get(device.serial) != device:
                self.detail_page.set_device(device, self.codecs.get(device.serial, []), state)

        online = sum(1 for device in devices if device.state == "device")
        self.header.set_device_count(len(devices))
        self.device_page.count_pill.setText(f"{online} 台在线" if devices else "暂无设备")
        self.status_bar.set_casting_count(self._active_cast_count())
        self.overview_page.set_devices(len(devices), online)
        self.overview_page.set_casting(self._active_cast_count())
        primary = next((device for device in devices if device.state == "device"), devices[0] if devices else None)
        if primary is None:
            self.overview_page.set_primary_device(None, [])
            self.overview_page.set_device_cards(devices, self.cast_states)
        else:
            state = self.cast_states.get(primary.serial, "idle")
            self.overview_page.set_primary_device(primary, self.codecs.get(primary.serial, []), state)
        now = QTime.currentTime().toString("HH:mm:ss")
        scan_ok = message == "设备扫描完成"
        was_ok = self._last_scan_ok
        if scan_ok:
            adb_text = "ADB 已连接"
            self.header.set_adb_status(True, adb_text)
            self.device_page.set_adb_status(True, "ADB 服务正常")
            self.status_bar.set_adb(True, "ADB 已连接")
            self.status_bar.set_scan(f"扫描完成 · {now}")
            self.overview_page.set_adb(True, adb_text)
            self.overview_page.set_scan(f"扫描完成 · {now}")
            if was_ok is False:
                self.status_bar.set_message("ADB 连接已恢复", "success")
            elif self.status_bar.message_label.text() in {"", "就绪", "正在初始化 ADB..."}:
                self.status_bar.set_message("设备扫描完成")
            if self.settings_page.adb_status.text().startswith("尚未检测") or "失败" in self.settings_page.adb_status.text():
                self.settings_page.set_adb_status(True, "ADB 服务正常")
            self._last_scan_ok = True
        else:
            adb_text = "ADB 异常"
            self.header.set_adb_status(False, adb_text)
            self.device_page.set_adb_status(False, "ADB 服务异常")
            self.status_bar.set_adb(False, "ADB 异常")
            self.status_bar.set_scan(f"扫描失败 · {now}")
            self.overview_page.set_adb(False, adb_text)
            self.overview_page.set_scan(f"扫描失败 · {now}")
            self.status_bar.set_message("ADB 扫描失败，请检查 ADB 路径", "error")
            self.settings_page.set_adb_status(False, message)
            if self._last_scan_ok is not False:
                self.toast.show_message("ADB 扫描失败，请检查 ADB 路径或设备连接", "error")
            self._last_scan_ok = False
        if self._active_cast_count():
            self._update_scan_status()

    def _detect_codecs(self, device: DeviceInfo, force: bool = False) -> None:
        if device.serial in self.detection_threads:
            return
        if not force and device.serial in self.codecs:
            return
        thread = EncoderDetectionThread(self.adb, device)
        thread.detected.connect(self._codecs_detected)
        thread.finished.connect(lambda serial=device.serial: self._detection_finished(serial))
        self.detection_threads[device.serial] = thread
        thread.start()

    def _detection_finished(self, serial: str) -> None:
        self.detection_threads.pop(serial, None)

    def _codecs_detected(self, serial: str, candidates: list) -> None:
        if serial not in self.current_devices:
            return
        self.codecs[serial] = candidates
        self.device_page.set_card_codecs(serial, candidates)
        self.overview_page.set_device_codecs(serial, candidates)
        if self.detail_serial == serial:
            self.detail_page.set_codecs(candidates)
        if serial in self.pending_starts:
            self.pending_starts.discard(serial)
            if candidates:
                self._set_cast_state(serial, "idle")
                self.start_cast(serial)
            else:
                self._set_cast_state(serial, "error")
                self.status_bar.set_message("未检测到 H.264/H.265 视频编码器", "error")
                self.toast.show_message("该设备未检测到可用的 H.264/H.265 编码器", "error")

    def start_cast(self, serial: str) -> None:
        device = self.current_devices.get(serial)
        if not device:
            return
        if device.state != "device":
            self.toast.show_message("设备未授权或已离线，暂时无法投屏", "warning")
            return
        if self.cast_states.get(serial) in {"starting", "running", "stopping", "detecting"}:
            return
        parameters = self.config.device_config(serial)["parameters"]
        candidates = self.codecs.get(serial)
        if not candidates:
            self.pending_starts.add(serial)
            self._set_cast_state(serial, "detecting")
            self.status_bar.set_message("正在检测设备编码器…", "warning")
            if serial not in self.detection_threads:
                self._detect_codecs(device, force=True)
            return
        requested = str(parameters.get("video_codec", "auto"))
        selected = self.detector.optimize(device, requested, candidates)
        used_fallback = False
        if selected is None and requested.lower() != "auto":
            selected = self.detector.optimize(device, "auto", candidates)
            used_fallback = selected is not None
        if selected is None:
            self._set_cast_state(serial, "error")
            self.status_bar.set_message("当前设备不支持所选编码格式", "error")
            self.toast.show_message("当前设备不支持所选编码格式，请更换编码器", "error")
            return
        resolution = str(parameters.get("resolution", "original")).lower().replace("p", "")
        ok = self.scrcpy.start(
            device,
            selected.codec,
            resolution,
            int(parameters.get("fps", 0)),
            int(parameters.get("bitrate_mbps", 8)),
            bool(parameters.get("audio", True)),
        )
        if not ok:
            self._set_cast_state(serial, "error")
            self.status_bar.set_message("scrcpy 启动失败，请检查程序路径", "error")
            self.toast.show_message("scrcpy 启动失败，请检查内置程序或授权状态", "error")
            return
        self._fallback_notices[serial] = used_fallback
        self._set_cast_state(serial, "starting")
        self.status_bar.set_message(f"正在启动 {selected.codec} 投屏…")
        self._begin_cast_scan_mode()

    def _scrcpy_started(self, serial: str) -> None:
        if serial not in self.current_devices:
            self.scrcpy.stop(serial)
            return
        if self.cast_states.get(serial) == "stopping":
            self.scrcpy.stop(serial)
            return
        self._set_cast_state(serial, "running")
        fallback = self._fallback_notices.pop(serial, False)
        if fallback:
            self.toast.show_message("请求的编码器不可用，已自动使用兼容编码器", "warning")
        else:
            self.toast.show_message("投屏已启动", "success")
        self.status_bar.set_message("投屏运行中", "success")
        self._begin_cast_scan_mode()

    def _scrcpy_failed(self, serial: str, message: str) -> None:
        self._fallback_notices.pop(serial, None)
        if serial in self.current_devices:
            self._set_cast_state(serial, "error")
        self.status_bar.set_message(message, "error")
        self.toast.show_message(message, "error")
        self._restore_scan_interval_if_idle()

    def stop_cast(self, serial: str) -> None:
        state = self.cast_states.get(serial, "idle")
        if state not in {"starting", "running"}:
            return
        self._set_cast_state(serial, "stopping")
        self.status_bar.set_message("正在停止投屏…", "warning")
        self.scrcpy.stop(serial)

    def _casting_stopped(self, serial: str, code: int) -> None:
        if serial in self.current_devices:
            self._set_cast_state(serial, "idle" if code == 0 else "error")
        if code == 0:
            self.status_bar.set_message("投屏已停止")
            self.toast.show_message("投屏已停止", "info")
        else:
            self.status_bar.set_message(f"投屏进程异常退出，错误码 {code}", "error")
            self.toast.show_message(f"投屏进程异常退出（{code}）；可尝试在设置中切换渲染后端", "error")
        self._restore_scan_interval_if_idle()

    def _set_cast_state(self, serial: str, state: str) -> None:
        self.cast_states[serial] = state
        self.device_page.set_card_casting(serial, state)
        self.overview_page.set_device_cast_state(serial, state)
        if self.detail_serial == serial:
            self.detail_page.set_casting_state(state)
        self.status_bar.set_casting_count(self._active_cast_count())

    def _active_cast_count(self) -> int:
        return sum(1 for state in self.cast_states.values() if state in {"starting", "running", "stopping"})

    def _set_scan_interval(self, seconds: int) -> None:
        QMetaObject.invokeMethod(self.worker, "set_interval", Qt.QueuedConnection, Q_ARG(int, seconds))

    def _set_scan_paused(self, paused: bool) -> None:
        QMetaObject.invokeMethod(self.worker, "set_paused", Qt.QueuedConnection, Q_ARG(bool, paused))

    def _begin_cast_scan_mode(self) -> None:
        if self.casting_scan_interval <= 0:
            self._set_scan_paused(True)
        else:
            self._set_scan_paused(False)
            self._set_scan_interval(self.casting_scan_interval)
        self._update_scan_status()

    def _update_scan_status(self) -> None:
        active = any(state in {"starting", "running", "stopping"} for state in self.cast_states.values())
        if active:
            if self.casting_scan_interval <= 0:
                self.status_bar.set_scan("投屏期间暂停扫描")
                self.device_page.scan_chip.setText("投屏期间暂停扫描")
            else:
                self.status_bar.set_scan(f"投屏期间扫描 · {self.casting_scan_interval}s")
                self.device_page.scan_chip.setText(f"投屏扫描 · {self.casting_scan_interval}s")
        else:
            self.status_bar.set_scan(
                f"自动扫描 · {self.base_scan_interval}s" if self.auto_scan_enabled else "自动扫描已暂停"
            )
            self.device_page.set_auto_scan(self.auto_scan_enabled, self.base_scan_interval)

    def _restore_scan_interval_if_idle(self) -> None:
        if not any(state in {"starting", "running", "stopping"} for state in self.cast_states.values()):
            self._set_scan_paused(False)
            self._set_scan_interval(self.base_scan_interval)
            self._update_scan_status()

    def _screen_backup(self, serial: str) -> ScreenBackup:
        if serial not in self._screen_backups:
            saved = self.config.device_config(serial).get("screen_backup")
            self._screen_backups[serial] = (
                ScreenBackup.from_dict(saved) if isinstance(saved, dict) else ScreenBackup()
            )
        return self._screen_backups[serial]

    def _persist_screen_backup(self, serial: str) -> None:
        backup = self._screen_backups.get(serial)
        if backup is not None:
            self.config.device_config(serial)["screen_backup"] = backup.to_dict()
            self.config.save()

    def _on_screen_op_routed(self, serial: str, op: str, value) -> None:
        if op == "__control__":
            self._run_device_control(serial, str(value))
        else:
            self._run_screen_op(serial, op, value)

    def _run_screen_op(self, serial: str, op: str, value) -> None:
        if serial in self._screen_threads:
            self.toast.show_message("该设备正在执行屏幕操作，请稍候", "warning")
            return
        thread = ScreenCommandThread(
            self.screen, serial, op, self._screen_backup(serial),
            value=value if isinstance(value, int) else None,
            mode=value if isinstance(value, str) else None,
            auto=None, parent=self,
        )
        thread.finished_with_result.connect(
            lambda s, payload, error: self._on_screen_result(s, payload, error)
        )
        thread.finished.connect(lambda: self._screen_threads.pop(serial, None))
        self._screen_threads[serial] = thread
        thread.start()

    def _on_screen_result(self, serial: str, payload, error: str) -> None:
        if error:
            self.toast.show_message(f"屏幕操作失败：{error}", "error")
            self.status_bar.set_message(f"屏幕操作失败：{error}", "error")
            return
        self._persist_screen_backup(serial)
        if self.overview_page._device is not None and self.overview_page._device.serial == serial:
            self.overview_page.set_screen_info(payload or {})
        toolbar = self._cast_toolbars.get(serial)
        if toolbar is not None and payload:
            toolbar.set_screen_info(payload)
        if payload:
            if "restored" in payload:
                self.toast.show_message("已恢复原始屏幕设置", "success")
            elif "orientation" in payload:
                self.toast.show_message(f"旋转模式：{payload['orientation']}", "success")
            elif "brightness" in payload and payload["brightness"] == -1:
                self.toast.show_message("已切换为自动亮度", "success")
            elif "screen_off_timeout" in payload and payload["screen_off_timeout"] == 2147483647:
                self.toast.show_message("屏幕常亮已开启", "success")
            elif "screen_off_timeout" in payload:
                self.toast.show_message("已恢复原始休眠时间", "success")

    def _start_screen_off_cast(self, serial: str) -> None:
        device = self.current_devices.get(serial)
        if device is None:
            self.toast.show_message("设备不在线", "error")
            return
        parameters = self.config.device_config(serial)["parameters"]
        serial_requested = str(parameters.get("video_codec", "auto"))
        candidates = self.codecs.get(serial) or []
        selected = self.detector.optimize(device, serial_requested, candidates)
        if selected is None and serial_requested.lower() != "auto":
            selected = self.detector.optimize(device, "auto", candidates)
        if selected is None:
            self.toast.show_message("当前设备不支持可用编码格式", "error")
            return
        resolution = str(parameters.get("resolution", "original")).lower().replace("p", "")
        ok = self.scrcpy.start(
            device,
            selected.codec,
            resolution,
            int(parameters.get("fps", 0)),
            int(parameters.get("bitrate_mbps", 8)),
            bool(parameters.get("audio", True)),
            turn_screen_off=True,
        )
        if ok:
            self._set_cast_state(serial, "starting")
            self.toast.show_message("熄屏投屏启动中，手机屏幕将关闭", "success")
            self._begin_cast_scan_mode()

    def _toggle_fullscreen(self, serial: str) -> None:
        if not self.scrcpy.is_running(serial):
            self.toast.show_message("该设备当前没有投屏会话", "warning")
            return
        if self.scrcpy.toggle_fullscreen(serial):
            state = "全屏" if self.scrcpy.is_fullscreen(serial) else "窗口"
            self.toast.show_message(f"已切换为{state}模式", "success")
        else:
            self.toast.show_message("未找到投屏窗口，请确认投屏正在运行", "error")

    def _on_sessions_changed(self) -> None:
        if self.stack.currentWidget() is self.sessions_page:
            self.sessions_page.refresh_sessions(list(self.scrcpy.sessions.values()))

    def _take_screenshot(self, serial: str) -> None:
        device = self.current_devices.get(serial)
        if device is None:
            self.toast.show_message("设备不在线，无法截图", "error")
            return
        for thread in self._media_threads:
            if isinstance(thread, ScreenshotThread) and thread.serial == serial:
                self.toast.show_message("正在截图，请稍候", "warning")
                return
        thread = ScreenshotThread(self.media, serial, device.model, self)
        thread.finished_with_result.connect(lambda record, error: self._on_screenshot_done(serial, record, error))
        thread.finished.connect(lambda t=thread: self._media_threads.discard(t))
        self._media_threads.add(thread)
        thread.start()
        self.status_bar.set_message("正在截图 ...")

    def _on_screenshot_done(self, serial: str, record, error: str) -> None:
        if error:
            self.toast.show_message(f"截图失败：{error}", "error")
            self.status_bar.set_message(f"截图失败：{error}", "error")
            return
        self.toast.show_message(f"截图已保存：{record.file_name}", "success")
        self.status_bar.set_message(f"截图已保存：{record.path}", "success")

    def _toggle_recording(self, serial: str) -> None:
        if serial in self._media_threads:
            self.toast.show_message("录屏操作正在执行，请稍候", "warning")
            return
        action = "stop" if serial in self._recording_serials else "start"
        device = self.current_devices.get(serial)
        if action == "start" and device is None:
            self.toast.show_message("设备不在线，无法录屏", "error")
            return
        device_name = device.model if device else serial
        thread = RecordControlThread(self.media, serial, device_name, self.scrcpy.scrcpy_path, action, self)
        thread.finished_with_result.connect(
            lambda ok, message, record: self._on_record_done(serial, action, ok, message, record)
        )
        thread.finished.connect(lambda t=thread: self._media_threads.discard(t))
        self._media_threads.add(thread)
        thread.start()
        self.status_bar.set_message("正在处理录屏 ...")

    def _on_record_done(self, serial: str, action: str, ok: bool, message: str, record) -> None:
        if not ok:
            self.toast.show_message(f"录屏操作失败：{message}", "error")
            self.status_bar.set_message(f"录屏操作失败：{message}", "error")
            return
        if action == "start":
            self._recording_serials.add(serial)
            self.toast.show_message(f"录屏已开始（无声模式）：{record.file_name}", "success")
        else:
            self._recording_serials.discard(serial)
            size_kb = (record.size / 1024) if record else 0
            self.toast.show_message(f"录屏已保存：{record.file_name if record else ''}（{size_kb:.0f} KB）", "success")
        self.overview_page.set_recording(serial, serial in self._recording_serials)
        toolbar = self._cast_toolbars.get(serial)
        if toolbar is not None:
            toolbar.set_recording(serial in self._recording_serials)

    def _open_media_file(self, record) -> None:
        if not record.exists():
            self.toast.show_message("文件不存在，可能已被删除", "warning")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(record.path))

    def _open_media_folder(self, record) -> None:
        folder = str(Path(record.path).parent)
        if Path(folder).is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        else:
            self.toast.show_message("目录不存在", "warning")

    def _delete_media_record(self, record) -> None:
        if QMessageBox.question(
            self, "删除记录", "仅删除这条历史记录？\n（不会删除媒体文件）",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) == QMessageBox.Yes:
            self.media.delete_record(record)
            self.media_page.set_records(self.media.load_history())

    def _delete_media_file(self, record) -> None:
        if QMessageBox.question(
            self, "删除文件", f"确定要删除文件 {record.file_name} 吗？\n该操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) == QMessageBox.Yes:
            try:
                self.media.delete_file_and_record(record)
                self.toast.show_message("文件与记录已删除", "info")
            except Exception as error:
                self.toast.show_message(str(error), "error")
            self.media_page.set_records(self.media.load_history())

    def _sync_cast_toolbars(self) -> None:
        import sys as _sys

        if _sys.platform != "win32":
            return
        import ctypes

        active = {
            s.serial for s in self.scrcpy.sessions.values()
            if s.state in ("starting", "running")
        }
        # remove toolbars for sessions that are no longer active
        for serial in list(self._cast_toolbars):
            if serial not in active:
                self._cast_toolbars.pop(serial).close()
        for serial in active:
            rect = self.scrcpy.get_window_rect(serial)
            if rect is None:
                continue
            toolbar = self._cast_toolbars.get(serial)
            if toolbar is None:
                toolbar = CastToolBar(serial, recording=serial in self._recording_serials)
                toolbar.action_requested.connect(self._run_device_control)
                toolbar.fullscreen_requested.connect(self._toggle_fullscreen)
                toolbar.screenshot_requested.connect(self._take_screenshot)
                toolbar.record_requested.connect(self._toggle_recording)
                toolbar.screen_op_requested.connect(self._on_screen_op_routed)
                toolbar.show()
                if serial not in self._screen_threads:
                    self._run_screen_op(serial, "get_info", None)
                self._cast_toolbars[serial] = toolbar
            toolbar.set_recording(serial in self._recording_serials)
            left, top, width, height = rect
            screen_w = ctypes.windll.user32.GetSystemMetrics(0)
            x = max(0, min(left + (width - toolbar.width()) // 2, screen_w - toolbar.width()))
            toolbar.move(x, top + height + 4)

    def _run_device_control(self, serial: str, action: str) -> None:
        if serial in self._control_threads:
            self.toast.show_message("该设备正在执行控制操作，请稍候", "warning")
            return
        self.status_bar.set_message(f"正在发送：{serial}", "info")
        thread = ControlCommandThread(self.control, serial, action, self)
        thread.finished_with_result.connect(
            lambda result: self._on_control_result(result)
        )
        thread.finished.connect(lambda: self._control_threads.pop(serial, None))
        self._control_threads[serial] = thread
        thread.start()

    def _on_control_result(self, result) -> None:
        tone = "success" if result.success else "error"
        self.toast.show_message(f"{result.serial}：{result.message}", tone)
        self.status_bar.set_message(f"{result.serial}：{result.message}", tone)

    def open_network_dialog(self) -> None:
        if self._network_dialog is None:
            self._network_dialog = NetworkConnectDialog(self, list(self.current_devices.values()))
            self._network_dialog.connect_requested.connect(self._connect_network_device)
            self._network_dialog.disconnect_requested.connect(self._disconnect_from_dialog)
            self._network_dialog.scan_requested.connect(self._scan_lan)
            self._network_dialog.restart_server_requested.connect(self._restart_adb_server)
        else:
            self._network_dialog.set_busy(False)
            self._network_dialog.set_scanning(False)
            self._network_dialog.set_restarting(False)
        self._network_dialog.show()
        self._network_dialog.raise_()
        self._network_dialog.activateWindow()

    def _network_thread_busy(self, thread_type: type, serial: str) -> bool:
        return any(
            isinstance(thread, thread_type)
            and f'{thread.ip}:{thread.port}' == serial
            for thread in self._network_threads
        )

    def _connect_network_device(self, ip: str, port: int) -> None:
        serial = f'{ip}:{port}'
        if self._network_thread_busy(NetworkConnectThread, serial):
            self.status_bar.set_message(f'{serial} 正在连接中，请稍候…', 'warning')
            return
        self.status_bar.set_message(f'正在连接 {ip}:{port} …', 'info')
        thread = NetworkConnectThread(self.network, ip, port, self)
        thread.finished_with_result.connect(lambda result: self._on_network_connect_result(ip, port, result))
        thread.finished.connect(lambda t=thread: self._network_threads.discard(t))
        self._network_threads.add(thread)
        thread.start()

    def _remember_network_address(self, ip: str, port: int) -> None:
        serial = f'{ip}:{port}'
        recent: list = self.config.settings.get('recent_network_addresses', [])
        if serial in recent:
            recent.remove(serial)
        recent.insert(0, serial)
        self.config.settings['recent_network_addresses'] = recent[:5]
        self.config.save()

    def _on_network_connect_result(self, ip: str, port: int, result) -> None:
        message = getattr(result, 'message', '')
        if result.success:
            self._remember_network_address(ip, port)
            if self._network_dialog is not None:
                self._network_dialog.show_result(True, message)
            self.request_scan()
            verb = '已连接' if result.already_connected else '连接成功'
            self.toast.show_message(f'{verb}：{ip}:{port}', 'success')
            self.status_bar.set_message(f'{verb} {ip}:{port}', 'success')
        else:
            if self._network_dialog is not None:
                self._network_dialog.show_result(False, message, server_error=getattr(result, 'server_error', False))
            self.toast.show_message(f'连接失败：{message}', 'error')
            self.status_bar.set_message(f'连接失败：{message}', 'error')

    def _scan_lan(self) -> None:
        if any(isinstance(thread, LanScanThread) for thread in self._network_threads):
            return
        self.status_bar.set_message('正在扫描局域网设备…', 'info')
        recent = list(self.config.settings.get('recent_network_addresses', []))
        thread = LanScanThread(self.network, 5555, self, recent=recent)
        thread.finished_with_result.connect(self._on_lan_scan_result)
        thread.finished.connect(lambda t=thread: self._network_threads.discard(t))
        self._network_threads.add(thread)
        thread.start()

    def _on_lan_scan_result(self, ips: list, results: list) -> None:
        connected = [result for result in results if result.success and not result.already_connected]
        already = [result for result in results if result.already_connected]
        if results:
            self.request_scan()
        for result in connected or []:
            if result.serial:
                host, _, port_text = result.serial.rpartition(':')
                if port_text.isdigit():
                    self._remember_network_address(host, int(port_text))
        if connected or already:
            total = len(connected) + len(already)
            verb = '新连接' if connected else '已连接'
            detail = ', '.join(result.serial for result in (connected or already))
            self.toast.show_message(f'扫描完成：{verb} {total} 台（{detail}）', 'success')
            self.status_bar.set_message(f'扫描完成：{verb} {total} 台设备', 'success')
        else:
            self.status_bar.set_message('局域网扫描完成，未发现可连接设备', 'warning')
        if self._network_dialog is not None and self._network_dialog.isVisible():
            self._network_dialog.show_scan_result(len(ips), len(connected) + len(already))

    def _disconnect_from_dialog(self, ip: str, port: int) -> None:
        if self._network_thread_busy(NetworkDisconnectThread, f'{ip}:{port}'):
            self.status_bar.set_message('正在断开中，请稍候…', 'warning')
            return
        if self._network_dialog is not None:
            self._network_dialog.set_busy(True)
        self.status_bar.set_message(f'正在断开 {ip}:{port} …', 'warning')
        thread = NetworkDisconnectThread(self.network, ip, port, self)
        thread.finished_with_result.connect(
            lambda result, i=ip, p=port: self._on_dialog_disconnect_result(i, p, result)
        )
        thread.finished.connect(lambda t=thread: self._network_threads.discard(t))
        self._network_threads.add(thread)
        thread.start()

    def _on_dialog_disconnect_result(self, ip: str, port: int, result) -> None:
        if self._network_dialog is not None:
            self._network_dialog.set_busy(False)
        if result.success:
            self.toast.show_message(f'已断开：{ip}:{port}', 'info')
            self.status_bar.set_message(f'已断开 {ip}:{port}')
        else:
            self.toast.show_message(f'断开失败：{result.message}', 'error')
            self.status_bar.set_message(f'断开失败：{result.message}', 'error')
        self.request_scan()

    def _restart_adb_server(self) -> None:
        if self._network_dialog is None:
            return
        self._network_dialog.set_restarting(True)
        self.status_bar.set_message('正在启动 ADB Server…', 'warning')
        thread = ServerRestartThread(self.network, self)
        thread.finished_with_result.connect(self._on_restart_server_result)
        thread.finished.connect(lambda t=thread: self._network_threads.discard(t))
        self._network_threads.add(thread)
        thread.start()

    def _on_restart_server_result(self, ok: bool, message: str) -> None:
        if self._network_dialog is not None:
            self._network_dialog.show_restart_result(ok, message)
        if ok:
            self.toast.show_message('ADB Server 已启动', 'success')
            self.status_bar.set_message('ADB Server 已启动', 'success')
            self.request_scan()
        else:
            self.toast.show_message(f'ADB Server 重启失败：{message}', 'error')
            self.status_bar.set_message(f'ADB Server 重启失败：{message}', 'error')

    def _disconnect_network_device(self, serial: str) -> None:
        host, sep, port_text = serial.rpartition(':')
        if not sep or not host or not port_text.isdigit():
            return
        if self._network_thread_busy(NetworkDisconnectThread, serial):
            self.status_bar.set_message(f'{serial} 正在断开中，请稍候…', 'warning')
            return
        self.status_bar.set_message(f'正在断开 {serial} …', 'warning')
        thread = NetworkDisconnectThread(self.network, host, int(port_text), self)
        thread.finished_with_result.connect(lambda result: self._on_network_disconnect_result(serial, result))
        thread.finished.connect(lambda t=thread: self._network_threads.discard(t))
        self._network_threads.add(thread)
        thread.start()

    def _on_network_disconnect_result(self, serial: str, result) -> None:
        if result.success:
            self.toast.show_message(f'已断开：{serial}', 'info')
            self.status_bar.set_message(f'已断开 {serial}')
        else:
            self.toast.show_message(f'断开失败：{result.message}', 'error')
            self.status_bar.set_message(f'断开失败：{result.message}', 'error')
        self.request_scan()

    def request_scan(self) -> None:
        self.status_bar.set_scan("正在扫描…")
        self.overview_page.set_scan("正在扫描…")
        QMetaObject.invokeMethod(self.worker, "scan", Qt.QueuedConnection)

    def _auto_scan_changed(self, enabled: bool) -> None:
        self.auto_scan_enabled = enabled
        self.config.settings["auto_scan"] = enabled
        self.config.save()
        self.device_page.set_auto_scan(enabled, self.base_scan_interval)
        QMetaObject.invokeMethod(self.worker, "set_enabled", Qt.QueuedConnection, Q_ARG(bool, enabled))
        self._update_scan_status()
        self.toast.show_message("自动扫描已开启" if enabled else "自动扫描已暂停", "info")

    def apply_default_parameters(self, parameters: dict) -> None:
        serials = list(self.current_devices)
        self.config.set_default_parameters(parameters, serials)
        self.config.save()
        self.cast_page.load_defaults(self.config.settings["default_parameters"])
        self.cast_page.quick_config.show_saved()
        self.settings_page.load(self.config.settings)
        self.status_bar.set_message("默认投屏参数已保存，下次投屏生效", "success")
        self.toast.show_message("默认投屏参数已保存", "success")

    def save_device_defaults(self, serial: str) -> None:
        if serial not in self.current_devices:
            return
        config = self.config.device_config(serial)
        dialog = DeviceSettingsDialog(config["parameters"], self.codecs.get(serial, []), self, device=self.current_devices.get(serial))
        if not dialog.exec():
            return
        config["parameters"] = dialog.parameters()
        self.config.save()
        self.status_bar.set_message("设备投屏设置已保存，下次投屏生效", "success")
        self.toast.show_message("设备投屏设置已保存", "success")

    def show_details(self, serial: str) -> None:
        device = self.current_devices.get(serial)
        if not device:
            return
        codecs = self.codecs.get(serial)
        if not codecs and serial not in self.detection_threads:
            self._detect_codecs(device, force=True)
        self.detail_serial = serial
        state = self.cast_states.get(serial, "idle")
        self.detail_page.set_device(device, codecs or [], state)
        if codecs is None or serial in self.detection_threads:
            self.detail_page.set_codecs_pending()
        self.stack.setCurrentWidget(self.detail_page)

    def redetect_codecs(self, serial: str) -> None:
        device = self.current_devices.get(serial)
        if not device or serial in self.detection_threads:
            return
        self.codecs.pop(serial, None)
        card = self.device_page.cards.get(serial)
        if card:
            card.set_codecs_pending()
        if self.detail_serial == serial:
            self.detail_page.set_codecs_pending()
        self._detect_codecs(device, force=True)
        self.status_bar.set_message("正在重新检测编码器…")
        self.toast.show_message("正在重新检测设备编码器", "info")

    def copy_serial(self, serial: str) -> None:
        QApplication.clipboard().setText(serial)
        self.status_bar.set_message("ADB 序列号已复制", "success")
        self.toast.show_message("ADB 序列号已复制", "success", 1800)

    def apply_theme(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(stylesheet_for("light"))
        self.config.settings["theme"] = "light"

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_size_grip"):
            grip = self._size_grip
            grip.move(self.centralWidget().width() - grip.width(), self.centralWidget().height() - grip.height())

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == event.Type.WinIdChange or event.type() == event.Type.WindowStateChange:
            self.title_bar.set_maximized(self.isMaximized())

    def _navigate(self, key: str) -> None:
        if key == "home":
            self.show_home_page()
        elif key == "devices":
            self.show_device_page()
        elif key == "sessions":
            self.show_sessions_page()
        elif key == "media":
            self.show_media_page()
        elif key == "cast":
            self.show_cast_settings_page()
        elif key == "guide":
            self.show_guide_page()
        elif key == "logs":
            self.show_log_page()
        elif key == "settings":
            self.open_settings()

    def open_settings(self) -> None:
        self.settings_page.load(self.config.settings)
        self.stack.setCurrentWidget(self.settings_page)
        self.header.settings_button.setEnabled(False)
        self.sidebar.set_active("settings")
        self.header.set_context("设置")
        self.status_bar.set_message("设置")
        self.check_tool("adb", self.config.settings.get("adb_path", ""), notify=False)
        self.check_tool("scrcpy", self.config.settings.get("scrcpy_path", ""), notify=False)

    def show_home_page(self) -> None:
        self.detail_serial = None
        self.stack.setCurrentWidget(self.overview_page)
        self.header.settings_button.setEnabled(True)
        self.sidebar.set_active("home")
        self.header.set_context("首页")
        self.status_bar.set_message("首页")

    def show_media_page(self) -> None:
        self.detail_serial = None
        self.media_page.set_records(self.media.load_history())
        self.stack.setCurrentWidget(self.media_page)
        self.header.settings_button.setEnabled(True)
        self.sidebar.set_active("media")
        self.header.set_context("媒体管理")
        self.status_bar.set_message("媒体管理")

    def show_sessions_page(self) -> None:
        self.detail_serial = None
        self.sessions_page.refresh_sessions(list(self.scrcpy.sessions.values()))
        self.stack.setCurrentWidget(self.sessions_page)
        self.header.settings_button.setEnabled(True)
        self.sidebar.set_active("sessions")
        self.header.set_context("投屏中心")
        self.status_bar.set_message("投屏中心")

    def show_guide_page(self) -> None:
        self.detail_serial = None
        self.stack.setCurrentWidget(self.guide_page)
        self.header.settings_button.setEnabled(True)
        self.sidebar.set_active("guide")
        self.header.set_context("使用指南")
        self.status_bar.set_message("使用指南")

    def show_cast_settings_page(self) -> None:
        self.stack.setCurrentWidget(self.cast_page)
        self.header.settings_button.setEnabled(True)
        self.sidebar.set_active("cast")
        self.header.set_context("投屏设置")
        self.status_bar.set_message("投屏参数")

    def show_log_page(self) -> None:
        self.stack.setCurrentWidget(self.log_page)
        self.header.settings_button.setEnabled(True)
        self.sidebar.set_active("logs")
        self.header.set_context("运行日志")
        self.status_bar.set_message("运行日志")

    def show_device_page(self) -> None:
        self.detail_serial = None
        self.stack.setCurrentWidget(self.device_page)
        self.header.settings_button.setEnabled(True)
        self.sidebar.set_active("devices")
        self.header.set_context("设备管理")
        self.status_bar.set_message("就绪")

    def save_settings(self, settings: dict) -> None:
        old_adb_path = self.adb.adb_path
        old_scrcpy_path = self.scrcpy.scrcpy_path
        old_render_driver = self.scrcpy.render_driver
        self.config.settings.update(settings)
        self.config.save()
        new_adb_path = resolve_tool(settings.get("adb_path", ""), "resources/adb", "adb")
        new_scrcpy_path = resolve_tool(settings.get("scrcpy_path", ""), "resources/scrcpy", "scrcpy")
        new_render_driver = settings.get("render_driver", "opengl")
        adb_changed = new_adb_path != old_adb_path
        scrcpy_changed = new_scrcpy_path != old_scrcpy_path
        render_changed = new_render_driver != old_render_driver
        self.adb.adb_path = new_adb_path
        self.scrcpy.scrcpy_path = new_scrcpy_path
        self.scrcpy.adb_path = new_adb_path
        self.scrcpy.render_driver = new_render_driver
        self.base_scan_interval = int(self.config.settings["scan_interval"])
        self.casting_scan_interval = int(self.config.settings["casting_scan_interval"])
        self.auto_scan_enabled = bool(self.config.settings["auto_scan"])
        self.device_page.set_auto_scan(self.auto_scan_enabled, self.base_scan_interval)
        self.cast_page.load_defaults(self.config.settings["default_parameters"])
        active = any(state in {"starting", "running", "stopping"} for state in self.cast_states.values())
        self._set_scan_paused(active and self.casting_scan_interval <= 0)
        self._set_scan_interval(self.casting_scan_interval if active and self.casting_scan_interval > 0 else self.base_scan_interval)
        QMetaObject.invokeMethod(self.worker, "set_enabled", Qt.QueuedConnection, Q_ARG(bool, self.auto_scan_enabled))
        if not self.auto_scan_enabled and adb_changed and not active:
            self.request_scan()
        self._update_scan_status()
        saved_message = "设置已保存并应用" + ("；渲染后端将在下次投屏生效" if render_changed and active else "")
        self.settings_page.set_saved(saved_message)
        self.status_bar.set_message(saved_message, "success")
        self.toast.show_message(saved_message, "success")
        if adb_changed:
            self.check_tool("adb", settings.get("adb_path", ""), notify=False)
        if scrcpy_changed:
            self.check_tool("scrcpy", settings.get("scrcpy_path", ""), notify=False)

    def reset_settings(self) -> None:
        self.settings_page.load(ConfigManager.default_settings())
        self.settings_page.set_hint("已载入默认值，点击“保存并应用”后生效")
        self.toast.show_message("已载入默认设置", "info")

    def check_tool(self, tool: str, path: str, notify: bool = False) -> None:
        existing = self.tool_threads.get(tool)
        if existing and existing.isRunning():
            return
        self.settings_page.set_tool_busy(tool, True)
        thread = ToolCheckThread(tool, path)
        self.tool_threads[tool] = thread
        thread.result.connect(lambda name, ok, message, notify=notify: self._tool_checked(name, ok, message, notify))
        thread.finished.connect(lambda name=tool: self._tool_thread_finished(name))
        thread.start()

    def _tool_checked(self, tool: str, ok: bool, message: str, notify: bool) -> None:
        if tool == "adb":
            self.settings_page.set_adb_status(ok, message)
            self.header.set_adb_status(ok, "ADB 已连接" if ok else "ADB 异常")
            self.status_bar.set_adb(ok, "ADB 已连接" if ok else "ADB 异常")
        else:
            self.settings_page.set_scrcpy_status(ok, message)
        self.settings_page.set_tool_busy(tool, False)
        if ok:
            if notify:
                self.toast.show_message(f"{tool.upper()} 检测通过", "success")
        else:
            self.settings_page.set_error(f"{tool.upper()} 检测失败：{message}")
            if notify:
                self.toast.show_message(f"{tool.upper()} 检测失败", "error")

    def _tool_thread_finished(self, tool: str) -> None:
        self.tool_threads.pop(tool, None)

    def show_help(self) -> None:
        dialog = FaqDialog(self)
        dialog.rescan_requested.connect(self.request_scan)
        dialog.exec()

    def open_logs(self) -> None:
        LOG_DIR.mkdir(exist_ok=True)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(LOG_DIR))):
            self.toast.show_message("无法打开日志目录", "error")

    def clear_interface_logs(self) -> None:
        self.log_page.clear_log()
        self.toast.show_message("界面日志已清空", "info", 1600)

    def export_logs(self) -> None:
        default_name = f"smartcast-log-{datetime.now():%Y%m%d-%H%M%S}.txt"
        path, _ = QFileDialog.getSaveFileName(self, "导出日志", default_name, "Text files (*.txt);;All files (*.*)")
        if not path:
            return
        source = LOG_DIR / "smartcast.log"
        try:
            content = self.log_page.to_plain_text()
            if not content and source.exists():
                content = source.read_text(encoding="utf-8", errors="ignore")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)
        except OSError as error:
            self.toast.show_message(f"导出失败：{error}", "error")
            return
        self.toast.show_message("日志已导出", "success")

    def _append_log(self, line: str) -> None:
        self.log_page.append_log(line)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "toast"):
            self.toast.reposition()

    def closeEvent(self, event) -> None:
        for thread in list(self.detection_threads.values()):
            if thread.isRunning() and not thread.wait(2500):
                thread.terminate()
                thread.wait(500)
        for thread in list(self.tool_threads.values()):
            if thread.isRunning() and not thread.wait(2500):
                thread.terminate()
                thread.wait(500)
        self.device_thread.quit()
        if not self.device_thread.wait(4000):
            self.device_thread.terminate()
            self.device_thread.wait(500)
        self.scrcpy.shutdown()
        self.config.save()
        if self._log_handler is not None:
            self.logger.removeHandler(self._log_handler)
            self._log_handler = None
        super().closeEvent(event)














