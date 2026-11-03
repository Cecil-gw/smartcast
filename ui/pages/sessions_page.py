from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.cast_session import CastSession, SESSION_ERROR, SESSION_RUNNING
from core.device_info import CONNECTION_WIFI
from ui.components.common import StatusPill
from ui.icons import icon
from ui.theme import COLORS


class SessionCard(QFrame):
    stop_requested = Signal(str)
    fullscreen_requested = Signal(str)

    def __init__(self, session: CastSession, parent=None) -> None:
        super().__init__(parent)
        self.session = session
        self.setObjectName("DeviceCard")
        self.setMinimumHeight(96)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(12)

        icon_tile = QFrame()
        icon_tile.setObjectName("IconBadge")
        icon_tile.setFixedSize(42, 42)
        icon_layout = QHBoxLayout(icon_tile)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        phone = QLabel()
        phone.setPixmap(icon("monitor", COLORS["accent_hover"], 22).pixmap(22, 22))
        phone.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(phone)
        row.addWidget(icon_tile, 0, Qt.AlignTop)

        info = QVBoxLayout()
        info.setSpacing(3)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        name = QLabel(f"{session.model} · {session.serial}")
        name.setObjectName("CardTitle")
        title_row.addWidget(name)
        self.type_pill = StatusPill(session.connection_label(), "info")
        title_row.addWidget(self.type_pill)
        self.state_pill = StatusPill(session.state_label(), "success" if session.state == SESSION_RUNNING else "idle")
        title_row.addWidget(self.state_pill)
        title_row.addStretch()
        info.addLayout(title_row)

        self.params_label = QLabel(session.params_text())
        self.params_label.setObjectName("Muted")
        self.params_label.setWordWrap(True)
        info.addWidget(self.params_label)
        row.addLayout(info, 1)

        duration_column = QVBoxLayout()
        duration_column.setSpacing(2)
        self.duration_label = QLabel(session.duration_text())
        self.duration_label.setObjectName("InfoValue")
        self.duration_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        duration_column.addWidget(self.duration_label)
        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        fullscreen = QPushButton("全屏")
        fullscreen.setObjectName("GhostButton")
        fullscreen.setIcon(icon("screen", COLORS["muted"], 13))
        fullscreen.setIconSize(QSize(13, 13))
        fullscreen.setCursor(Qt.PointingHandCursor)
        fullscreen.clicked.connect(lambda: self.fullscreen_requested.emit(self.session.serial))
        stop = QPushButton("停止")
        stop.setObjectName("GhostButton")
        stop.setIcon(icon("stop", COLORS["muted"], 12))
        stop.setIconSize(QSize(12, 12))
        stop.setCursor(Qt.PointingHandCursor)
        stop.clicked.connect(lambda: self.stop_requested.emit(self.session.serial))
        buttons.addWidget(fullscreen)
        buttons.addWidget(stop)
        duration_column.addLayout(buttons)
        row.addLayout(duration_column)

    def refresh(self, session: CastSession) -> None:
        self.session = session
        self.state_pill.setText(session.state_label())
        tone = "success" if session.state == SESSION_RUNNING else ("error" if session.state == SESSION_ERROR else "idle")
        self.state_pill.set_tone(tone)
        self.type_pill.setText(session.connection_label())
        self.params_label.setText(session.params_text())
        self.duration_label.setText(session.duration_text())


class SessionsPage(QWidget):
    stop_requested = Signal(str)
    fullscreen_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        title_column = QVBoxLayout()
        title_column.setSpacing(3)
        title = QLabel("投屏中心")
        title.setObjectName("PageTitle")
        subtitle = QLabel("统一管理所有投屏会话的状态、时长与参数")
        subtitle.setObjectName("PageSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        header = QHBoxLayout()
        header.addLayout(title_column, 1)
        self.count_pill = StatusPill("0 个会话", "idle")
        header.addWidget(self.count_pill, 0, Qt.AlignVCenter)
        root.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.host = QWidget()
        self.layout_area = QVBoxLayout(self.host)
        self.layout_area.setContentsMargins(0, 0, 4, 0)
        self.layout_area.setSpacing(10)
        self.layout_area.addStretch(1)
        self.empty = QLabel("当前没有投屏会话。在设备管理页选择设备开始投屏。")
        self.empty.setObjectName("Caption")
        self.empty.setAlignment(Qt.AlignCenter)
        self.layout_area.insertWidget(0, self.empty)
        self.scroll.setWidget(self.host)
        root.addWidget(self.scroll, 1)

        self.cards: dict[str, SessionCard] = {}

        # UI-only refresh for durations; no ADB commands here.
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick_durations)
        self._timer.start()

    def refresh_sessions(self, sessions: list[CastSession]) -> None:
        current = {s.serial: s for s in sessions}
        for serial in list(self.cards):
            if serial not in current:
                card = self.cards.pop(serial)
                self.layout_area.removeWidget(card)
                card.deleteLater()
        for session in sessions:
            card = self.cards.get(session.serial)
            if card is None:
                card = SessionCard(session)
                card.stop_requested.connect(self.stop_requested)
                card.fullscreen_requested.connect(self.fullscreen_requested)
                self.cards[session.serial] = card
                self.layout_area.insertWidget(self.layout_area.count() - 1, card)
            else:
                card.refresh(session)
        self.empty.setVisible(not sessions)
        running = sum(1 for s in sessions if s.state == SESSION_RUNNING)
        self.count_pill.setText(f"{len(sessions)} 个会话")
        self.count_pill.set_tone("success" if running else "idle")

    def _tick_durations(self) -> None:
        for card in self.cards.values():
            if card.session.state == SESSION_RUNNING:
                card.duration_label.setText(card.session.duration_text())
