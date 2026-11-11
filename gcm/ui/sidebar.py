"""左侧导航栏。"""
from __future__ import annotations

from PyQt6.QtCore import QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..i18n import t
from ..theme.tokens import Tokens
from .icons import pixmap

NAV_ITEMS = [
    ("library", "我的修改器", "grid"),
    ("discover", "发现", "compass"),
    ("downloads", "下载队列", "download"),
    ("settings", "设置", "settings"),
]


class Logo(QWidget):
    def __init__(self, tokens: Tokens, parent=None) -> None:
        super().__init__(parent)
        self.tokens = tokens
        self.setFixedSize(30, 30)

    def set_tokens(self, tokens: Tokens) -> None:
        self.tokens = tokens
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect())
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor("#4f8cff"))
        grad.setColorAt(1.0, QColor("#1d4ed8"))
        path = QPainterPath()
        path.addRoundedRect(rect, 9, 9)
        p.fillPath(path, grad)
        f = QFont(self.tokens.font_family)
        f.setPixelSize(12)
        f.setWeight(QFont.Weight.Black)
        p.setFont(f)
        p.setPen(QColor("#ffffff"))
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "GC")


def _two_state_icon(name: str, tokens: Tokens) -> QIcon:
    ic = QIcon()
    normal: QPixmap = pixmap(name, tokens.muted, 17)
    active: QPixmap = pixmap(name, tokens.accent, 17)
    ic.addPixmap(normal, QIcon.Mode.Normal, QIcon.State.Off)
    ic.addPixmap(active, QIcon.Mode.Normal, QIcon.State.On)
    return ic


class NavButton(QPushButton):
    def __init__(self, text: str, icon_name: str, tokens: Tokens, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("NavButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(36)
        self.setIconSize(QSize(17, 17))
        self._icon_name = icon_name
        self.set_tokens(tokens)

        self._count = QLabel("", self)
        self._count.setObjectName("Kbd")
        self._count.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._count.hide()

    def set_count(self, value: int) -> None:
        self._count.setText(str(value))
        self._count.setVisible(value > 0)
        self._count.adjustSize()
        self._place_count()

    def _place_count(self) -> None:
        self._count.move(
            self.width() - self._count.width() - 8,
            (self.height() - self._count.height()) // 2,
        )

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._place_count()

    def set_tokens(self, tokens: Tokens) -> None:
        self.setIcon(_two_state_icon(self._icon_name, tokens))


class Sidebar(QWidget):
    navigate = pyqtSignal(int)

    def __init__(self, tokens: Tokens, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Rail")
        self.setFixedWidth(208)
        self.tokens = tokens

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 16, 12, 16)
        root.setSpacing(2)

        brand = QHBoxLayout()
        brand.setContentsMargins(6, 4, 6, 18)
        brand.setSpacing(10)
        self.logo = Logo(tokens)
        brand.addWidget(self.logo)
        text_box = QVBoxLayout()
        text_box.setSpacing(0)
        self.brand_name = QLabel("Game Cheats")
        self.brand_name.setStyleSheet("font-weight: 700; font-size: 14px;")
        self.brand_sub = QLabel(t("修改器管理器"))
        self.brand_sub.setObjectName("Subtle")
        self.brand_sub.setStyleSheet("font-size: 11px;")
        text_box.addWidget(self.brand_name)
        text_box.addWidget(self.brand_sub)
        brand.addLayout(text_box)
        brand.addStretch(1)
        root.addLayout(brand)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: list[NavButton] = []
        for i, (_key, text, icon_name) in enumerate(NAV_ITEMS):
            btn = NavButton(t(text), icon_name, tokens)
            self.group.addButton(btn, i)
            root.addWidget(btn)
            self.buttons.append(btn)
            if i == 2:
                sep = QLabel(t("管理"))
                sep.setObjectName("SectionLabel")
                sep.setStyleSheet("padding: 14px 0 6px 10px;")
                root.addWidget(sep)
        self.group.idClicked.connect(self.navigate)
        self.buttons[0].setChecked(True)

        root.addStretch(1)

        footer = QVBoxLayout()
        footer.setContentsMargins(6, 12, 6, 0)
        footer.setSpacing(6)
        self.sources = QLabel("")
        self.sources.setObjectName("Subtle")
        self.sources.setTextFormat(Qt.TextFormat.RichText)
        self.sources.setWordWrap(True)
        self.db_line = QLabel(t("数据库未加载"))
        self.db_line.setObjectName("Subtle")
        footer.addWidget(self.sources)
        footer.addWidget(self.db_line)
        root.addLayout(footer)

        self.set_tokens(tokens)

    def set_tokens(self, tokens: Tokens) -> None:
        self.tokens = tokens
        self.logo.set_tokens(tokens)
        for btn in self.buttons:
            btn.set_tokens(tokens)
        dot = tokens.ok
        muted = tokens.muted
        self.sources.setText(
            f'<span style="color:{dot}">●</span> GCM&nbsp;·&nbsp;'
            f'<span style="color:{dot}">●</span> FLiNG<br/>'
            f'<span style="color:{dot}">●</span> {t("小幸")}&nbsp;·&nbsp;'
            f'<span style="color:{muted}">●</span> CT'
        )

    def set_counts(self, library: int, downloads: int) -> None:
        self.buttons[0].set_count(library)
        self.buttons[2].set_count(downloads)

    def set_db_info(self, text: str) -> None:
        self.db_line.setText(text)

    def select(self, index: int) -> None:
        self.buttons[index].setChecked(True)
