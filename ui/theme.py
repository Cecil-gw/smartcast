from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QObject,
    QRect,
    QSize,
    QTimer,
    Qt,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QImageReader, QPainter, QPixmap
from PySide6.QtWidgets import QGridLayout, QWidget

from utils.logger import setup_logger
from utils.system_utils import resource_path


COLORS = {
    "bg": "#F7F8F5",
    "surface": "#FFFFFF",
    "panel": "#F2F5F2",
    "card": "#FFFFFF",
    "card_alt": "#F7FAF7",
    "hover": "#EDF3EF",
    "accent": "#59816F",
    "accent_hover": "#6C937F",
    "accent_pressed": "#4B6E5E",
    "accent_soft": "#E6EFE9",
    "success": "#4F9D75",
    "warning": "#C08A4D",
    "error": "#C76F6F",
    "text": "#1E2A25",
    "muted": "#64748B",
    "faint": "#879691",
    "border": "#DDE5DF",
    "border_strong": "#C9D5CD",
    "sidebar": "#EEF3EF",
}

LIGHT_STYLE = f"""
QWidget {{
    color: {COLORS['text']};
    font-family: "Microsoft YaHei UI", "Segoe UI";
    font-size: 13px;
}}
QMainWindow {{ background: transparent; }}
QDialog {{ background: {COLORS['bg']}; }}
QWidget#PageHost, QWidget#PageSurface, QWidget#BackgroundLayer {{ background: transparent; }}
QStackedWidget {{ background: transparent; border: none; }}
QStackedWidget > QWidget {{ background: transparent; }}
QScrollArea > QWidget#qt_scrollarea_viewport {{ background: transparent; }}
QScrollArea > QWidget > QWidget#qt_scrollarea_viewport {{ background: transparent; }}
QWidget#RootShell {{
    background: {COLORS['bg']};
    border-radius: 12px;
}}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QToolTip {{
    background: #FFFFFF;
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 7px;
    padding: 6px 9px;
}}

QWidget#Sidebar {{
    background: {COLORS['sidebar']};
    border: none;
    border-right: 1px solid {COLORS['border']};
}}
QFrame#SidebarBrand, QFrame#SidebarNav, QFrame#SidebarFooter {{ background: transparent; border: none; }}
QFrame#HeaderBar {{
    background: {COLORS['surface']};
    border: none;
    border-bottom: 1px solid {COLORS['border']};
}}
QFrame#HeaderStatusChip {{
    background: transparent;
    border: none;
    border-radius: 0;
}}
QFrame#StatusBar {{ background: transparent; border: none; border-top: 1px solid {COLORS['border']}; }}
QFrame#Card, QFrame#QuickPanel, QFrame#SettingsSection, QFrame#HeroCard,
QFrame#StatCard, QFrame#ActionCard, QFrame#DeviceCard {{
    background: {COLORS['card']};
QFrame#ConfigCard {{ background: rgba(255, 255, 255, 0.40); }}
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
}}
QFrame#QuickPanel {{ background: transparent; border: none; }}
/* 功能面板半透明，让背景插画自然透出；文字仍为深色，对比度充足 */
QFrame#SettingsSection {{ background: rgba(255, 255, 255, 0.25); }}
QFrame#SettingsSection:hover {{ background: rgba(255, 255, 255, 0.45); }}
QFrame#DeviceCard:hover {{ background: #FBFDFB; border-color: {COLORS['border_strong']}; }}
QFrame#DeviceCard[casting="true"] {{ border-color: #A7C7B7; background: #F7FBF8; }}
QFrame#InfoTile {{ background: transparent; border: none; }}
QFrame#CodecPanel {{
    background: {COLORS['card_alt']};
    border: 1px solid {COLORS['border']};
    border-radius: 9px;
}}
QFrame#Divider {{ background: {COLORS['border']}; max-height: 1px; border: none; }}
QFrame#VerticalDivider {{ background: {COLORS['border']}; max-width: 1px; border: none; }}
QFrame#EmptyIllustration {{ background: transparent; border: none; }}
QFrame#IconBadge {{
    background: {COLORS['accent_soft']};
    border: 1px solid #D4E3D9;
    border-radius: 9px;
}}
QFrame#LogoTile {{ background: {COLORS['accent']}; border: none; border-radius: 10px; }}
QFrame#ConfigTabs {{
    background: {COLORS['panel']};
    border: 1px solid {COLORS['border']};
    border-radius: 9px;
}}
QFrame#Toast {{
    background: #FFFFFF;
    border: 1px solid {COLORS['border_strong']};
    border-radius: 10px;
}}
QFrame#Toast[tone="success"] {{ border-color: #B7D9C6; }}
QFrame#Toast[tone="error"] {{ border-color: #E3BDBD; }}
QFrame#Toast[tone="warning"] {{ border-color: #E6D2B0; }}
QLabel#ProductName {{ font-size: 17px; font-weight: 700; }}
QLabel#PageTitle {{ font-size: 22px; font-weight: 700; }}
QLabel#PageSubtitle {{ color: {COLORS['muted']}; font-size: 12px; }}
QLabel#SectionTitle {{ font-size: 15px; font-weight: 650; }}
QLabel#GuideSectionTitle {{ font-size: 17px; font-weight: 700; }}
QLabel#SectionDescription {{ color: {COLORS['muted']}; font-size: 12px; }}
QLabel#CardTitle {{ font-size: 16px; font-weight: 700; }}
QLabel#Muted {{ color: {COLORS['muted']}; }}
QLabel#Caption {{ color: {COLORS['faint']}; font-size: 11px; }}
QLabel#InfoLabel {{ color: {COLORS['muted']}; font-size: 11px; }}
QLabel#InfoValue {{ color: {COLORS['text']}; font-size: 12px; font-weight: 600; }}
QLabel#MetricValue {{ color: {COLORS['text']}; font-size: 16px; font-weight: 700; }}
QLabel#ActionTitle {{ color: {COLORS['text']}; font-size: 13px; font-weight: 700; }}
QLabel#SerialLabel {{ color: {COLORS['muted']}; font-family: "Cascadia Mono", "Consolas"; font-size: 11px; }}
QLabel#MonoLabel {{ font-family: "Cascadia Mono", "Consolas"; font-size: 11px; }}
QLabel#CodecName {{ font-family: "Cascadia Mono", "Consolas"; font-size: 10px; }}
QLabel#HeroTitle {{ font-size: 23px; font-weight: 700; }}
QLabel#EmptyTitle {{ font-size: 20px; font-weight: 700; }}
QLabel#EmptyDescription {{ color: {COLORS['muted']}; font-size: 13px; }}
QLabel#ToastLabel {{ font-size: 12px; font-weight: 600; }}
QLabel#NavTitle {{ color: {COLORS['faint']}; font-size: 10px; font-weight: 700; }}
QLabel#SidebarVersion {{ color: {COLORS['faint']}; font-size: 10px; }}
QLabel#SidebarName {{ color: {COLORS['text']}; font-size: 14px; font-weight: 700; }}
QLabel#StatusPill {{
    background: {COLORS['panel']};
    color: {COLORS['muted']};
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 3px 9px;
    font-size: 10px;
    font-weight: 650;
}}
QLabel#StatusPill[tone="success"] {{ background: #E9F5EE; color: #36795A; }}
QLabel#StatusPill[tone="warning"] {{ background: #F8EFD8; color: #8A6320; }}
QLabel#StatusPill[tone="error"] {{ background: #F7E7E7; color: #A34A4A; }}
QLabel#StatusPill[tone="info"] {{ background: {COLORS['accent_soft']}; color: #4E7362; }}
QLabel#StatusPill[tone="idle"] {{ background: {COLORS['panel']}; color: {COLORS['muted']}; }}
QLabel#Chip {{
    background: {COLORS['panel']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
    padding: 3px 9px;
    color: {COLORS['muted']};
    font-size: 11px;
}}
QLabel#Chip[tone="success"] {{ color: #36795A; background: #E9F5EE; border-color: #CFE7D8; }}
QLabel#Chip[tone="error"] {{ color: #A34A4A; background: #F7E7E7; border-color: #EBCACA; }}
QLabel#RecommendTitle {{ color: {COLORS['accent']}; font-weight: 650; font-size: 12px; }}
QLabel#ConfigStatus {{ color: {COLORS['muted']}; font-size: 11px; }}
QLabel#ConfigStatus[tone="success"] {{ color: {COLORS['success']}; }}
QLabel#ConfigStatus[tone="warning"] {{ color: {COLORS['warning']}; }}
QLabel#ConfigStatus[tone="error"] {{ color: {COLORS['error']}; }}
QLabel#FooterStatus {{ color: {COLORS['muted']}; font-size: 11px; }}
QLabel#FooterStatus[tone="success"] {{ color: {COLORS['success']}; }}
QLabel#FooterStatus[tone="error"] {{ color: {COLORS['error']}; }}
QLabel#BitrateHint {{ color: {COLORS['muted']}; font-size: 11px; }}
QLabel#BitrateHint[tone="success"] {{ color: {COLORS['success']}; }}
QLabel#BitrateHint[tone="warning"] {{ color: {COLORS['warning']}; }}
QLabel#CodecGroupHeading {{ color: {COLORS['muted']}; font-weight: 650; font-size: 12px; }}
QLabel#CodecGroupHeading[tone="success"] {{ color: {COLORS['success']}; }}
QLabel#StatusMessage {{ color: {COLORS['muted']}; font-size: 11px; }}
QLabel#StatusMessage[tone="success"] {{ color: {COLORS['success']}; }}
QLabel#StatusMessage[tone="warning"] {{ color: {COLORS['warning']}; }}
QLabel#StatusMessage[tone="error"] {{ color: {COLORS['error']}; }}

QPushButton {{
    background: {COLORS['panel']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border_strong']};
    border-radius: 8px;
    padding: 0 14px;
    min-height: 32px;
    font-weight: 600;
}}
QPushButton:hover {{ background: #E7EFE9; border-color: #B8C9BF; }}
QPushButton:pressed {{ background: #E2EBE5; }}
QPushButton:disabled {{ background: #F0F3F0; color: #98A5B5; border-color: {COLORS['border']}; }}
QPushButton#PrimaryButton {{
    background: {COLORS['accent']};
    color: #FFFFFF;
    border: 1px solid {COLORS['accent']};
}}
QPushButton#PrimaryButton:hover {{ background: {COLORS['accent_hover']}; border-color: {COLORS['accent_hover']}; }}
QPushButton#PrimaryButton:pressed {{ background: {COLORS['accent_pressed']}; border-color: {COLORS['accent_pressed']}; }}
QPushButton#PrimaryButton:disabled {{ background: #D5E2DB; color: #7C8C84; border-color: #D5E2DB; }}
QPushButton#DangerButton {{ background: #F7E7E7; color: #A34A4A; border-color: #EBCACA; }}
QPushButton#DangerButton:hover {{ background: #F2DBDB; }}
QPushButton#GhostButton {{ background: transparent; border: 1px solid transparent; color: {COLORS['muted']}; }}
QPushButton#GhostButton:hover {{ background: {COLORS['panel']}; color: {COLORS['text']}; }}
QPushButton#IconButton {{
    background: transparent;
    border: 1px solid transparent;
    padding: 0;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    border-radius: 8px;
}}
QPushButton#IconButton:hover {{ background: {COLORS['panel']}; border-color: {COLORS['border']}; }}
QFrame#TitleBar {{
    background: transparent;
    border: none;
}}
QPushButton#TitleControlButton {{
    background: transparent;
    border: none;
    border-radius: 0;
    padding: 0;
}}
QPushButton#TitleControlButton:hover, QPushButton#TitleControlButton:pressed {{
    background: transparent;
    border: none;
}}
QPushButton#TopIconButton {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    border-radius: 8px;
    padding: 0;
}}
QPushButton#TopIconButton:hover {{ background: {COLORS['panel']}; border-color: {COLORS['border_strong']}; }}
QPushButton#SettingsButton {{ background: {COLORS['panel']}; border: 1px solid {COLORS['border']}; min-width: 76px; }}
QPushButton#LinkButton {{ background: transparent; border: none; color: {COLORS['accent']}; padding: 0 4px; min-height: 24px; }}
QPushButton#LinkButton:hover {{ color: {COLORS['accent_hover']}; }}
QFrame#StatCell {{
    background: transparent;
    border: none;
}}
QPushButton#QuickAction {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 6px 10px;
    color: {COLORS['text']};
    font-size: 12px;
    font-weight: 600;
    text-align: left;
}}
QPushButton#QuickAction:hover {{
    background: {COLORS['hover']};
    border-color: {COLORS['border']};
}}
QPushButton#QuickAction:pressed {{
    background: {COLORS['accent_soft']};
}}
QWidget#SquareAction {{
    background: rgba(255, 255, 255, 0.42);
    border: 1px solid rgba(213, 224, 217, 0.65);
    border-radius: 8px;
}}
QWidget#SquareAction:hover {{
    background: {COLORS['accent_soft']};
    border-color: rgba(193, 214, 200, 0.9);
}}
QWidget#SquareAction:pressed {{
    background: #D6E6DC;
}}
QWidget#SquareAction[disabled="true"] {{
    background: rgba(255, 255, 255, 0.22);
    border-color: rgba(213, 224, 217, 0.4);
}}
QLabel#SquareActionText {{
    color: {COLORS['text']};
    font-size: 10px;
    font-weight: 600;
    background: transparent;
}}
QLabel#SquareActionText[disabled="true"] {{
    color: {COLORS['faint']};
}}
QPushButton#NavButton {{
    background: transparent;
    color: {COLORS['muted']};
    border: 1px solid transparent;
    border-radius: 9px;
    min-height: 40px;
    padding: 0 12px;
    text-align: left;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#NavButton:hover {{ background: #E6EEE8; color: {COLORS['text']}; }}
QPushButton#NavButton[active="true"] {{
    background: #DFEAE2;
    color: #345245;
    border: 1px solid #CFDFD5;
    font-weight: 650;
}}
QPushButton#PanelTab {{
    background: transparent;
    color: {COLORS['muted']};
    border: none;
    border-radius: 8px;
    padding: 0 12px;
    min-height: 34px;
    font-weight: 600;
}}
QPushButton#PanelTab:hover {{ color: {COLORS['text']}; background: #E9EFEA; }}
QPushButton#PanelTab[active="true"] {{ background: {COLORS['accent_soft']}; color: #3F6555; }}
QPushButton#AccordionButton {{
    background: {COLORS['panel']};
    border: 1px solid {COLORS['border']};
    border-radius: 9px;
    color: {COLORS['muted']};
    padding: 0 13px;
    text-align: left;
    min-height: 40px;
}}
QPushButton#AccordionButton:hover {{ background: #E7EFE9; color: {COLORS['text']}; }}

QLineEdit, QSpinBox, QComboBox {{
    background: #FBFDFB;
    border: 1px solid {COLORS['border_strong']};
    border-radius: 7px;
    padding: 0 10px;
    min-height: 32px;
    selection-background-color: {COLORS['accent']};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border: 1px solid {COLORS['accent']}; }}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{ color: #98A5B5; background: #F2F5F2; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: #FFFFFF;
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: {COLORS['accent_soft']};
    outline: none;
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 20px; background: {COLORS['panel']}; border: none; }}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background: #E7EFE9; }}

QCheckBox {{ spacing: 8px; color: {COLORS['muted']}; }}
QCheckBox::indicator {{
    width: 17px; height: 17px;
    border-radius: 5px;
    border: 1px solid {COLORS['border_strong']};
    background: #FFFFFF;
}}
QCheckBox::indicator:hover {{ border-color: {COLORS['accent']}; }}
QCheckBox::indicator:checked {{ background: {COLORS['accent']}; border-color: {COLORS['accent']}; }}

QScrollBar:vertical {{ background: transparent; width: 9px; margin: 2px 1px; }}
QScrollBar::handle:vertical {{ background: #C9D5CD; min-height: 32px; border-radius: 4px; }}
QScrollBar::handle:vertical:hover {{ background: #B7C7BD; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 9px; }}
QScrollBar::handle:horizontal {{ background: #C9D5CD; min-width: 32px; border-radius: 4px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QTextEdit#LogView {{
    background: rgba(255, 255, 255, 0.40);
    border: 1px solid {COLORS['border']};
    border-radius: 9px;
    color: {COLORS['muted']};
    font-family: "Cascadia Mono", "Consolas";
    font-size: 11px;
    padding: 8px;
}}
QSplitter::handle {{ background: transparent; }}
QLabel#StepBadge {{
    background: {COLORS['accent_soft']};
    color: #3F6555;
    border: 1px solid #D4E3D9;
    border-radius: 14px;
    font-size: 10px;
    font-weight: 700;
}}
"""

# Compatibility name retained for older imports; SmartCast now always uses the light theme.
DARK_STYLE = LIGHT_STYLE


def stylesheet_for(theme: str) -> str:
    return LIGHT_STYLE


# ============================================================
# 页面背景系统：图片由用户放入 resources/assets/illustrations/<页面>/
# 缺失或损坏时自动回退纯色；绘制层不拦截鼠标事件。
# ============================================================
MODE_FILL = "fill"
MODE_RIGHT = "right"
MODE_WATERMARK = "watermark"
DISPLAY_MODES = (MODE_FILL, MODE_RIGHT, MODE_WATERMARK)

POSITION_LEFT = "left"
POSITION_CENTER = "center"
POSITION_RIGHT = "right"
POSITIONS = (POSITION_LEFT, POSITION_CENTER, POSITION_RIGHT)

# 单张背景图的最大解码尺寸，避免超大图片占用过多内存
MAX_DECODE_EDGE = 2560


@dataclass(frozen=True)
class BackgroundSpec:
    """一个页面的背景配置（集中管理，不在页面中硬编码路径）。"""

    key: str
    mode: str = MODE_RIGHT
    position: str = POSITION_RIGHT
    opacity: float = 0.55
    mask_alpha: int = 42
    offset_x_ratio: float = 0.0  # 整体向右偏移（占页面宽度的比例），用于微调人物位置

    @property
    def relative_path(self) -> str:
        return f"resources/assets/illustrations/{self.key}/background.png"


# 页面 ID → 背景配置。用户把同名图片放进对应目录即可生效。
BACKGROUND_SPECS: dict[str, BackgroundSpec] = {
    # 竖版人物立绘：右侧贴底完整显示，透明度较高保持人物清晰；
    # 立绘自带透明背景，左侧内容区天然无遮挡。
    "home": BackgroundSpec("home", MODE_RIGHT, POSITION_RIGHT, 0.95, 0),
    "devices": BackgroundSpec("devices", MODE_RIGHT, POSITION_RIGHT, 0.92, 0),
    "casting": BackgroundSpec("casting", MODE_RIGHT, POSITION_RIGHT, 0.92, 0),
    "control": BackgroundSpec("control", MODE_RIGHT, POSITION_RIGHT, 0.88, 0),
    "media": BackgroundSpec("media", MODE_RIGHT, POSITION_RIGHT, 0.92, 0),
    # 投屏设置：沿用原「设置」插画（该图右侧有透明留白，需要轻微右移）
    "cast_settings": BackgroundSpec("cast_settings", MODE_RIGHT, POSITION_RIGHT, 0.70, 0, offset_x_ratio=0.10),
    # 设置：新插画，贴右下即可
    "settings": BackgroundSpec("settings", MODE_RIGHT, POSITION_RIGHT, 0.78, 0),
    "logs": BackgroundSpec("logs", MODE_RIGHT, POSITION_RIGHT, 0.55, 24),
}

# 主题遮罩：浅色用更亮的遮罩，深色预留暗色遮罩
MASK_COLORS = {
    "light": QColor(247, 248, 245),
    "dark": QColor(24, 28, 26),
}
BASE_COLORS = {
    "light": QColor(247, 248, 245),
    "dark": QColor(24, 28, 26),
}


class BackgroundColorLayer(QWidget):
    """纯色 + 主题遮罩的最底层，永远不透明，保证页面切换无白色闪烁。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("BackgroundColorLayer")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._theme = "light"
        self._mask_alpha = 34

    def set_theme(self, theme: str) -> None:
        self._theme = "dark" if theme == "dark" else "light"
        self.update()


    def set_mask_alpha(self, alpha: int) -> None:
        self._mask_alpha = max(0, min(255, int(alpha)))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), BASE_COLORS[self._theme])
        mask = QColor(MASK_COLORS[self._theme])
        mask.setAlpha(self._mask_alpha)
        painter.fillRect(self.rect(), mask)


class BackgroundLayer(QWidget):
    """绘制背景图片的最底层控件；始终忽略鼠标事件。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("BackgroundLayer")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setFocusPolicy(Qt.NoFocus)
        self._source: QPixmap | None = None
        self._scaled: QPixmap | None = None
        self._mode = MODE_RIGHT
        self._position = POSITION_RIGHT
        self._opacity = 0.55
        self._mask_alpha = 42
        self._theme = "light"
        self._fill_base = False
        self._offset_x_ratio = 0.0
        self._zoom = 1.0
        self._zoom_anim = None
        self._animations_enabled = True
        # 拖拽缩放时延迟重采样，避免每个 resize 事件都做一次高质量缩放（抖动来源）
        self._resample_timer = QTimer(self)
        self._resample_timer.setSingleShot(True)
        self._resample_timer.setInterval(120)
        self._resample_timer.timeout.connect(self._recompute)

    # -- setters -------------------------------------------------------
    def set_source(self, pixmap: QPixmap | None) -> None:
        self._source = pixmap
        self._scaled = None
        self._recompute()
        self.update()

    def set_mode(self, mode: str) -> None:
        if mode not in DISPLAY_MODES:
            return
        self._mode = mode
        self._scaled = None
        self._recompute()
        self.update()

    def set_position(self, position: str) -> None:
        if position not in POSITIONS:
            return
        self._position = position
        self._scaled = None
        self._recompute()
        self.update()

    def set_opacity(self, opacity: float) -> None:
        self._opacity = max(0.0, min(1.0, float(opacity)))
        self.update()

    def set_mask_alpha(self, alpha: int) -> None:
        self._mask_alpha = max(0, min(255, int(alpha)))
        self.update()

    def set_theme(self, theme: str) -> None:
        self._theme = "dark" if theme == "dark" else "light"
        self.update()

    # -- 缩放过渡（窗口大小变化时图片平滑缩放）-------------------
    def get_zoom(self) -> float:
        return self._zoom

    def set_zoom(self, value: float) -> None:
        self._zoom = float(value)
        self.update()

    def animate_zoom(self, start: float, duration: int = 400, enabled: bool = True) -> None:
        from PySide6.QtCore import QPropertyAnimation  # 局部导入避免循环

        if self._zoom_anim is not None:
            self._zoom_anim.stop()
        if not enabled or duration <= 0:
            self.set_zoom(1.0)
            return
        anim = QPropertyAnimation(self, b"zoom", self)
        anim.setDuration(duration)
        anim.setStartValue(max(0.6, min(1.6, start)))
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        self._zoom_anim = anim

    zoom = Property(float, get_zoom, set_zoom)

    def set_offset_x_ratio(self, ratio: float) -> None:
        self._offset_x_ratio = max(-0.5, min(0.5, float(ratio)))
        self._recompute()
        self.update()

    # -- geometry ------------------------------------------------------
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # 拖拽中先复用缓存图（绘制时拉伸），停止 120ms 后再高质量重采样
        self._resample_timer.start()
        self.update()

    def _target_rect(self) -> QRect:
        """按显示模式与位置计算图片绘制区域（保持比例）。"""
        if self._source is None or self._source.isNull():
            return QRect()
        area = self.rect()
        if area.isEmpty():
            return QRect()
        src_w = max(1, self._source.width())
        src_h = max(1, self._source.height())
        ratio = src_w / src_h

        if self._mode == MODE_FILL:
            # 等比覆盖整个区域，允许裁切
            if area.width() / max(1, area.height()) > ratio:
                width = area.width()
                height = int(width / ratio)
            else:
                height = area.height()
                width = int(height * ratio)
            x = area.x() + (area.width() - width) // 2
            y = area.y() + (area.height() - height) // 2
            return QRect(x, y, width, height)

        if self._mode == MODE_RIGHT:
            # 右侧人物立绘：高度撑满，宽度等比，贴右下；
            # 宽度限制在 440px 内，避免覆盖左侧功能面板
            box_w = min(area.width(), 440)
            box_h = area.height()
        else:  # watermark
            box_w = int(area.width() * 0.70)
            box_h = int(area.height() * 0.86)

        if box_w <= 0 or box_h <= 0:
            return QRect()
        if box_w / box_h > ratio:
            height = box_h
            width = int(height * ratio)
        else:
            width = box_w
            height = int(width / ratio)

        if self._mode == MODE_RIGHT:
            # 立绘贴右下角，可按页面宽度比例整体右移
            x = area.right() - width + 1 + int(area.width() * self._offset_x_ratio)
            y = area.bottom() - height + 1
            return QRect(x, y, width, height)
        if self._position == POSITION_LEFT:
            x = area.x()
        elif self._position == POSITION_CENTER:
            x = area.x() + (area.width() - width) // 2
        else:
            x = area.right() - width + 1
        y = area.y() + (area.height() - height) // 2
        return QRect(x, y, width, height)

    def _recompute(self) -> None:
        if self._source is None or self._source.isNull():
            self._scaled = None
            return
        target = self._target_rect()
        if target.isEmpty():
            self._scaled = None
            return
        # 按设备像素比缩放：高 DPI（125%/150% 缩放）下保持锐利，
        # 避免逻辑像素再次被系统拉伸导致发虚。只缩放一次并缓存。
        dpr = self.devicePixelRatioF()
        if dpr > 1.01:
            scaled = self._source.scaled(
                QSize(int(target.width() * dpr), int(target.height() * dpr)),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            scaled.setDevicePixelRatio(dpr)
            self._scaled = scaled
        else:
            self._scaled = self._source.scaled(
                QSize(target.width(), target.height()),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )

    # -- painting ------------------------------------------------------
    def paintEvent(self, event) -> None:
        # 无图片时完全透明；底色与遮罩由 BackgroundColorLayer 负责
        if self._source is None or self._source.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setOpacity(self._opacity)
        target = self._target_rect()
        if not target.isEmpty() and self._scaled is not None and not self._scaled.isNull():
            if abs(self._zoom - 1.0) > 0.001:
                anchor_x = target.right()
                anchor_y = target.bottom()
                painter.translate(anchor_x, anchor_y)
                painter.scale(self._zoom, self._zoom)
                painter.translate(-anchor_x, -anchor_y)
            painter.drawPixmap(target, self._scaled)
        painter.setOpacity(1.0)


class BackgroundManager(QObject):
    """页面背景的加载、缓存与切换。"""

    background_changed = Signal(str)

    def __init__(self, page_host: QWidget, page_surface: QWidget,
                 theme: str = "light", parent=None) -> None:
        super().__init__(parent)
        self.logger = setup_logger()
        self.page_host = page_host
        self.page_surface = page_surface
        self.theme = theme
        self._cache: dict[str, QPixmap | None] = {}
        self._current_key = ""
        self._opacity_scale = 1.0
        self._mode_override = ""
        self._position_override = ""
        self.enabled = True
        self.animations_enabled = True
        self.animation_scale = 1.0
        self.fade_duration = 400

        self.color_layer = BackgroundColorLayer(page_host)
        self.layer = BackgroundLayer(page_host)          # 当前背景（淡出）
        self.fade_layer = BackgroundLayer(page_host)     # 新背景（淡入）
        layout = page_host.layout()
        if not isinstance(layout, QGridLayout):
            layout = QGridLayout(page_host)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
        self._host_width = max(1, page_host.width())
        layout.addWidget(self.color_layer, 0, 0)
        layout.addWidget(self.layer, 0, 0)
        layout.addWidget(self.fade_layer, 0, 0)
        layout.addWidget(page_surface, 0, 0)
        page_surface.raise_()
        self.fade_layer.lower()
        self.layer.lower()
        self.color_layer.lower()

        # 交叉淡入淡出：基础层淡出（1→0）与新层淡入（0→1）同时进行
        self._fade_out_anim = QVariantAnimation(self)
        self._fade_out_anim.setStartValue(1.0)
        self._fade_out_anim.setEndValue(0.0)
        self._fade_out_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_out_anim.valueChanged.connect(self._on_fade_out_value)

        self._fade_anim = QVariantAnimation(self)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim.valueChanged.connect(self._on_fade_value)
        self._fade_anim.finished.connect(self._on_fade_finished)

    # -- public API ----------------------------------------------------
    def set_background(self, page_key: str, animate: bool = True) -> bool:
        """切换到指定页面的背景；返回是否显示了真实图片。

        animate=True 且动画开启时使用交叉淡入淡出：
        基础层保持旧画面，淡入层显示新画面并渐显，
        结束后把新画面转正到基础层。
        """
        self._current_key = page_key or ""
        if not self.enabled:
            self._stop_fade()
            self.layer.set_source(None)
            self.fade_layer.set_source(None)
            return False
        spec = self.get_background_config(page_key)
        if spec is None:
            self._stop_fade()
            self.clear_background()
            return False
        pixmap = self._load_pixmap(spec)
        animate_now = animate and self.animations_enabled and self.animation_scale > 0
        if animate_now:
            duration = max(1, int(self.fade_duration * self.animation_scale))
            self._start_crossfade(spec, pixmap, duration)
        else:
            self._stop_fade()
            self._adopt_on_base(spec, pixmap)
        self.background_changed.emit(page_key)
        return pixmap is not None

    def _adopt_on_base(self, spec: "BackgroundSpec", pixmap) -> None:
        self.layer.set_theme(self.theme)
        self.layer.set_mode(self._mode_override or spec.mode)
        self.layer.set_position(self._position_override or spec.position)
        self.layer.set_opacity(spec.opacity * self._opacity_scale)
        self.layer.set_mask_alpha(spec.mask_alpha)
        self.layer.set_offset_x_ratio(spec.offset_x_ratio)
        self.layer.set_source(pixmap)
        self.fade_layer.set_source(None)
        self.fade_layer.set_opacity(0)

    def _start_crossfade(self, spec: "BackgroundSpec", pixmap, duration: int) -> None:
        # 淡入层配置新背景；基础层保持旧画面与旧位置，仅透明度淡出
        self.fade_layer.set_theme(self.theme)
        self.fade_layer.set_mode(self._mode_override or spec.mode)
        self.fade_layer.set_position(self._position_override or spec.position)
        self.fade_layer.set_offset_x_ratio(spec.offset_x_ratio)
        self.fade_layer.set_source(pixmap)
        self.fade_layer.set_opacity(0.0)

        self.layer.set_offset_x_ratio(getattr(self, "_fade_out_from_offset", self.layer._offset_x_ratio))

        self._fade_out_anim.stop()
        self._fade_anim.stop()
        self._fade_out_anim.setDuration(duration)
        self._fade_anim.setDuration(duration)
        self._fade_out_anim.start()
        self._fade_anim.setEndValue(spec.opacity * self._opacity_scale)
        self._fade_anim.start()

    def _stop_fade(self) -> None:
        self._fade_out_anim.stop()
        self._fade_anim.stop()
        self.fade_layer.set_source(None)
        self.fade_layer.set_opacity(0.0)

    def _on_fade_value(self, value: float) -> None:
        self.fade_layer.set_opacity(float(value))

    def _on_fade_out_value(self, value: float) -> None:
        self.layer.set_opacity(float(value))

    def _on_fade_finished(self) -> None:
        spec = self.get_background_config(self._current_key)
        if spec is None:
            self.layer.set_source(None)
            self.fade_layer.set_source(None)
            self.fade_layer.set_opacity(0.0)
            return
        # 新背景转正到基础层
        self.layer.set_theme(self.theme)
        self.layer.set_mode(self._mode_override or spec.mode)
        self.layer.set_position(self._position_override or spec.position)
        self.layer.set_offset_x_ratio(spec.offset_x_ratio)
        self.layer.set_opacity(spec.opacity * self._opacity_scale)
        self.layer.set_source(self.fade_layer._source)
        self.fade_layer.set_source(None)
        self.fade_layer.set_opacity(0.0)

    def clear_background(self) -> None:
        self._current_key = ""
        self.layer.set_source(None)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        if not self.enabled:
            self.layer.set_source(None)
        elif self._current_key:
            self.set_background(self._current_key)

    def set_opacity(self, value: float) -> None:
        self._opacity_scale = max(0.0, min(1.0, float(value)))
        if self._current_key:
            self.set_background(self._current_key)

    def set_position(self, position: str) -> None:
        self._position_override = position if position in POSITIONS else ""
        if self._current_key:
            self.set_background(self._current_key)

    def set_display_mode(self, mode: str) -> None:
        self._mode_override = mode if mode in DISPLAY_MODES else ""
        if self._current_key:
            self.set_background(self._current_key)

    def on_host_resized(self, new_width: int) -> None:
        """窗口尺寸变化时驱动背景图缩放过渡（400ms）。

        拖拽缩放会连续触发该回调，这里做防抖：尺寸稳定 160ms 后才播放一次，
        避免动画被反复重启造成背景"抖动"。
        """
        if not hasattr(self, "_resize_timer"):
            self._resize_timer = QTimer(self)
            self._resize_timer.setSingleShot(True)
            self._resize_timer.setInterval(160)
            self._resize_timer.timeout.connect(self._play_resize_zoom)
        self._host_width_new = max(1, int(new_width))
        self._resize_timer.start()

    def _play_resize_zoom(self) -> None:
        old_width = getattr(self, "_host_width", 0)
        new_width = getattr(self, "_host_width_new", 0)
        self._host_width = new_width
        if not self.animations_enabled or old_width <= 0 or new_width <= 0:
            return
        ratio = old_width / float(new_width)
        if 0.6 <= ratio <= 1.6 and abs(ratio - 1.0) > 0.01:
            for layer in (self.layer, self.fade_layer):
                layer.animate_zoom(ratio, duration=400, enabled=True)

    def set_animations_enabled(self, enabled: bool) -> None:
        """同步动画开关到各绘制层（关闭后缩放立即生效，无过渡）。"""
        self.animations_enabled = bool(enabled)
        for layer in (self.layer, self.fade_layer):
            layer._animations_enabled = self.animations_enabled

    def set_theme(self, theme: str) -> None:
        self.theme = "dark" if theme == "dark" else "light"
        self.color_layer.set_theme(self.theme)
        self.layer.set_theme(self.theme)
        self.fade_layer.set_theme(self.theme)

    def stop_animations(self) -> None:
        """停止所有背景动画（窗口关闭时调用，避免析构阶段回调）。"""
        try:
            self._fade_anim.stop()
            self._fade_out_anim.stop()
        except Exception:
            pass

    def reload_backgrounds(self) -> None:
        self._cache.clear()
        if self._current_key:
            self.set_background(self._current_key)

    def get_background_config(self, page_key: str) -> BackgroundSpec | None:
        return BACKGROUND_SPECS.get(page_key or "")

    def background_path(self, page_key: str) -> Path | None:
        spec = self.get_background_config(page_key)
        if spec is None:
            return None
        return resource_path(spec.relative_path)

    def is_showing_image(self) -> bool:
        return self.layer._source is not None and not self.layer._source.isNull()

    @property
    def current_key(self) -> str:
        return self._current_key

    # -- internals -----------------------------------------------------
    def _load_pixmap(self, spec: BackgroundSpec) -> QPixmap | None:
        path = resource_path(spec.relative_path)
        cache_key = str(path)
        if cache_key in self._cache:
            return self._cache[cache_key]

        pixmap: QPixmap | None = None
        try:
            if not path.is_file():
                pixmap = None
            else:
                reader = QImageReader(str(path))
                reader.setAutoTransform(True)
                size = reader.size()
                if size.isValid() and size.width() > MAX_DECODE_EDGE:
                    scale = MAX_DECODE_EDGE / size.width()
                    reader.setScaledSize(QSize(MAX_DECODE_EDGE, max(1, int(size.height() * scale))))
                image = reader.read()
                if image.isNull():
                    self.logger.warning("背景图片无法解码：%s", path)
                    pixmap = None
                else:
                    pixmap = QPixmap.fromImage(image)
        except Exception as error:  # 资源缺失/损坏都不应影响启动
            self.logger.warning("背景图片加载失败：%s (%s)", path, error)
            pixmap = None

        self._cache[cache_key] = pixmap
        return pixmap
