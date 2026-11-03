from __future__ import annotations

import re
from dataclasses import dataclass

from core.device_info import DeviceInfo
from core.encoder_detector import CodecCandidate


BITRATE_TIERS = (8, 12, 16, 24, 32, 48, 64, 96, 128)
_RESOLUTION_RE = re.compile(r"(\d+)\s*[x×]\s*(\d+)", re.I)


@dataclass(frozen=True)
class BitrateRecommendation:
    mbps: int
    summary: str
    detail: str
    codec: str
    hardware: bool
    pixels_million: float


def recommend_bitrate(
    device: DeviceInfo,
    candidates: list[CodecCandidate] | None,
    requested_codec: str = "auto",
    resolution: str = "original",
) -> BitrateRecommendation | None:
    native = _parse_resolution(device.resolution)
    effective_width, effective_height, resolution_label = _effective_resolution(native, resolution)
    pixels_million = (effective_width * effective_height) / 1_000_000 if effective_width and effective_height else 2.07

    selected = _select_codec(candidates or [], requested_codec)
    if selected is None:
        return None
    codec, hardware, encoder_note = selected
    if hardware:
        factor = 9.0 if codec == "H.265" else 14.0
    else:
        factor = 5.0
    raw_mbps = pixels_million * factor
    mbps = min(BITRATE_TIERS, key=lambda value: abs(value - raw_mbps))
    if not hardware:
        mbps = min(mbps, 16)
    mbps = max(8, min(128, mbps))
    detail = f"{resolution_label} · {codec} {'硬件' if hardware else '软件'}编码 · 约 {pixels_million:.1f} MP"
    if encoder_note:
        detail += f"（{encoder_note}）"
    return BitrateRecommendation(
        mbps=mbps,
        summary=f"推荐 {mbps} Mbps",
        detail=detail,
        codec=codec,
        hardware=hardware,
        pixels_million=pixels_million,
    )


def _parse_resolution(text: str) -> tuple[int, int] | None:
    match = _RESOLUTION_RE.search(text or "")
    if not match:
        return None
    width, height = int(match.group(1)), int(match.group(2))
    return (width, height) if width > 0 and height > 0 else None


def _effective_resolution(native: tuple[int, int] | None, resolution: str) -> tuple[int, int, str]:
    resolution = str(resolution or "original").lower().replace("p", "").strip()
    if native:
        native_long = max(native)
        native_short = min(native)
    else:
        native_long, native_short = 1920, 1080
    if resolution.isdigit():
        requested_long = int(resolution)
        scale = min(1.0, requested_long / native_long)
        width = max(1, round(native[0] * scale))
        height = max(1, round(native[1] * scale))
        return width, height, f"长边 {requested_long}px（约 {width}×{height}）"
    if native:
        return native[0], native[1], f"原生 {native[0]}×{native[1]}"
    return 1920, 1080, "原始分辨率（估算 1080p）"


def _select_codec(candidates: list[CodecCandidate], requested: str) -> tuple[str, bool, str] | None:
    requested = (requested or "auto").strip()
    if not candidates:
        codec = requested if requested in {"H.264", "H.265"} else "H.264"
        return codec, True, "编码器尚未检测，按硬件编码估算"
    aliases = {"h.264": "H.264", "h.265": "H.265", "h264": "H.264", "h265": "H.265", "hevc": "H.265"}
    wanted = aliases.get(requested.lower(), requested)
    if wanted in {"H.264", "H.265"}:
        matches = [item for item in candidates if item.codec == wanted]
        if not matches:
            return None
        best = max(matches, key=lambda item: (item.hardware, item.priority, item.encoder))
        return best.codec, best.hardware, best.encoder
    supported = [item for item in candidates if item.codec in {"H.264", "H.265"}]
    if not supported:
        return None
    best = max(supported, key=lambda item: (item.hardware, item.priority, item.encoder))
    return best.codec, best.hardware, best.encoder
