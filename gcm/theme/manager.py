"""主题管理器：切换即时生效，无需重启。"""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

from .qss import build_qss
from .tokens import THEMES, Tokens


class ThemeManager(QObject):
    changed = pyqtSignal(object)  # Tokens

    def __init__(self, app: QApplication, theme: str = "dark") -> None:
        super().__init__()
        self._app = app
        self._tokens: Tokens = THEMES.get(theme, THEMES["dark"])

    @property
    def tokens(self) -> Tokens:
        return self._tokens

    @property
    def name(self) -> str:
        return self._tokens.name

    def apply(self) -> None:
        t = self._tokens
        self._app.setStyleSheet(build_qss(t))

        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(t.bg))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(t.fg))
        palette.setColor(QPalette.ColorRole.Base, QColor(t.card))
        palette.setColor(QPalette.ColorRole.Text, QColor(t.fg))
        palette.setColor(QPalette.ColorRole.Button, QColor(t.card))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(t.fg))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(t.accent))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(t.on_accent))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(t.card))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(t.fg))
        self._app.setPalette(palette)
        self._repolish()

    def _repolish(self) -> None:
        """重建样式后逐个控件重刷：已存在的控件不会自动跟着换底色。"""
        palette = self._app.palette()
        for widget in self._app.allWidgets():
            try:
                widget.setPalette(palette)
                style = widget.style()
                style.unpolish(widget)
                style.polish(widget)
                widget.update()
            except RuntimeError:
                continue

    def set_theme(self, name: str) -> None:
        if name not in THEMES or name == self._tokens.name:
            return
        self._tokens = THEMES[name]
        self.apply()
        self.changed.emit(self._tokens)

    def toggle(self) -> None:
        self.set_theme("light" if self._tokens.name == "dark" else "dark")
