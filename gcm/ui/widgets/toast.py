"""轻量提示条：右下角浮层，4 秒自动消失，不打断操作。"""
from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget


class Toast(QFrame):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(10)
        self.dot = QLabel("●")
        self.dot.setObjectName("ToastDot")
        self.text = QLabel("")
        lay.addWidget(self.dot)
        lay.addWidget(self.text)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self.hide()

    def show_message(self, message: str, kind: str = "info", msec: int = 4000) -> None:
        colors = {"info": "#3b82f6", "ok": "#22c55e", "warn": "#f59e0b", "error": "#ef4444"}
        self.dot.setStyleSheet(f"color: {colors.get(kind, colors['info'])};")
        self.text.setText(message)
        self.adjustSize()
        self._place()
        self.show()
        self.raise_()
        self._timer.start(msec)

    def _place(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        margin = 24
        x = max(margin, (parent.width() - self.width()) // 2)
        y = parent.height() - self.height() - 60
        self.move(x, y)
