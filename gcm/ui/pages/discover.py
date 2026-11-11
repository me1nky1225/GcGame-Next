"""「发现」页：在线修改器库。"""
from __future__ import annotations

import re

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget

from ...context import AppContext
from ...data.search import matches
from ...i18n import t as tr
from ...theme.tokens import Tokens
from ..widgets.trainer_list import TrainerListView, TrainerModel
from .library import SOURCES, make_chips, make_empty, make_header

_CJK = re.compile(r"[\u3400-\u9fff]")


class DiscoverPage(QWidget):
    selectionChanged = pyqtSignal(object)
    acquireRequested = pyqtSignal(object)

    def __init__(self, ctx: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self._query = ""
        self._source = "全部"
        self._selected_name: str | None = None
        self._asked: set[str] = set()  # 已经问过 Steam 的中文搜索词

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 0)
        root.setSpacing(14)

        head, self._subtitle = make_header(tr("发现"), "")
        root.addWidget(head)

        chips, self._chip_group = make_chips(ctx.tokens, SOURCES)
        self._chip_group.idClicked.connect(self._on_chip)
        root.addWidget(chips)

        self.model = TrainerModel(self)
        self.view = TrainerListView(ctx.tokens)
        self.view.setModel(self.model)
        self.view.pillClicked.connect(self.acquireRequested.emit)
        self.view.activated_trainer.connect(self.acquireRequested.emit)
        self.view.selectionModel().currentChanged.connect(self._on_current)

        empty, _ = make_empty(
            ctx.tokens,
            "没有匹配的修改器",
            "换个关键词试试，或检查「设置 → 数据源」是否开启",
        )
        self.empty = empty

        self.stack = QStackedWidget()
        self.stack.addWidget(self.view)
        self.stack.addWidget(self.empty)
        root.addWidget(self.stack, 1)

        ctx.catalog.changed.connect(self.refresh)

    def refresh(self) -> None:
        items = [
            t
            for t in self.ctx.catalog.items()
            if (self._source == "全部" or t.source == self._source)
            and matches(self._query, t.name, t.search_text())
        ]
        # 条目没变（只是后台补到了中文名/封面）时绝不重置模型：
        # 重置会让视图滚回顶部，用户正在往下翻的时候尤其明显。
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
        target = next((t for t in items if t.name == self._selected_name), None)
        if target is None and not had_selection and items:
            target = items[0]
        if target is not None:
            self.view.setCurrentIndex(self.model.index(items.index(target), 0))
        if had_selection:
            bar.setValue(pos)
        if target is None:
            self.selectionChanged.emit(None)
        else:
            self.selectionChanged.emit(target)

    def _update_subtitle(self) -> None:
        all_items = self.ctx.catalog.items()
        counts: dict[str, int] = {}
        for t in all_items:
            counts[t.source] = counts.get(t.source, 0) + 1
        parts = " · ".join(f"{tr(src)} {n}" for src, n in counts.items() if n)
        self._subtitle.setText(
            tr("{n} 个修改器").format(n=len(all_items)) + (f" · {parts}" if parts else "")
        )

    def set_query(self, text: str) -> None:
        self._query = text
        self.refresh()
        # 中文搜不到时，去 Steam 查一次：拿回中文名后再筛一遍（每个词只问一次，避免打转）
        query = text.strip()
        if query and _CJK.search(query) and not self.model.items() and query not in self._asked:
            self._asked.add(query)
            self.ctx.steam.request_query(query)

    def set_tokens(self, tokens: Tokens) -> None:
        self.view.set_tokens(tokens)

    def _on_chip(self, idx: int) -> None:
        self._source = SOURCES[idx]
        self.refresh()

    def _on_current(self, current, _previous) -> None:
        t = self.model.trainer_at(current)
        if t is not None:
            self._selected_name = t.name
        self.selectionChanged.emit(t)
