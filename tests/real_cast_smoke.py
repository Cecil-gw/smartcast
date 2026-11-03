import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from core.adb_manager import AdbManager
from core.device_info import DeviceInfoReader
from core.encoder_detector import EncoderDetector
from core.scrcpy_manager import ScrcpyManager
from utils.config_manager import ConfigManager


app = QApplication(sys.argv)
config = ConfigManager()
adb = AdbManager(config.settings["adb_path"])
devices = adb.devices()
if not devices:
    print("no device connected; real cast smoke skipped")
    raise SystemExit(0)

device = DeviceInfoReader(adb).read(devices[0])
detector = EncoderDetector(adb)
codec = detector.optimize(device, "auto", detector.detect(device))
if codec is None:
    print("no supported encoder; real cast smoke skipped")
    raise SystemExit(0)

params = config.device_config(device.serial)["parameters"]
manager = ScrcpyManager(config.settings["scrcpy_path"])


def started(serial: str) -> None:
    print("started:", serial, "codec:", codec.codec)
    print("render_driver:", manager.render_driver)
    QTimer.singleShot(9000, lambda: manager.stop(serial))


def failed(serial: str, message: str) -> None:
    print("failed:", serial, message)
    app.exit(1)


def stopped(serial: str, code: int) -> None:
    print("stopped:", serial, "code:", code)
    app.exit(0 if code == 0 else 1)


manager.casting_started.connect(started)
manager.casting_failed.connect(failed)
manager.casting_stopped.connect(stopped)
accepted = manager.start(
    device,
    codec.codec,
    str(params.get("resolution", "original")),
    int(params.get("fps", 0)),
    int(params.get("bitrate_mbps", 8)),
    bool(params.get("audio", True)),
)
if not accepted:
    print("scrcpy start rejected")
    raise SystemExit(1)

QTimer.singleShot(25000, lambda: (print("real cast smoke timed out"), app.exit(2)))
raise SystemExit(app.exec())
