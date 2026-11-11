"""带图标的搜索框：左侧放大镜、右侧 Ctrl K 提示。"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QLineEdit

from ...theme.tokens import Tokens
from ..icons import icon


class SearchField(QLineEdit):
    def __init__(self, tokens: Tokens, placeholder: str = "搜索游戏或修改器", parent=None) -> None:
        super().__init__(parent)
        self.tokens = tokens
        self.setObjectName("SearchField")
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self.setMinimumHeight(36)
        self.setMaximumHeight(36)
        self.setMaximumWidth(520)
        self.setMinimumWidth(340)
        self._action = self.addAction(
            icon("search", tokens.muted, 16), QLineEdit.ActionPosition.LeadingPosition
        )

        self._kbd = QLabel("Ctrl K", self)
        self._kbd.setObjectName("Kbd")
        self._kbd.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._kbd.adjustSize()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._kbd.adjustSize()
        self._kbd.move(
            self.width() - self._kbd.width() - 10,
            (self.height() - self._kbd.height()) // 2,
        )

    def set_tokens(self, tokens: Tokens) -> None:
        self.tokens = tokens
        self._action.setIcon(icon("search", tokens.muted, 16))
