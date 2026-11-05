from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from utils.system_utils import writable_data_dir


APP_DIR = writable_data_dir()
CONFIG_DIR = APP_DIR / "config"


def _deep_merge(default: dict[str, Any], loaded: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(default)
    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class ConfigManager:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.config_dir = Path(base_dir) if base_dir else CONFIG_DIR
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.config_dir / "settings.json"
        self.devices_path = self.config_dir / "devices.json"
        loaded_settings = self._load(self.settings_path, {})
        self.settings: dict[str, Any] = _deep_merge(self.default_settings(), loaded_settings)
        self._normalize_settings()
        loaded_devices = self._load(self.devices_path, {})
        self.devices: dict[str, Any] = loaded_devices if isinstance(loaded_devices, dict) else {}
        self._normalize_devices()

    @staticmethod
    def default_settings() -> dict[str, Any]:
        return {
            "adb_path": "",
            "scrcpy_path": "",
            "recent_network_addresses": [],
            "background_enabled": True,
            "background_opacity": 1.0,
            "background_mode": "",
            "background_position": "",
            "window_geometry": {},
            "window_maximized": False,
            "animations_enabled": True,
            "animation_duration_scale": 1.0,
            "scan_interval": 2,
            "casting_scan_interval": 0,
            "auto_scan": True,
            "render_driver": "opengl",
            "theme": "light",
            "default_parameters": {
                "video_codec": "auto",
                "resolution": "original",
                "fps": 0,
                "bitrate_mbps": 8,
                "audio": True,
            },
        }

    _default_settings = default_settings

    def _load(self, path: Path, default: Any) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return copy.deepcopy(default)

    def _normalize_settings(self) -> None:
        try:
            self.settings["scan_interval"] = max(1, int(self.settings.get("scan_interval", 2)))
        except (TypeError, ValueError):
            self.settings["scan_interval"] = 2
        try:
            self.settings["casting_scan_interval"] = max(0, min(120, int(self.settings.get("casting_scan_interval", 0))))
        except (TypeError, ValueError):
            self.settings["casting_scan_interval"] = 0
        self.settings["auto_scan"] = bool(self.settings.get("auto_scan", True))
        self.settings["background_enabled"] = bool(self.settings.get("background_enabled", True))
        try:
            self.settings["background_opacity"] = max(0.0, min(1.0, float(self.settings.get("background_opacity", 1.0))))
        except (TypeError, ValueError):
            self.settings["background_opacity"] = 1.0
        mode = str(self.settings.get("background_mode", "") or "")
        self.settings["background_mode"] = mode if mode in {"fill", "right", "watermark"} else ""
        position = str(self.settings.get("background_position", "") or "")
        self.settings["background_position"] = position if position in {"left", "center", "right"} else ""
        geometry = self.settings.get("window_geometry")
        if not isinstance(geometry, dict):
            geometry = {}
        cleaned_geometry = {}
        for key in ("x", "y", "width", "height"):
            try:
                cleaned_geometry[key] = int(geometry.get(key))
            except (TypeError, ValueError):
                cleaned_geometry = {}
                break
        self.settings["window_geometry"] = cleaned_geometry
        self.settings["window_maximized"] = bool(self.settings.get("window_maximized", False))
        self.settings["animations_enabled"] = bool(self.settings.get("animations_enabled", True))
        try:
            self.settings["animation_duration_scale"] = max(0.0, min(2.0, float(self.settings.get("animation_duration_scale", 1.0))))
        except (TypeError, ValueError):
            self.settings["animation_duration_scale"] = 1.0
        recent = self.settings.get("recent_network_addresses")
        if not isinstance(recent, list):
            recent = []
        self.settings["recent_network_addresses"] = [
            text.strip() for text in recent if isinstance(text, str) and text.strip()
        ]
        render_driver = str(self.settings.get("render_driver", "opengl")).lower()
        if render_driver not in {"opengl", "auto", "direct3d", "software"}:
            render_driver = "opengl"
        self.settings["render_driver"] = render_driver
        theme = str(self.settings.get("theme", "light")).lower()
        if theme != "light":
            theme = "light"
        self.settings["theme"] = theme
        self.settings["default_parameters"] = self._normalize_parameters(self.settings.get("default_parameters", {}))

    def _normalize_devices(self) -> None:
        for serial, config in list(self.devices.items()):
            if not isinstance(config, dict):
                config = {}
                self.devices[serial] = config
            parameters = config.get("parameters", {})
            merged = _deep_merge(self.settings["default_parameters"], parameters if isinstance(parameters, dict) else {})
            config["parameters"] = self._normalize_parameters(merged)

    def _normalize_parameters(self, parameters: dict[str, Any]) -> dict[str, Any]:
        normalized = _deep_merge(self.default_settings()["default_parameters"], parameters)
        resolution = str(normalized.get("resolution", "original")).lower().replace("p", "")
        if resolution not in {"original", "auto", "720", "1080", "1440", "2560"}:
            resolution = "original"
        normalized["resolution"] = resolution
        try:
            normalized["fps"] = int(normalized.get("fps", 0))
        except (TypeError, ValueError):
            normalized["fps"] = 0
        try:
            normalized["bitrate_mbps"] = max(1, int(normalized.get("bitrate_mbps", 8)))
        except (TypeError, ValueError):
            normalized["bitrate_mbps"] = 8
        normalized["audio"] = bool(normalized.get("audio", True))
        return normalized

    def save(self) -> None:
        self.settings_path.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding="utf-8")
        self.devices_path.write_text(json.dumps(self.devices, ensure_ascii=False, indent=2), encoding="utf-8")

    def device_config(self, serial: str) -> dict[str, Any]:
        config = self.devices.setdefault(serial, {"parameters": copy.deepcopy(self.settings["default_parameters"])})
        config["parameters"] = self._normalize_parameters(config.get("parameters", {}))
        return config

    def set_default_parameters(self, parameters: dict[str, Any], serials: list[str] | None = None) -> None:
        normalized = self._normalize_parameters(parameters)
        self.settings["default_parameters"] = copy.deepcopy(normalized)
        for serial in serials or []:
            self.device_config(serial)["parameters"] = copy.deepcopy(normalized)


