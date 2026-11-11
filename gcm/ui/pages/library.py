"""「我的修改器」页：工具条 + 卡片列表 + 空态。"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QActionGroup
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ...context import AppContext
from ...data.search import matches
from ...i18n import t as tr
from ...theme.tokens import Tokens
from ...util import fmt_size, humanize
from ..icons import icon, pixmap
from ..widgets.trainer_list import TrainerListView, TrainerModel

SOURCES = ["全部", "GCM", "FLiNG", "小幸", "CT"]


def make_header(title: str, subtitle: str = "") -> tuple[QWidget, QLabel]:
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    h1 = QLabel(title)
    h1.setObjectName("H1")
    lay.addWidget(h1)
    sub = QLabel(subtitle)
    sub.setObjectName("Subtle")
    lay.addWidget(sub)
    return box, sub


def make_chips(tokens: Tokens, names: list[str]) -> tuple[QWidget, QButtonGroup]:
    box = QWidget()
    lay = QHBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(8)
    group = QButtonGroup(box)
    group.setExclusive(True)
    for i, name in enumerate(names):
        btn = QPushButton(tr(name))
        btn.setObjectName("Chip")
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        group.addButton(btn, i)
        lay.addWidget(btn)
        if i == 0:
            btn.setChecked(True)
    lay.addStretch(1)
    return box, group


def make_empty(tokens: Tokens, title: str, hint: str, action: str = "") -> tuple[QWidget, QPushButton | None]:
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 40, 0, 40)
    lay.setSpacing(10)
    lay.addStretch(1)

    ic = QLabel()
    ic.setPixmap(pixmap("grid", tokens.muted, 30))
    ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.addWidget(ic)

    title_lbl = QLabel(tr(title))
    title_lbl.setObjectName("EmptyTitle")
    title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.addWidget(title_lbl)

    h = QLabel(tr(hint))
    h.setObjectName("EmptyHint")
    h.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.addWidget(h)

    btn = None
    if action:
        btn = QPushButton(tr(action))
        btn.setObjectName("Primary")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(btn)
        row.addStretch(1)
        lay.addSpacing(6)
        lay.addLayout(row)

    lay.addStretch(1)
    return box, btn


class LibraryPage(QWidget):
    selectionChanged = pyqtSignal(object)
    launchRequested = pyqtSignal(object)
    folderRequested = pyqtSignal(object)
    removeRequested = pyqtSignal(object)
    discoverRequested = pyqtSignal()

    def __init__(self, ctx: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self._query = ""
        self._source = "全部"
        self._sort = "updated"
        self._selected_name: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 0)
        root.setSpacing(14)

        head, self._subtitle = make_header(tr("我的修改器"), "")
        head_row = QHBoxLayout()
        head_row.addWidget(head)
        head_row.addStretch(1)
        self.sort_btn = QPushButton(tr("按更新时间排序"))
        self.sort_btn.setObjectName("SortBtn")
        self.sort_btn.setIcon(icon("chevron_down", ctx.tokens.muted, 14))
        self.sort_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.sort_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        menu = QMenu(self.sort_btn)
        self._sort_group = QActionGroup(menu)
        for text, key in (("按更新时间排序", "updated"), ("按名称排序", "name")):
            act = menu.addAction(tr(text))
            act.setCheckable(True)
            act.setData(key)
            act.setChecked(key == self._sort)
            self._sort_group.addAction(act)
        self._sort_group.triggered.connect(self._on_sort)
        self.sort_btn.setMenu(menu)
        head_row.addWidget(self.sort_btn, 0, Qt.AlignmentFlag.AlignBottom)
        root.addLayout(head_row)

        chips, self._chip_group = make_chips(ctx.tokens, SOURCES)
        self._chip_group.idClicked.connect(self._on_chip)
        root.addWidget(chips)

        self.model = TrainerModel(self)
        self.view = TrainerListView(ctx.tokens)
        self.view.setModel(self.model)
        self.view.pillClicked.connect(self._on_pill)
        self.view.activated_trainer.connect(self.launchRequested.emit)
        self.view.contextRequested.connect(self._on_context)
        self.view.selectionModel().currentChanged.connect(self._on_current)

        empty, empty_btn = make_empty(
            ctx.tokens,
            "还没有安装修改器",
            "在「发现」里获取，或点右上角「导入修改器」添加本地文件",
            "去发现",
        )
        if empty_btn is not None:
            empty_btn.clicked.connect(self.discoverRequested.emit)
        self.empty = empty

        self.stack = QStackedWidget()
        self.stack.addWidget(self.view)
        self.stack.addWidget(self.empty)
        root.addWidget(self.stack, 1)

        ctx.installed.changed.connect(self.refresh)

    # ---- 数据 ----
    def _filtered(self):
        items = [
            t
            for t in self.ctx.installed.items()
            if (self._source == "全部" or t.source == self._source)
            and matches(self._query, t.name, f"{t.author} {t.source}")
        ]
        if self._sort == "name":
            items.sort(key=lambda t: t.name.lower())
        else:
            items.sort(key=lambda t: (t.updated or 0), reverse=True)
        return items

    def refresh(self) -> None:
        items = self._filtered()
        if [t.name for t in items] == [t.name for t in self.model.items()]:
            self.model.refresh()
            self._update_subtitle()
            return
        bar = self.view.verticalScrollBar()
        pos = bar.value()
        had_selection = self._selected_name is not None
        self.model.set_items(items)
        self._update_subtitle()
        self.stack.setCurrentWidget(self.view if items else self.empty)
        self._restore_selection(items)
        if had_selection:
            bar.setValue(pos)

    def _update_subtitle(self) -> None:
        all_items = self.ctx.installed.items()
        if all_items:
            total = len(all_items)
            size = fmt_size(sum(t.size_mb for t in all_items))
            newest = max((t.updated for t in all_items if t.updated), default=0)
            stamp = humanize(newest) if newest else "—"
            self._subtitle.setText(
                tr("{n} 个 · 共 {size} · 最近更新 {stamp}").format(
                    n=total, size=size, stamp=stamp
                )
            )
        else:
            self._subtitle.setText(tr("扫描目录里还没有修改器"))

    def _restore_selection(self, items) -> None:
        target = None
        for t in items:
            if t.name == self._selected_name:
                target = t
                break
        if target is None and items and self._selected_name is None:
            target = items[0]
        if target is None:
            self.selectionChanged.emit(None)
            return
        idx = self.model.index(items.index(target), 0)
        self.view.setCurrentIndex(idx)
        self.selectionChanged.emit(target)

    def select_name(self, name: str) -> None:
        self._selected_name = name
        self.refresh()

    # ---- 事件 ----
    def set_query(self, text: str) -> None:
        self._query = text
        self.refresh()

    def set_tokens(self, tokens: Tokens) -> None:
        self.view.set_tokens(tokens)

    def _on_chip(self, idx: int) -> None:
        self._source = SOURCES[idx]
        self.refresh()

    def _on_sort(self, action) -> None:
        self._sort = action.data()
        self.sort_btn.setText(action.text())
        self.refresh()

    def _on_current(self, current, _previous) -> None:
        t = self.model.trainer_at(current)
        if t is not None:
            self._selected_name = t.name
        self.selectionChanged.emit(t)

    def _on_pill(self, trainer) -> None:
        self.launchRequested.emit(trainer)

    def _on_context(self, trainer, pos) -> None:
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)
        act_launch = menu.addAction(tr("启动"))
        act_folder = menu.addAction(tr("打开所在目录"))
        menu.addSeparator()
        act_remove = menu.addAction(tr("删除（移到回收站）"))
        chosen = menu.exec(pos)
        if chosen is act_launch:
            self.launchRequested.emit(trainer)
        elif chosen is act_folder:
            self.folderRequested.emit(trainer)
        elif chosen is act_remove:
            self.removeRequested.emit(trainer)
