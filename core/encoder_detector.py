import re
from dataclasses import dataclass

from core.adb_manager import AdbManager, AdbError
from core.device_info import DeviceInfo
from utils.logger import setup_logger


@dataclass(frozen=True)
class CodecCandidate:
    codec: str
    encoder: str
    hardware: bool
    priority: int


HARDWARE_HINTS = ("omx.", "c2.qti", "c2.exynos", "c2.mtk", "c2.unisoc", "c2.intel", "c2.amlogic")


class EncoderDetector:
    """Parses Android media codec inventory; no fake device data is generated."""

    def __init__(self, adb: AdbManager) -> None:
        self.adb = adb
        self.logger = setup_logger()

    def detect(self, device: DeviceInfo) -> list[CodecCandidate]:
        if device.state != "device":
            return []
        try:
            output = self.adb.shell(device.serial, "dumpsys media.codec", 4.0)
        except AdbError:
            self.logger.warning("media.codec unavailable: %s", device.serial)
            output = ""
        if "encoder infos by media types" not in output.lower():
            try:
                player_output = self.adb.shell(device.serial, "dumpsys media.player", 4.0)
                if "encoder infos by media types" in player_output.lower():
                    output = player_output
            except AdbError:
                self.logger.warning("media.player unavailable: %s", device.serial)
        if not output:
            return []
        candidates: dict[str, CodecCandidate] = {}
        encoder_pattern = re.compile(r"\b((?:omx|c2)[\w.\-]*(?:avc|hevc|vp8|vp9|h264|h265)[\w.\-]*encoder)\b", re.I)
        for line in output.splitlines():
            lower = line.lower()
            codec_match = re.search(r"(avc|h264|hevc|h265|vp8|vp9)", lower)
            encoder_match = encoder_pattern.search(line)
            if not codec_match or "encoder" not in lower:
                continue
            codec = "H.265" if {"hevc", "h265"} & set(codec_match.groups()) else codec_match.group(1).upper()
            codec = {"AVC": "H.264", "H264": "H.264", "HEVC": "H.265"}.get(codec, codec)
            encoder = encoder_match.group(1) if encoder_match else f"generic.{codec}"
            hardware = any(hint in lower for hint in HARDWARE_HINTS) and not encoder.lower().startswith(("c2.android.", "omx.google."))
            priority = (hardware * 10) + (codec == "H.265") * 2 + (codec == "H.264")
            key = (codec, encoder)
            if key not in candidates or priority > candidates[key].priority:
                candidates[key] = CodecCandidate(codec, encoder, hardware, priority)
        ordered = sorted(candidates.values(), key=lambda item: item.priority, reverse=True)
        self.logger.info("Detected codecs for %s: %s", device.serial, ordered)
        return ordered

    def optimize(self, device: DeviceInfo, requested: str, candidates: list[CodecCandidate]) -> CodecCandidate | None:
        supported_by_scrcpy = {"H.264", "H.265"}
        if requested == "auto":
            return next((item for item in candidates if item.codec in supported_by_scrcpy), None)
        aliases = {"h.265": "H.265", "h.264": "H.264", "vp8": "VP8", "vp9": "VP9"}
        wanted = aliases.get(requested.lower(), requested)
        if wanted not in supported_by_scrcpy:
            return None
        return next((item for item in candidates if item.codec == wanted), None)
