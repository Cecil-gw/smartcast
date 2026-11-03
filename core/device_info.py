from dataclasses import dataclass

from core.adb_manager import AdbError, AdbManager, RawDevice

CONNECTION_USB = 'usb'
CONNECTION_WIFI = 'wifi'
CONNECTION_EMULATOR = 'emulator'
CONNECTION_UNKNOWN = 'unknown'


def connection_type_for_serial(serial: str) -> str:
    text = (serial or '').strip()
    if not text:
        return CONNECTION_UNKNOWN
    lowered = text.lower()
    if lowered.startswith('emulator-'):
        return CONNECTION_EMULATOR
    host, sep, port = text.rpartition(':')
    if sep and host and port.isdigit() and 1 <= int(port) <= 65535:
        return CONNECTION_WIFI
    return CONNECTION_USB


@dataclass
class DeviceInfo:
    serial: str
    state: str
    manufacturer: str = "未知"
    brand: str = "未知"
    model: str = "未知"
    android_version: str = "未知"
    sdk: str = "未知"
    resolution: str = "未知"
    density: str = "未知"
    connection_type: str = CONNECTION_USB


class DeviceInfoReader:
    def __init__(self, adb: AdbManager) -> None:
        self.adb = adb

    def read(self, raw: RawDevice) -> DeviceInfo:
        info = DeviceInfo(serial=raw.serial, state=raw.state, connection_type=connection_type_for_serial(raw.serial))
        if raw.state != "device":
            return info
        script = (
            "getprop ro.product.manufacturer; getprop ro.product.brand; getprop ro.product.model; "
            "getprop ro.build.version.release; getprop ro.build.version.sdk; "
            "echo __SMARTCAST_SIZE__; wm size; echo __SMARTCAST_DENSITY__; wm density"
        )
        try:
            output = self.adb.shell(raw.serial, script, 8.0)
            lines = [line.strip() for line in output.splitlines()]
            size_index = lines.index("__SMARTCAST_SIZE__")
            density_index = lines.index("__SMARTCAST_DENSITY__")
            props = lines[:size_index]
            if len(props) >= 5:
                info.manufacturer, info.brand, info.model, info.android_version, info.sdk = props[:5]
            size_lines = lines[size_index + 1:density_index]
            density_lines = lines[density_index + 1:]
            info.resolution = self._pick_value(size_lines, "Physical size:", "size:") or "未知"
            info.density = self._pick_value(density_lines, "Physical density:", "density:") or "未知"
            return info
        except (AdbError, ValueError):
            pass
        properties = {
            "manufacturer": "ro.product.manufacturer",
            "brand": "ro.product.brand",
            "model": "ro.product.model",
            "android_version": "ro.build.version.release",
            "sdk": "ro.build.version.sdk",
        }
        for key, prop in properties.items():
            try:
                setattr(info, key, self.adb.shell(raw.serial, f"getprop {prop}"))
            except AdbError:
                self.adb.logger.warning("读取 %s 失败：%s", prop, raw.serial)
        try:
            size = self.adb.shell(raw.serial, "wm size").replace("Physical size:", "").strip()
            density = self.adb.shell(raw.serial, "wm density").replace("Physical density:", "").strip()
            info.resolution, info.density = size or "未知", density or "未知"
        except AdbError:
            pass
        return info

    @staticmethod
    def _pick_value(lines: list[str], *prefixes: str) -> str:
        for line in lines:
            for prefix in prefixes:
                if line.startswith(prefix):
                    return line.split(":", 1)[1].strip()
        return next((line for line in lines if line), "")
