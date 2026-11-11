"""顶栏：搜索 + 主题切换 + 导入。"""
from __future__ import annotations

from PyQt6.QtCore import QSize, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton

from ..i18n import t
from ..theme.tokens import Tokens
from .icons import icon
from .widgets.search_field import SearchField


class TopBar(QFrame):
    navToggled = pyqtSignal()
    detailToggled = pyqtSignal()
    searchChanged = pyqtSignal(str)
    themeToggled = pyqtSignal()
    importRequested = pyqtSignal()
    refreshRequested = pyqtSignal()

    def __init__(self, tokens: Tokens, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TopBar")
        self.setFixedHeight(60)
        self.tokens = tokens

        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(10)

        self.nav_btn = QPushButton()
        self.nav_btn.setObjectName("IconButton")
        self.nav_btn.setFixedSize(34, 34)
        self.nav_btn.setIconSize(QSize(16, 16))
        self.nav_btn.clicked.connect(self.navToggled.emit)
        lay.addWidget(self.nav_btn)

        self.search = SearchField(tokens, t("搜索游戏或修改器"))
        self.search.textChanged.connect(self.searchChanged.emit)
        lay.addWidget(self.search)
        lay.addStretch(1)

        self.detail_btn = QPushButton()
        self.detail_btn.setObjectName("IconButton")
        self.detail_btn.setFixedSize(34, 34)
        self.detail_btn.setIconSize(QSize(16, 16))
        self.detail_btn.clicked.connect(self.detailToggled.emit)
        lay.addWidget(self.detail_btn)

        self.refresh_btn = QPushButton()
        self.refresh_btn.setObjectName("IconButton")
        self.refresh_btn.setFixedSize(34, 34)
        self.refresh_btn.setIconSize(QSize(16, 16))
        self.refresh_btn.setToolTip(t("刷新列表（F5）"))
        self.refresh_btn.clicked.connect(self.refreshRequested.emit)
        lay.addWidget(self.refresh_btn)

        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("IconButton")
        self.theme_btn.setFixedSize(34, 34)
        self.theme_btn.setIconSize(QSize(16, 16))
        self.theme_btn.clicked.connect(self.themeToggled.emit)
        lay.addWidget(self.theme_btn)

        self.import_btn = QPushButton(t("导入修改器"))
        self.import_btn.setObjectName("Primary")
        self.import_btn.setMinimumHeight(34)
        self.import_btn.setIconSize(QSize(15, 15))
        self.import_btn.clicked.connect(self.importRequested.emit)
        lay.addWidget(self.import_btn)

        self.set_tokens(tokens)

    def set_sidebar_visible(self, visible: bool) -> None:
        """侧边栏收起时按钮变成「展开」，提示文案跟着换。"""
        self.nav_btn.setToolTip(t("隐藏侧边栏（Ctrl+B）") if visible else t("显示侧边栏（Ctrl+B）"))

    def set_detail_visible(self, visible: bool) -> None:
        self.detail_btn.setToolTip(
            t("隐藏详情面板（Ctrl+D）") if visible else t("显示详情面板（Ctrl+D）")
        )

    def set_tokens(self, tokens: Tokens) -> None:
        self.tokens = tokens
        self.nav_btn.setIcon(icon("sidebar", tokens.fg2, 16))
        self.detail_btn.setIcon(icon("panel_right", tokens.fg2, 16))
        self.search.set_tokens(tokens)
        self.refresh_btn.setIcon(icon("refresh", tokens.fg2, 16))
        is_dark = tokens.name == "dark"
        self.theme_btn.setIcon(icon("sun" if is_dark else "moon", tokens.fg2, 16))
        self.theme_btn.setToolTip(t("切换到浅色主题") if is_dark else t("切换到深色主题"))
        self.import_btn.setIcon(icon("plus", tokens.on_accent, 15))

    def set_search_text(self, text: str) -> None:
        self.search.blockSignals(True)
        self.search.setText(text)
        self.search.blockSignals(False)
