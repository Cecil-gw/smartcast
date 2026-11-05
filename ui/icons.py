from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication


_SVG = {
    "logo": '<rect x="6.5" y="2.5" width="11" height="19" rx="2.4"/><path d="M9.5 18.5h5"/><path d="M3 8.5a5.5 5.5 0 0 1 2-4.3"/><path d="M1 8.5a8 8 0 0 1 2.8-6.1"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.55V21h-4v-.08A1.7 1.7 0 0 0 9 19.37a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.63 15a1.7 1.7 0 0 0-1.55-1.03H3v-4h.08A1.7 1.7 0 0 0 4.63 9a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 9 4.63a1.7 1.7 0 0 0 1.03-1.55V3h4v.08A1.7 1.7 0 0 0 15 4.63a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 19.37 9a1.7 1.7 0 0 0 1.55 1.03H21v4h-.08A1.7 1.7 0 0 0 19.4 15z"/>',
    "refresh": '<path d="M20 11a8 8 0 1 0 1 5"/><path d="M20 4v7h-7"/>',
    "tablet": '<rect x="5" y="2.5" width="14" height="19" rx="2"/><path d="M10.5 18.5h3"/>',
    "home": '<path d="M3 10.5 12 3l9 7.5"/><path d="M5.5 9.5V20h13V9.5"/><path d="M10 20v-5.5h4V20"/>',
    "phone": '<rect x="7" y="2" width="10" height="20" rx="2.2"/><path d="M10.5 5.5h3"/><path d="M11 18.5h2"/>',
    "usb": '<path d="M12 21V7"/><path d="M12 7 8.5 10.5"/><path d="M12 7l3.5 3.5"/><circle cx="12" cy="4" r="2"/><path d="M6 13h12"/><path d="M6 13v3"/><path d="M18 13v3"/>',
    "wifi": '<path d="M5 12.5a10 10 0 0 1 14 0"/><path d="M8.5 16a5 5 0 0 1 7 0"/><circle cx="12" cy="19.5" r="1"/>',
    "play": '<path d="M8 5.5v13l11-6.5z" fill="{c}" stroke="none"/>',
    "stop": '<rect x="6" y="6" width="12" height="12" rx="2" fill="{c}" stroke="none"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><circle cx="12" cy="8" r=".8" fill="{c}" stroke="none"/>',
    "copy": '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
    "check": '<path d="M4.5 12.5 9 17 19.5 6.5"/>',
    "alert": '<path d="M10.3 3.9 2.4 18a2 2 0 0 0 1.8 3h15.6a2 2 0 0 0 1.8-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><circle cx="12" cy="17" r=".8" fill="{c}" stroke="none"/>',
    "monitor": '<rect x="2.5" y="4" width="19" height="13" rx="2"/><path d="M8 21h8"/><path d="M12 17v4"/>',
    "chip": '<rect x="7" y="7" width="10" height="10" rx="2"/><path d="M9 3v4M15 3v4M9 17v4M15 17v4M3 9h4M3 15h4M17 9h4M17 15h4"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "trash": '<path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="M6 7l1 14h10l1-14"/><path d="M10 11v6M14 11v6"/>',
    "export": '<path d="M12 3v12"/><path d="M7 8l5-5 5 5"/><path d="M5 15v5h14v-5"/>',
    "close": '<path d="M6 6l12 12M18 6 6 18"/>',
    "minus": '<path d="M5 12h14"/>',
    "maximize": '<rect x="6" y="6" width="12" height="12" rx="1.5"/>',
    "restore": '<rect x="8" y="5" width="11" height="11" rx="1.5"/><path d="M5.5 16.5v-9A2 2 0 0 1 7.5 5.5h9"/>',
    "back": '<path d="M19 12H5"/><path d="m11 18-6-6 6-6"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.6 2.6 0 1 1 4.2 2.1c-.9.7-1.7 1.2-1.7 2.4"/><circle cx="12" cy="17" r=".8" fill="{c}" stroke="none"/>',
    "bolt": '<path d="M13 2 4.5 13H11l-1 9 8.5-11H12z"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.1.1l2-2a5 5 0 0 0-7.1-7.1l-1.1 1.1"/><path d="M14 11a5 5 0 0 0-7.1-.1l-2 2A5 5 0 0 0 12 20l1.1-1.1"/>',
    "chevron-right": '<path d="m9 18 6-6-6-6"/>',
    "list": '<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="3.5" cy="6" r=".8" fill="{c}" stroke="none"/><circle cx="3.5" cy="12" r=".8" fill="{c}" stroke="none"/><circle cx="3.5" cy="18" r=".8" fill="{c}" stroke="none"/>',
    "hardware": '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M7 10h4M7 14h7"/>',
    "screen": '<rect x="4" y="3" width="16" height="14" rx="2"/><path d="M4 21h16"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "moon": '<path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5 8.5 8.5 0 1 0 20.5 14.2z"/>',
}


@lru_cache(maxsize=256)
def icon(name: str, color: str = "#F1F4F9", size: int = 18) -> QIcon:
    if QApplication.instance() is None:
        return QIcon()
    svg = _SVG.get(name)
    if not svg:
        return QIcon()
    svg = svg.replace("{c}", color)
    body = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
        'fill="none" stroke="' + color + '" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
        + svg + "</svg>"
    )
    renderer = QSvgRenderer(QByteArray(body.encode("utf-8")))
    scale = 2
    pixmap = QPixmap(size * scale, size * scale)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter, QRectF(0, 0, size * scale, size * scale))
    painter.end()
    pixmap.setDevicePixelRatio(scale)
    return QIcon(pixmap)

