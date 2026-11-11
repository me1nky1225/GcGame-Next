"""开关控件：QCheckBox 的指示器要贴图片才能显示对勾，干脆自己画。"""
from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget

from ...theme.tokens import Tokens


class Switch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, tokens: Tokens, checked: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._tokens = tokens
        self._on = checked
        self.setFixedSize(38, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    # ---- 状态 ----
    def isChecked(self) -> bool:  # noqa: N802
        return self._on

    def setChecked(self, value: bool, emit: bool = False) -> None:  # noqa: N802
        value = bool(value)
        if value == self._on:
            return
        self._on = value
        self.update()
        if emit:
            self.toggled.emit(value)

    def set_tokens(self, tokens: Tokens) -> None:
        self._tokens = tokens
        self.update()

    # ---- 交互 ----
    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._on, emit=True)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        t = self._tokens
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        h = self.height()
        track = QRectF(0, 1, self.width(), h - 2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(t.accent if self._on else t.line_strong))
        p.drawRoundedRect(track, track.height() / 2, track.height() / 2)

        d = h - 6
        x = self.width() - d - 3 if self._on else 3
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QRectF(x, 3, d, d))
