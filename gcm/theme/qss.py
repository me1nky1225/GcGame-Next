"""由 Tokens 生成全局 QSS。占位符用 `{key}`，靠字符串替换填充（避免 QSS 大括号转义地狱）。"""
from __future__ import annotations

from dataclasses import asdict

from .tokens import Tokens

_TEMPLATE = """
* {{
    font-family: "{font_family}";
    font-size: 13px;
    outline: none;
}}

QWidget {{
    color: {fg};
}}

QMainWindow, #MainSurface {{
    background: {bg};
}}

#Rail {{
    background: {rail};
    border-right: 1px solid {line};
}}

#TopBar {{
    background: {bg};
    border-bottom: 1px solid {line};
}}

#ContentArea {{
    background: {bg};
}}

#DetailPanel {{
    background: {rail};
    border-left: 1px solid {line};
}}

#QueueBar {{
    background: {rail};
    border-top: 1px solid {line};
}}

#Toast {{
    background: {card};
    border: 1px solid {line_strong};
    border-radius: 10px;
}}

QLabel#ToastDot {{
    font-size: 12px;
}}

QLabel {{
    background: transparent;
    color: {fg};
}}

QLabel#H1 {{
    font-size: 19px;
    font-weight: 700;
    color: {fg};
}}

QLabel#H2 {{
    font-size: 15px;
    font-weight: 700;
    color: {fg};
}}

QLabel#DangerHint {{
    color: {danger};
    font-size: 12px;
}}

QLabel#Subtle {{
    color: {muted};
    font-size: 12px;
}}

QLabel#FieldLabel {{
    color: {muted};
    font-size: 12px;
}}

QLabel#SectionLabel {{
    color: {muted};
    font-size: 11px;
    letter-spacing: 1px;
}}

QLabel#Value {{
    color: {fg2};
    font-size: 13px;
}}

QLineEdit {{
    background: {card};
    color: {fg};
    border: 1px solid {line};
    border-radius: {radius_s}px;
    padding: 7px 10px;
    selection-background-color: {accent};
    selection-color: {on_accent};
}}

QLineEdit:hover {{
    border-color: {line_strong};
}}

QLineEdit:focus {{
    border-color: {accent};
}}

QLineEdit#SearchField {{
    padding-left: 34px;
    padding-right: 60px;
    border-radius: 10px;
    font-size: 13px;
}}

QLineEdit#PathField {{
    font-family: "{font_mono}", Consolas, monospace;
    font-size: 12px;
    color: {muted};
    background: {card};
}}

QLineEdit#FlatField {{
    background: {card_hover};
    border: 1px solid transparent;
    border-radius: {radius_s}px;
    padding: 6px 10px;
    color: {fg2};
}}

QComboBox {{
    background: {card};
    color: {fg};
    border: 1px solid {line};
    border-radius: {radius_s}px;
    padding: 6px 10px;
    min-height: 20px;
}}

QComboBox:hover {{
    border-color: {line_strong};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background: {card};
    color: {fg};
    border: 1px solid {line};
    border-radius: {radius_s}px;
    padding: 4px;
    selection-background-color: {accent_soft};
    selection-color: {fg};
    outline: none;
}}

QPushButton {{
    background: {card};
    color: {fg2};
    border: 1px solid {line};
    border-radius: {radius_s}px;
    padding: 7px 14px;
}}

QPushButton:hover {{
    background: {card_hover};
    border-color: {line_strong};
    color: {fg};
}}

QPushButton:pressed {{
    background: {card_press};
}}

QPushButton:disabled {{
    color: {muted};
    border-color: {line};
}}

QPushButton#SortBtn {{
    background: {card};
    border: 1px solid {line};
    border-radius: {radius_s}px;
    color: {fg2};
    padding: 6px 10px 6px 12px;
    font-size: 12px;
}}

QPushButton#SortBtn:hover {{
    background: {card_hover};
    border-color: {line_strong};
    color: {fg};
}}

QPushButton#SortBtn::menu-indicator {{
    image: none;
    width: 0;
}}

QPushButton#Primary {{
    background: {accent};
    color: {on_accent};
    border: 1px solid {accent};
    font-weight: 600;
}}

QPushButton#Primary:hover {{
    background: {accent_hover};
    border-color: {accent_hover};
}}

QPushButton#Primary:pressed {{
    background: {accent_press};
    border-color: {accent_press};
}}

QPushButton#Danger {{
    color: {danger};
    border: 1px solid {line};
    background: transparent;
}}

QPushButton#Danger:hover {{
    background: {danger_soft};
    border-color: {danger};
}}

QPushButton#Ghost {{
    background: transparent;
    border: 1px solid transparent;
    color: {muted};
    padding: 7px 6px;
}}

QPushButton#Ghost:hover {{
    background: {card_hover};
    color: {fg};
    border-color: transparent;
}}

QPushButton#IconButton {{
    background: {card};
    border: 1px solid {line};
    border-radius: {radius_s}px;
    padding: 0;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
}}

QPushButton#IconButton:hover {{
    background: {card_hover};
    border-color: {line_strong};
}}

QPushButton#NavButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: {radius_s}px;
    padding: 8px 40px 8px 10px;
    text-align: left;
    color: {fg2};
    font-size: 13px;
}}

QPushButton#NavButton:hover {{
    background: {card};
    color: {fg};
}}

QPushButton#NavButton:checked {{
    background: {accent_soft};
    color: {accent};
    font-weight: 600;
    border-color: transparent;
}}

QPushButton#Chip {{
    background: {card};
    border: 1px solid {line};
    border-radius: 13px;
    padding: 4px 12px;
    color: {fg2};
    font-size: 12px;
}}

QPushButton#Chip:hover {{
    border-color: {line_strong};
    color: {fg};
}}

QPushButton#Chip:checked {{
    background: {accent_soft};
    border-color: {accent};
    color: {accent};
    font-weight: 600;
}}

QPushButton#SegLeft, QPushButton#SegRight {{
    background: {card};
    border: 1px solid {line};
    color: {fg2};
    padding: 6px 14px;
}}

QPushButton#SegLeft {{
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
}}

QPushButton#SegRight {{
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
    border-left: none;
}}

QPushButton#SegLeft:checked, QPushButton#SegRight:checked {{
    background: {accent_soft};
    color: {accent};
    border-color: {accent};
    font-weight: 600;
}}

QListView {{
    background: transparent;
    border: none;
    outline: none;
}}

QListView::item {{
    background: transparent;
}}

QScrollArea {{
    background: {bg};
    border: none;
}}

/* 滚动区里的内容容器：显式上色，否则切主题后这块会留着旧底色 */
QScrollArea > QWidget > QWidget {{
    background: {bg};
}}

QStackedWidget {{
    background: {bg};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px 2px 2px 0;
}}

QScrollBar::handle:vertical {{
    background: {line_strong};
    border-radius: 3px;
    min-height: 32px;
}}

QScrollBar::handle:vertical:hover {{
    background: {muted};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0 2px 2px 2px;
}}

QScrollBar::handle:horizontal {{
    background: {line_strong};
    border-radius: 3px;
    min-width: 32px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

QProgressBar {{
    background: {card_hover};
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    background: {accent};
    border-radius: 3px;
}}

QMenu {{
    background: {card};
    border: 1px solid {line_strong};
    border-radius: {radius_s}px;
    padding: 5px;
}}

QMenu::item {{
    padding: 7px 26px 7px 12px;
    border-radius: 6px;
    color: {fg2};
}}

QMenu::item:selected {{
    background: {accent_soft};
    color: {fg};
}}

QMenu::item:disabled {{
    color: {muted};
}}

QMenu::separator {{
    height: 1px;
    background: {line};
    margin: 5px 8px;
}}

QToolTip {{
    background: {card};
    color: {fg};
    border: 1px solid {line_strong};
    border-radius: 6px;
    padding: 5px 8px;
}}

QLabel#PathBox {{
    background: {card};
    border: 1px solid {line};
    border-radius: 9px;
    padding: 8px 10px;
    color: {muted};
    font-family: "{font_mono}", Consolas, monospace;
    font-size: 11px;
}}

QLabel#Kbd {{
    color: {muted};
    background: {card_hover};
    border: 1px solid {line_strong};
    border-radius: 5px;
    padding: 2px 6px;
    font-size: 11px;
}}

QLabel#EmptyTitle {{
    color: {fg2};
    font-size: 14px;
    font-weight: 600;
}}

QLabel#EmptyHint {{
    color: {muted};
    font-size: 12px;
}}

QLabel#OnlineTag {{
    color: {accent};
    font-size: 12px;
}}

QFrame#Card {{
    background: {card};
    border: 1px solid {line};
    border-radius: {radius_m}px;
}}

QFrame#Divider {{
    background: {line};
    max-height: 1px;
    min-height: 1px;
    border: none;
}}

QCheckBox {{
    color: {fg2};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 5px;
    border: 1px solid {line_strong};
    background: {card};
}}

QCheckBox::indicator:hover {{
    border-color: {accent};
}}

QCheckBox::indicator:checked {{
    background: {accent};
    border-color: {accent};
}}
"""


def build_qss(tokens: Tokens) -> str:
    qss = _TEMPLATE
    for key, value in asdict(tokens).items():
        if key in ("badges", "name"):
            continue
        qss = qss.replace("{%s}" % key, str(value))
    # 模板里用 {{ }} 表示字面大括号，这里统一还原
    return qss.replace("{{", "{").replace("}}", "}")
