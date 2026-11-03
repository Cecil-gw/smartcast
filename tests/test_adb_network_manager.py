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

from core.adb_network_manager import (
    AdbNetworkError,
    AdbNetworkManager,
    NetworkResult,
    parse_address,
    validate_ip,
    validate_port,
)
from core.device_info import (
    CONNECTION_EMULATOR,
    CONNECTION_USB,
    CONNECTION_WIFI,
    DeviceInfo,
    connection_type_for_serial,
)
from utils.config_manager import ConfigManager


def run_manager() -> AdbNetworkManager:
    return AdbNetworkManager("adb")


class ValidationTests(unittest.TestCase):
    def test_valid_ips(self) -> None:
        for value in ["192.168.1.23", "10.0.0.1", "127.0.0.1"]:
            self.assertIsNone(validate_ip(value))

    def test_invalid_ips(self) -> None:
        for value in ["", "abc", "1.2.3", "256.1.1.1", "1.2.3.4.5", "1..2.3"]:
            self.assertIsNotNone(validate_ip(value))

    def test_valid_ports(self) -> None:
        self.assertEqual(validate_port("5555"), (5555, None))
        self.assertEqual(validate_port("1"), (1, None))
        self.assertEqual(validate_port("65535"), (65535, None))

    def test_invalid_ports(self) -> None:
        self.assertIsNotNone(validate_port("")[1])
        self.assertIsNotNone(validate_port("abc")[1])
        self.assertIsNotNone(validate_port("0")[1])
        self.assertIsNotNone(validate_port("65536")[1])


class ConnectTests(unittest.TestCase):
    def test_connect_success(self) -> None:
        manager = run_manager()
        responses = [
            (0, "connected to 192.168.1.23:5555", ""),  # adb connect
            (0, "List of devices attached\n192.168.1.23:5555\tdevice product:x", ""),  # devices
            (0, "smartcast_ok\n", ""),  # shell echo
        ]
        with mock.patch("core.adb_network_manager.run_command", side_effect=responses) as mocked:
            result = manager.connect("192.168.1.23", 5555)
        self.assertTrue(result.success)
        self.assertFalse(result.already_connected)
        self.assertEqual(result.state, "device")
        self.assertEqual(result.serial, "192.168.1.23:5555")
        self.assertEqual(mocked.call_args_list[0][0][0], ["adb", "connect", "192.168.1.23:5555"])
        self.assertEqual(mocked.call_args_list[1][0][0], ["adb", "devices"])
        self.assertEqual(mocked.call_args_list[2][0][0][:3], ["adb", "-s", "192.168.1.23:5555"])

    def test_connect_reports_connected_but_unauthorized(self) -> None:
        manager = run_manager()
        responses = [
            (0, "connected to 192.168.1.23:5555", ""),
            (0, "List of devices attached\n192.168.1.23:5555\tunauthorized", ""),
        ]
        with mock.patch("core.adb_network_manager.run_command", side_effect=responses):
            result = manager.connect("192.168.1.23", 5555)
        self.assertFalse(result.success)
        self.assertEqual(result.state, "unauthorized")
        self.assertIn("未授权", result.message)

    def test_connect_reports_connected_but_offline(self) -> None:
        manager = run_manager()
        responses = [
            (0, "connected to 192.168.1.23:5555", ""),
            (0, "List of devices attached\n192.168.1.23:5555\toffline", ""),
        ]
        with mock.patch("core.adb_network_manager.run_command", side_effect=responses):
            result = manager.connect("192.168.1.23", 5555)
        self.assertFalse(result.success)
        self.assertEqual(result.state, "offline")
        self.assertIn("offline", result.message)

    def test_connect_reports_connected_but_shell_dead(self) -> None:
        manager = run_manager()
        responses = [
            (0, "connected to 192.168.1.23:5555", ""),
            (0, "List of devices attached\n192.168.1.23:5555\tdevice", ""),
            (1, "", "error: closed"),
        ]
        with mock.patch("core.adb_network_manager.run_command", side_effect=responses):
            result = manager.connect("192.168.1.23", 5555)
        self.assertFalse(result.success)
        self.assertIn("无响应", result.message)

    def test_connect_failure(self) -> None:
        manager = run_manager()
        with mock.patch("core.adb_network_manager.run_command", return_value=(1, "", "cannot connect to 192.168.1.23:5555: Connection refused")):
            result = manager.connect("192.168.1.23", 5555)
        self.assertFalse(result.success)
        self.assertIn("拒绝", result.message)

    def test_connect_already_connected(self) -> None:
        manager = run_manager()
        responses = [
            (0, "already connected to 192.168.1.23:5555", ""),
            (0, "List of devices attached\n192.168.1.23:5555\tdevice", ""),
            (0, "smartcast_ok\n", ""),
        ]
        with mock.patch("core.adb_network_manager.run_command", side_effect=responses):
            result = manager.connect("192.168.1.23", 5555)
        self.assertTrue(result.success)
        self.assertTrue(result.already_connected)

    def test_connect_winerror_10060(self) -> None:
        manager = run_manager()
        with mock.patch("core.adb_network_manager.run_command", return_value=(1, "", "cannot connect to 192.168.1.23:5555: 10060")):
            result = manager.connect("192.168.1.23", 5555)
        self.assertFalse(result.success)
        self.assertIn("10060", result.message)

    def test_connect_winerror_10013(self) -> None:
        manager = run_manager()
        with mock.patch("core.adb_network_manager.run_command", return_value=(1, "", "cannot connect to 192.168.1.23:5555: 10013")):
            result = manager.connect("192.168.1.23", 5555)
        self.assertFalse(result.success)
        self.assertIn("10013", result.message)

    def test_connect_adb_server_down(self) -> None:
        manager = run_manager()
        with mock.patch("core.adb_network_manager.run_command", return_value=(1, "", "* failed to start daemon\nerror: cannot connect to daemon")):
            result = manager.connect("192.168.1.23", 5555)
        self.assertFalse(result.success)
        self.assertTrue(result.server_error)
        self.assertIn("ADB Server", result.message)

    def test_restart_server(self) -> None:
        manager = run_manager()
        with mock.patch("core.adb_network_manager.run_command", return_value=(0, "", "")) as mocked:
            ok, message = manager.restart_server()
        self.assertTrue(ok)
        self.assertEqual(mocked.call_args[0][0], ["adb", "start-server"])

    def test_parse_address(self) -> None:
        self.assertEqual(parse_address("10.23.224.216:39401"), ("10.23.224.216", 39401, None))
        self.assertEqual(parse_address("192.168.1.23"), ("192.168.1.23", None, None))
        self.assertIsNone(parse_address("192.168.1.23:abc")[0])
        self.assertIsNone(parse_address("bad:5555")[0])
        self.assertIsNone(parse_address("")[0])

    def test_connect_rejected_input(self) -> None:
        manager = run_manager()
        self.assertFalse(manager.connect("bad-ip", 5555).success)
        self.assertFalse(manager.connect("192.168.1.23", 99999).success)

    def test_connect_exit_code_zero_without_confirmation_is_failure(self) -> None:
        manager = run_manager()
        # adb exits 0 with empty output but device never appears in list
        with mock.patch(
            "core.adb_network_manager.run_command",
            side_effect=[(0, "", ""), (0, "List of devices attached\n", "")],
        ):
            result = manager.connect("192.168.1.23", 5555)
        self.assertFalse(result.success)
        self.assertEqual(result.state, "disconnected")

    def test_connect_timeout(self) -> None:
        manager = run_manager()
        with mock.patch("core.adb_network_manager.run_command", return_value=(124, "", "Command timed out")):
            result = manager.connect("192.168.1.23", 5555)
        self.assertFalse(result.success)
        self.assertIn("超时", result.message)

    def test_adb_missing_raises(self) -> None:
        manager = run_manager()
        with mock.patch("core.adb_network_manager.run_command", return_value=(127, "", "Executable not found")):
            with self.assertRaises(AdbNetworkError):
                manager.connect("192.168.1.23", 5555)


class DisconnectTests(unittest.TestCase):
    def test_disconnect_success(self) -> None:
        manager = run_manager()
        with mock.patch("core.adb_network_manager.run_command", return_value=(0, "disconnected 192.168.1.23:5555", "")) as mocked:
            result = manager.disconnect("192.168.1.23", 5555)
        self.assertTrue(result.success)
        self.assertEqual(mocked.call_args[0][0], ["adb", "disconnect", "192.168.1.23:5555"])

    def test_disconnect_not_found_is_success(self) -> None:
        manager = run_manager()
        with mock.patch("core.adb_network_manager.run_command", return_value=(0, "error: no such device", "")):
            result = manager.disconnect("192.168.1.23", 5555)
        self.assertTrue(result.success)


class ConnectionTypeTests(unittest.TestCase):
    def test_usb_serial(self) -> None:
        self.assertEqual(connection_type_for_serial("320146588834"), CONNECTION_USB)

    def test_wifi_serial(self) -> None:
        self.assertEqual(connection_type_for_serial("192.168.1.23:5555"), CONNECTION_WIFI)

    def test_emulator_serial(self) -> None:
        self.assertEqual(connection_type_for_serial("emulator-5554"), CONNECTION_EMULATOR)

    def test_device_info_default(self) -> None:
        info = DeviceInfo(serial="320146588834", state="device")
        self.assertEqual(info.connection_type, CONNECTION_USB)


class ScrcpySerialTests(unittest.TestCase):
    def test_network_serial_passed_to_scrcpy(self) -> None:
        from core.scrcpy_manager import ScrcpyManager

        class Dummy:
            render_driver = "opengl"

        command = ScrcpyManager.build_command(
            Dummy(), "192.168.1.23:5555", "h264", "720", 60, 8, audio=True
        )
        self.assertIn("-s", command)
        self.assertEqual(command[command.index("-s") + 1], "192.168.1.23:5555")

    def test_usb_serial_passed_to_scrcpy(self) -> None:
        from core.scrcpy_manager import ScrcpyManager

        class Dummy:
            render_driver = "opengl"

        command = ScrcpyManager.build_command(Dummy(), "320146588834", "h264", "original", 0, 8)
        self.assertEqual(command[command.index("-s") + 1], "320146588834")


class ConfigIsolationTests(unittest.TestCase):
    def test_device_configs_are_isolated_by_serial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ConfigManager(Path(tmp))
            usb = config.device_config("320146588834")
            wifi = config.device_config("192.168.1.23:5555")
            usb["parameters"]["resolution"] = "720"
            wifi["parameters"]["bitrate_mbps"] = 12
            self.assertEqual(usb["parameters"]["resolution"], "720")
            self.assertEqual(wifi["parameters"]["bitrate_mbps"], 12)
            self.assertNotEqual(
                config.devices["320146588834"]["parameters"],
                config.devices["192.168.1.23:5555"]["parameters"],
            )




class NetworkScannerTests(unittest.TestCase):
    def test_subnet_hosts_24(self) -> None:
        from core.network_scanner import subnet_hosts

        hosts = subnet_hosts("192.168.1.23")
        self.assertEqual(len(hosts), 254)
        self.assertIn("192.168.1.1", hosts)
        self.assertIn("192.168.1.254", hosts)
        self.assertNotIn("192.168.1.0", hosts)
        self.assertNotIn("192.168.1.255", hosts)

    def test_subnet_hosts_invalid(self) -> None:
        from core.network_scanner import subnet_hosts

        self.assertEqual(subnet_hosts("not-an-ip"), [])

    def test_scan_hosts_with_mocked_sockets(self) -> None:
        from unittest.mock import patch

        import core.network_scanner as scanner

        def fake_open(ip, port, timeout=0.4):
            return ip in {"192.168.1.20", "192.168.1.3"}

        with patch.object(scanner, "port_open", side_effect=fake_open):
            found = scanner.scan_hosts(
                ["192.168.1.1", "192.168.1.3", "192.168.1.20", "192.168.1.50"]
            )
        self.assertEqual(found, ["192.168.1.3", "192.168.1.20"])

    def test_discover_without_network(self) -> None:
        from unittest.mock import patch

        import core.network_scanner as scanner

        with patch.object(scanner, "local_ipv4", return_value=None):
            self.assertEqual(scanner.discover(), [])


class LanScanThreadTests(unittest.TestCase):
    def test_thread_connects_found_devices(self) -> None:
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        from workers.network_worker import LanScanThread

        app = QApplication.instance() or QApplication([])
        manager = mock.MagicMock(spec=AdbNetworkManager)
        manager.connect.side_effect = [
            NetworkResult(True, serial="192.168.1.3:5555", message="ok"),
        ]
        captured = {}

        def on_result(ips, results):
            captured["ips"] = ips
            captured["results"] = results
            app.quit()

        thread = LanScanThread(manager, 5555)
        thread.finished_with_result.connect(on_result)
        with mock.patch("workers.network_worker.discover_serials", return_value=["192.168.1.3:5555"]):
            thread.start()
            app.exec()
        self.assertEqual(captured["ips"], ["192.168.1.3:5555"])
        self.assertTrue(captured["results"][0].success)




class WorkerRobustnessTests(unittest.TestCase):
    """Workers must always emit their result signal, even on unexpected errors."""

    def _run_thread(self, thread) -> None:
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        self.app = QApplication.instance() or QApplication([])
        captured = {}
        thread.finished_with_result.connect(lambda *args: (captured.update(args=args), self.app.quit()))
        thread.start()
        self.app.exec()
        return captured["args"]

    def test_connect_thread_swallows_unexpected_errors(self) -> None:
        from workers.network_worker import NetworkConnectThread

        manager = mock.MagicMock(spec=AdbNetworkManager)
        manager.connect.side_effect = RuntimeError("boom")
        args = self._run_thread(NetworkConnectThread(manager, "192.168.1.23", 5555))
        self.assertEqual(len(args), 1)
        self.assertFalse(args[0].success)
        self.assertIn("boom", args[0].message)

    def test_disconnect_thread_swallows_unexpected_errors(self) -> None:
        from workers.network_worker import NetworkDisconnectThread

        manager = mock.MagicMock(spec=AdbNetworkManager)
        manager.disconnect.side_effect = RuntimeError("boom")
        args = self._run_thread(NetworkDisconnectThread(manager, "192.168.1.23", 5555))
        self.assertEqual(len(args), 1)
        self.assertFalse(args[0].success)

    def test_restart_thread_swallows_unexpected_errors(self) -> None:
        from workers.network_worker import ServerRestartThread

        manager = mock.MagicMock(spec=AdbNetworkManager)
        manager.restart_server.side_effect = RuntimeError("boom")
        args = self._run_thread(ServerRestartThread(manager))
        self.assertEqual(len(args), 2)
        self.assertFalse(args[0])

    def test_lan_scan_thread_swallows_unexpected_errors(self) -> None:
        from workers.network_worker import LanScanThread

        manager = mock.MagicMock(spec=AdbNetworkManager)
        manager.connect.side_effect = RuntimeError("boom")
        with mock.patch("workers.network_worker.discover_serials", return_value=["192.168.1.3:5555"]):
            args = self._run_thread(LanScanThread(manager, 5555))
        self.assertEqual(len(args), 2)
        self.assertEqual(args[1][0].success, False)


class SerialConsistencyTests(unittest.TestCase):
    def test_port_normalization_produces_canonical_serial(self) -> None:
        manager = run_manager()
        with mock.patch(
            "core.adb_network_manager.run_command",
            side_effect=[
                (0, "connected to 192.168.1.23:5555", ""),
                (0, "List of devices attached\n192.168.1.23:5555\tdevice", ""),
                (0, "smartcast_ok\n", ""),
            ],
        ) as mocked:
            result = manager.connect("192.168.1.23", "05555")
        self.assertTrue(result.success)
        self.assertEqual(result.serial, "192.168.1.23:5555")
        self.assertEqual(mocked.call_args_list[0][0][0][2], "192.168.1.23:5555")

    def test_parse_address_normalizes_leading_zero_port(self) -> None:
        ip, port, error = parse_address("192.168.1.23:05555")
        self.assertIsNone(error)
        self.assertEqual((ip, port), ("192.168.1.23", 5555))

    def test_shell_verify_timeout_is_failure_not_crash(self) -> None:
        manager = run_manager()
        with mock.patch(
            "core.adb_network_manager.run_command",
            side_effect=[
                (0, "connected to 192.168.1.23:5555", ""),
                (0, "List of devices attached\n192.168.1.23:5555\tdevice", ""),
                (124, "", "Command timed out"),
            ],
        ):
            result = manager.connect("192.168.1.23", 5555)
        self.assertFalse(result.success)
        self.assertIn("无响应", result.message)

    def test_already_connected_but_offline_still_fails(self) -> None:
        manager = run_manager()
        with mock.patch(
            "core.adb_network_manager.run_command",
            side_effect=[
                (0, "already connected to 192.168.1.23:5555", ""),
                (0, "List of devices attached\n192.168.1.23:5555\toffline", ""),
            ],
        ):
            result = manager.connect("192.168.1.23", 5555)
        self.assertFalse(result.success)
        self.assertTrue(result.already_connected)
        self.assertEqual(result.state, "offline")

    def test_disconnect_offline_device_is_success(self) -> None:
        manager = run_manager()
        with mock.patch("core.adb_network_manager.run_command", return_value=(0, "disconnected 192.168.1.23:5555", "")):
            result = manager.disconnect("192.168.1.23", 5555)
        self.assertTrue(result.success)




class MultiPortScanTests(unittest.TestCase):
    def test_scan_ports_finds_non_default_port(self) -> None:
        from unittest.mock import patch

        import core.network_scanner as scanner

        def fake_open(host, port, timeout=0.3):
            return (host, port) in {("192.168.1.9", 39401), ("192.168.1.4", 5555)}

        with patch.object(scanner, "port_open", side_effect=fake_open):
            serials = scanner.scan_ports(
                ["192.168.1.4", "192.168.1.9"],
                ports=[5555, 39401],
            )
        self.assertEqual(serials, ["192.168.1.4:5555", "192.168.1.9:39401"])

    def test_discover_serials_probes_recent_addresses(self) -> None:
        from unittest.mock import patch

        import core.network_scanner as scanner

        def fake_open(host, port, timeout=0.6):
            return (host, port) == ("10.23.224.216", 39401)

        with patch.object(scanner, "local_ipv4", return_value="192.168.1.100"), \
                patch.object(scanner, "port_open", side_effect=fake_open):
            serials = scanner.discover_serials(recent=["10.23.224.216:39401"])
        # nothing on the default sweep, but the remembered random-port device is found
        self.assertEqual(serials, ["10.23.224.216:39401"])

    def test_discover_serials_deduplicates_recent(self) -> None:
        from unittest.mock import patch

        import core.network_scanner as scanner

        def fake_open(host, port, timeout=0.3):
            return True

        with patch.object(scanner, "local_ipv4", return_value=None), \
                patch.object(scanner, "port_open", side_effect=fake_open):
            serials = scanner.discover_serials(recent=["192.168.1.3:5555", "192.168.1.3:5555", "bad"])
        self.assertEqual(serials, ["192.168.1.3:5555"])


class RecentAddressConfigTests(unittest.TestCase):
    def test_default_settings_include_recent_addresses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ConfigManager(Path(tmp))
            self.assertEqual(config.settings["recent_network_addresses"], [])

    def test_old_config_files_gain_recent_addresses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text('{"scan_interval": 3}', encoding="utf-8")
            config = ConfigManager(Path(tmp))
            self.assertEqual(config.settings["recent_network_addresses"], [])
            self.assertEqual(config.settings["scan_interval"], 3)

    def test_recent_addresses_round_trip(self) -> None:
        import json

        with tempfile.TemporaryDirectory() as tmp:
            config = ConfigManager(Path(tmp))
            config.settings["recent_network_addresses"] = ["10.23.224.216:39401"]
            config.save()
            reloaded = ConfigManager(Path(tmp))
            self.assertEqual(reloaded.settings["recent_network_addresses"], ["10.23.224.216:39401"])

    def test_non_list_recent_addresses_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text('{"recent_network_addresses": "junk"}', encoding="utf-8")
            config = ConfigManager(Path(tmp))
            self.assertEqual(config.settings["recent_network_addresses"], [])


if __name__ == "__main__":
    unittest.main()


