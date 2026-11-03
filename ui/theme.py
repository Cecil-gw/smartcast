from __future__ import annotations

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
QFrame#ConfigCard, QFrame#StatCard, QFrame#ActionCard, QFrame#DeviceCard {{
    background: {COLORS['card']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
}}
QFrame#QuickPanel {{ background: transparent; border: none; }}
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
QPushButton#NavButton {{
    background: transparent;
    color: {COLORS['muted']};
    border: 1px solid transparent;
    border-radius: 9px;
    min-height: 42px;
    padding: 0 12px;
    text-align: left;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#NavButton:hover {{ background: #E5EDE7; color: {COLORS['text']}; }}
QPushButton#NavButton[active="true"] {{
    background: {COLORS['accent_soft']};
    color: #3F6555;
    border: 1px solid #D4E3D9;
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
    background: #F9FBF9;
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


