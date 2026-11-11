"""「下载队列」页。"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...context import AppContext
from ...i18n import t as tr
from ...theme.tokens import Tokens
from ...util import initials
from .library import make_empty, make_header


class _Tile(QWidget):
    """34x34 渐变方块，给下载行一点视觉锚点。"""

    def __init__(self, tokens: Tokens, text: str, parent=None) -> None:
        super().__init__(parent)
        self._tokens = tokens
        self._text = text
        self.setFixedSize(34, 34)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        c1, c2 = self._tokens.cover(self._text)
        grad = QLinearGradient(0, 0, 34, 34)
        grad.setColorAt(0.0, QColor(c1))
        grad.setColorAt(1.0, QColor(c2))
        p.setBrush(grad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), 10, 10)
        p.setPen(QColor("#ffffff"))
        font = p.font()
        font.setBold(True)
        font.setPointSizeF(10.0)
        p.setFont(font)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, initials(self._text))


class DownloadRow(QFrame):
    def __init__(self, tokens: Tokens, queue, task, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.task = task
        self._queue = queue

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)

        self.tile = _Tile(tokens, task.name)
        lay.addWidget(self.tile)

        col = QVBoxLayout()
        col.setSpacing(6)
        top = QHBoxLayout()
        top.setSpacing(8)
        self.name = QLabel(task.name)
        self.name.setStyleSheet("font-weight: 600;")
        top.addWidget(self.name)
        self.source = QLabel(task.source)
        self.source.setObjectName("Subtle")
        top.addWidget(self.source)
        top.addStretch(1)
        self.pct = QLabel("0%")
        self.pct.setObjectName("Subtle")
        top.addWidget(self.pct)
        col.addLayout(top)

        line = QHBoxLayout()
        line.setSpacing(10)
        self.bar = QProgressBar()
        self.bar.setFixedHeight(6)
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        self.bar.setMaximumWidth(320)
        self.bar.setMinimumWidth(200)
        line.addWidget(self.bar)
        self.status = QLabel("")
        self.status.setObjectName("Subtle")
        # Ignored：允许比 sizeHint 更窄，否则英文长句会把右侧按钮挤出卡片
        self.status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.status.setMinimumWidth(0)
        line.addWidget(self.status, 1)
        line.addStretch(0)
        col.addLayout(line)
        lay.addLayout(col, 1)

        self.pause_btn = QPushButton(tr("暂停"))
        self.pause_btn.setObjectName("Ghost")
        self.pause_btn.setFixedSize(68, 28)
        self.pause_btn.clicked.connect(self._primary)
        lay.addWidget(self.pause_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self.remove_btn = QPushButton(tr("移除"))
        self.remove_btn.setObjectName("Ghost")
        self.remove_btn.setFixedSize(68, 28)
        self.remove_btn.clicked.connect(lambda: queue.remove(self.task))
        lay.addWidget(self.remove_btn, 0, Qt.AlignmentFlag.AlignVCenter)

    def _primary(self) -> None:
        task = self.task
        if task.status == "failed":
            self._queue.retry(task)
        elif task.status in ("downloading", "paused"):
            self._queue.toggle_pause(task)

    def set_tokens(self, tokens: Tokens) -> None:
        self.tile._tokens = tokens
        self.tile.update()

    def sync(self) -> None:
        t = self.task
        self.bar.setValue(t.progress)
        self.pct.setText(f"{t.progress}%")
        state = t.status
        self.status.setStyleSheet("color: #ef4444;" if state == "failed" else "")
        if state == "queued":
            self.status.setText(tr("排队中"))
            self.pause_btn.setText(tr("暂停"))
            self.pause_btn.setEnabled(False)
        elif state == "paused":
            size = f"{t.done_mb:.1f} / {t.total_mb:.1f} MB" if t.total_mb else f"{t.done_mb:.1f} MB"
            self.status.setText(tr("已暂停 · {size}").format(size=size))
            self.pause_btn.setText(tr("继续"))
            self.pause_btn.setEnabled(True)
        elif state == "installing":
            self.status.setText(tr("解压并写入库目录…"))
            self.pause_btn.setText(tr("安装中"))
            self.pause_btn.setEnabled(False)
        elif state == "done":
            self.status.setText(
                tr("已完成 · {size} MB · 已加入「我的修改器」").format(size=f"{t.total_mb:.1f}")
            )
            self.pause_btn.setText(tr("完成"))
            self.pause_btn.setEnabled(False)
        elif state == "failed":
            self.status.setText(t.error or tr("下载失败"))
            self.pause_btn.setText(tr("重试"))
            self.pause_btn.setEnabled(True)
        else:
            speed = f"{t.speed:.1f} MB/s" if t.speed > 0.01 else tr("连接中…")
            size = f"{t.done_mb:.1f} / {t.total_mb:.1f} MB" if t.total_mb else ""
            eta = f" · {t.eta}" if t.eta else ""
            self.status.setText(" · ".join(x for x in (t.stage, size, speed + eta) if x))
            self.pause_btn.setText(tr("暂停"))
            self.pause_btn.setEnabled(True)


class DownloadsPage(QWidget):
    def __init__(self, ctx: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self._rows: dict[int, DownloadRow] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 12)
        root.setSpacing(14)

        head, self._subtitle = make_header(tr("下载队列"), tr("后台下载与解压进度"))
        row = QHBoxLayout()
        row.addWidget(head)
        row.addStretch(1)
        self.clear_btn = QPushButton(tr("清除已完成"))
        self.clear_btn.setObjectName("Ghost")
        self.clear_btn.clicked.connect(ctx.queue.clear_finished)
        row.addWidget(self.clear_btn, 0, Qt.AlignmentFlag.AlignBottom)
        root.addLayout(row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        holder = QWidget()
        holder.setMaximumWidth(920)
        self.list_lay = QVBoxLayout(holder)
        self.list_lay.setContentsMargins(0, 0, 0, 0)
        self.list_lay.setSpacing(8)
        self.list_lay.addStretch(1)
        self.scroll.setWidget(holder)

        empty, _ = make_empty(
            ctx.tokens, tr("队列是空的"), tr("在「发现」里点「获取」，下载任务会出现在这里")
        )
        self.empty = empty

        root.addWidget(self.scroll, 1)
        root.addWidget(self.empty)
        self.empty.hide()

        ctx.queue.updated.connect(self._sync)
        self._sync()

    def _sync(self) -> None:
        tasks = list(self.ctx.queue.tasks)
        alive = {t.tid for t in tasks}
        for tid in list(self._rows):
            if tid not in alive:
                w = self._rows.pop(tid)
                self.list_lay.removeWidget(w)
                w.deleteLater()

        for task in tasks:
            row = self._rows.get(task.tid)
            if row is None:
                row = DownloadRow(self.ctx.tokens, self.ctx.queue, task)
                self._rows[task.tid] = row
                self.list_lay.insertWidget(self.list_lay.count() - 1, row)
            row.task = task
            row.sync()

        has = bool(self._rows)
        self.scroll.setVisible(has)
        self.empty.setVisible(not has)
        pending = [t for t in tasks if t.status != "done"]
        if tasks:
            self._subtitle.setText(
                tr("{n} 个任务 · {m} 个进行中").format(n=len(tasks), m=len(pending))
            )
        else:
            self._subtitle.setText(tr("后台下载与解压进度"))

    def set_tokens(self, tokens: Tokens) -> None:
        for row in self._rows.values():
            row.set_tokens(tokens)
