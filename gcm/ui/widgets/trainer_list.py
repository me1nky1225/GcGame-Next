"""列表核心：QAbstractListModel + 自绘 delegate + 支持胶囊按钮的 QListView。"""
from __future__ import annotations

import os

from PyQt6.QtCore import QAbstractListModel, QModelIndex, QPoint, QRect, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import QListView, QStyle, QStyledItemDelegate

from ...data.trainer import Trainer
from ...i18n import t as tr
from ...theme.tokens import Tokens
from ...util import humanize

TRAINER_ROLE = Qt.ItemDataRole.UserRole + 1
ROW_HEIGHT = 74
ROW_GAP = 6
PILL_W, PILL_H = 70, 28

_PIXMAPS: dict[tuple[str, float], QPixmap] = {}


def _cover_pixmap(path: str) -> QPixmap | None:
    """读封面并缓存；文件变了（mtime）就重读。"""
    try:
        stamp = os.path.getmtime(path)
    except OSError:
        return None
    key = (path, stamp)
    cached = _PIXMAPS.get(key)
    if cached is not None and not cached.isNull():
        return cached
    pix = QPixmap(path)
    if pix.isNull():
        return None
    _PIXMAPS[key] = pix
    return pix


def row_body(item_rect: QRect) -> QRect:
    return item_rect.adjusted(0, 0, 0, -ROW_GAP)


def pill_rect(item_rect: QRect) -> QRect:
    r = row_body(item_rect)
    return QRect(r.right() - 12 - PILL_W, r.center().y() - PILL_H // 2 + 1, PILL_W, PILL_H)


class TrainerModel(QAbstractListModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[Trainer] = []

    def set_items(self, items: list[Trainer]) -> None:
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()

    def items(self) -> list[Trainer]:
        return self._items

    def refresh(self) -> None:
        """数据被原地改了（补到中文名/封面）时重画可见行，不重置模型。"""
        if self._items:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self._items) - 1, 0))

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        trainer = self._items[index.row()]
        if role == TRAINER_ROLE:
            return trainer
        if role == Qt.ItemDataRole.DisplayRole:
            return trainer.title
        if role == Qt.ItemDataRole.ToolTipRole:
            return trainer.title if not trainer.name_zh else f"{trainer.title} · {trainer.name}"
        return None

    def trainer_at(self, row) -> Trainer | None:
        if isinstance(row, QModelIndex):
            row = row.row() if row.isValid() else -1
        if 0 <= row < len(self._items):
            return self._items[row]
        return None


class TrainerDelegate(QStyledItemDelegate):
    def __init__(self, tokens: Tokens, parent=None) -> None:
        super().__init__(parent)
        self.tokens = tokens
        # 页面注入：这一行还没有封面时该去找谁补（由 enricher 做去重）
        self.cover_needed = None

    def set_tokens(self, tokens: Tokens) -> None:
        self.tokens = tokens

    def sizeHint(self, option, index) -> QSize:  # noqa: N802
        return QSize(0, ROW_HEIGHT)

    # ---------- 绘制 ----------
    def paint(self, painter: QPainter, option, index: QModelIndex) -> None:
        trainer: Trainer = index.data(TRAINER_ROLE)
        if trainer is None:
            return
        t = self.tokens
        r = row_body(option.rect)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)

        body = QRectF(r).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(body, t.radius_m, t.radius_m)
        if selected:
            painter.fillPath(path, QColor(t.accent_soft))
            pen = QPen(QColor(t.accent))
            pen.setWidthF(1.2)
            painter.setPen(pen)
            painter.drawPath(path)
        elif hovered:
            painter.fillPath(path, QColor(t.card_hover))
            painter.setPen(QPen(QColor(t.line_strong), 1))
            painter.drawPath(path)
        else:
            painter.fillPath(path, QColor(t.card))
            painter.setPen(QPen(QColor(t.line), 1))
            painter.drawPath(path)

        # 封面块：有 Steam 封面就画图，否则退回渐变 + 首字母
        cover = QRectF(r.left() + 12, r.center().y() - 26, 52, 52)
        cp = QPainterPath()
        cp.addRoundedRect(cover, 10, 10)
        pix = _cover_pixmap(trainer.cover) if trainer.cover else None
        if pix is not None:
            painter.save()
            painter.setClipPath(cp)
            pw, ph = pix.width(), pix.height()
            side = min(pw, ph)
            src = QRectF((pw - side) / 2, 0, side, side)
            painter.drawPixmap(cover, pix, src)
            painter.restore()
        else:
            c1, c2 = t.cover(trainer.cover_key)
            grad = QLinearGradient(cover.topLeft(), cover.bottomRight())
            grad.setColorAt(0.0, QColor(c1))
            grad.setColorAt(1.0, QColor(c2))
            painter.fillPath(cp, grad)

            f = QFont(t.font_family)
            f.setPixelSize(14)
            f.setWeight(QFont.Weight.Bold)
            painter.setFont(f)
            painter.setPen(QColor("#ffffff"))
            painter.drawText(cover, Qt.AlignmentFlag.AlignCenter, trainer.initials)
            if self.cover_needed is not None and not trainer.appid:
                self.cover_needed(trainer)

        # 右侧：时间 + 胶囊
        pill = pill_rect(option.rect)
        time_text = humanize(trainer.updated) if trainer.installed else (
            f"{trainer.size_mb:.0f} MB" if trainer.size_mb else ""
        )
        if time_text:
            f = QFont(t.font_family)
            f.setPixelSize(11)
            painter.setFont(f)
            painter.setPen(QColor(t.muted))
            time_rect = QRect(pill.left() - 96, r.top(), 88, r.height())
            painter.drawText(
                time_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, time_text
            )

        pill_path = QPainterPath()
        pill_path.addRoundedRect(QRectF(pill).adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)
        if trainer.installed:
            painter.fillPath(pill_path, QColor(t.accent))
            fg = QColor("#ffffff")
            label = tr("启动")
        else:
            painter.fillPath(pill_path, QColor(t.accent_soft))
            pen = QPen(QColor(t.accent))
            pen.setWidthF(1.0)
            painter.setPen(pen)
            painter.drawPath(pill_path)
            fg = QColor(t.accent)
            label = tr("网页") if trainer.external else tr("获取")

        f = QFont(t.font_family)
        f.setPixelSize(12)
        f.setWeight(QFont.Weight.DemiBold)
        painter.setFont(f)
        painter.setPen(fg)
        painter.drawText(pill, Qt.AlignmentFlag.AlignCenter, label)

        # 标题 / 徽章 / 副标题
        text_left = int(cover.right()) + 12
        text_right = pill.left() - 104
        avail = max(80, text_right - text_left)

        f = QFont(t.font_family)
        f.setPixelSize(14)
        f.setWeight(QFont.Weight.DemiBold)
        painter.setFont(f)
        fm = QFontMetrics(f)

        badges = [trainer.source] + list(trainer.tags)
        bf = QFont(t.font_family)
        bf.setPixelSize(10)
        bf.setWeight(QFont.Weight.DemiBold)
        bfm = QFontMetrics(bf)
        badge_w = [bfm.horizontalAdvance(b) + 14 for b in badges]
        badge_total = sum(badge_w) + 6 * len(badge_w)

        title_max = max(60, avail - badge_total - 8)
        title = fm.elidedText(trainer.title, Qt.TextElideMode.ElideRight, title_max)
        title_w = fm.horizontalAdvance(title)
        painter.setPen(QColor(t.fg))
        painter.drawText(
            QRect(text_left, r.top() + 11, title_w + 2, 20),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title,
        )

        bx = text_left + title_w + 8
        for label, w in zip(badges, badge_w):
            if bx + w > text_right:
                break
            fg, bg, border = t.badge(label)
            brect = QRectF(bx, r.top() + 14, w, 17)
            bpath = QPainterPath()
            bpath.addRoundedRect(brect, 5, 5)
            painter.fillPath(bpath, QColor(bg))
            pen = QPen(QColor(border))
            pen.setWidthF(1)
            painter.setPen(pen)
            painter.drawPath(bpath)
            painter.setFont(bf)
            painter.setPen(QColor(fg))
            painter.drawText(brect, Qt.AlignmentFlag.AlignCenter, label)
            bx += w + 6

        f = QFont(t.font_family)
        f.setPixelSize(12)
        painter.setFont(f)
        painter.setPen(QColor(t.muted))
        sub_fm = QFontMetrics(f)
        sub = sub_fm.elidedText(trainer.subtitle(), Qt.TextElideMode.ElideRight, avail)
        painter.drawText(
            QRect(text_left, r.top() + 34, avail, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            sub,
        )

        painter.restore()


class TrainerListView(QListView):
    """点击右胶囊 = 启动/获取；双击 = 启动；右键 = 上下文菜单。"""

    pillClicked = pyqtSignal(object)
    activated_trainer = pyqtSignal(object)
    contextRequested = pyqtSignal(object, QPoint)

    def __init__(self, tokens: Tokens, parent=None) -> None:
        super().__init__(parent)
        self.tokens = tokens
        self.setMouseTracking(True)
        self.setUniformItemSizes(True)
        self.delegate = TrainerDelegate(tokens, self)
        self.setItemDelegate(self.delegate)
        self.setSelectionMode(QListView.SelectionMode.SingleSelection)
        self.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QListView.Shape.NoFrame)
        self.setSpacing(0)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context)
        self.doubleClicked.connect(self._on_double)

    def set_tokens(self, tokens: Tokens) -> None:
        self.tokens = tokens
        self.delegate.set_tokens(tokens)
        self.viewport().update()

    def set_cover_needed(self, callback) -> None:
        """页面把「这一行需要补封面」的回调塞进来。"""
        self.delegate.cover_needed = callback

    # 兼容不同 PyQt 版本的坐标接口
    def _pos(self, event) -> QPoint:
        try:
            return event.position().toPoint()
        except AttributeError:
            return event.pos()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        pos = self._pos(event)
        index = self.indexAt(pos)
        if index.isValid() and event.button() == Qt.MouseButton.LeftButton:
            if pill_rect(self.visualRect(index)).contains(pos):
                trainer = index.data(TRAINER_ROLE)
                if trainer is not None:
                    self.pillClicked.emit(trainer)
                    event.accept()
                    return
        super().mouseReleaseEvent(event)

    def _on_double(self, index: QModelIndex) -> None:
        trainer = index.data(TRAINER_ROLE)
        if trainer is not None:
            self.activated_trainer.emit(trainer)

    def _on_context(self, pos: QPoint) -> None:
        index = self.indexAt(pos)
        if not index.isValid():
            return
        trainer = index.data(TRAINER_ROLE)
        if trainer is not None:
            self.contextRequested.emit(trainer, self.viewport().mapToGlobal(pos))
