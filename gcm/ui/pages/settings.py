"""设置页：外观 / 库 / 数据源 / 关于。"""
from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QActionGroup
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...context import AppContext
from ...i18n import DEFAULT_LANG, LANGS, lang_name, t as tr
from ...paths import APP_VERSION, DATA_DIR, display_path
from ...theme.tokens import Tokens
from ...ui.icons import icon
from ..widgets.switch import Switch


class Card(QFrame):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(16, 14, 16, 14)
        self.body.setSpacing(10)
        label = QLabel(title)
        label.setObjectName("SectionLabel")
        self.body.addWidget(label)


class SettingsPage(QWidget):
    themeChanged = pyqtSignal(str)
    pathChanged = pyqtSignal(str)
    languageChanged = pyqtSignal(str)
    sourcesChanged = pyqtSignal(dict)
    urlsChanged = pyqtSignal(dict)
    namesChanged = pyqtSignal(bool)
    sidebarChanged = pyqtSignal(bool)
    detailChanged = pyqtSignal(bool)

    def __init__(self, ctx: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        holder = QWidget()
        holder.setMaximumWidth(880)
        scroll.setWidget(holder)
        root = QVBoxLayout(holder)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(14)

        title = QLabel(tr("设置"))
        title.setObjectName("H1")
        root.addWidget(title)

        # ---- 外观 ----
        appearance = Card(tr("外观"))
        row = QHBoxLayout()
        row.setSpacing(8)
        self._theme_group = QButtonGroup(self)
        self._theme_group.setExclusive(True)
        for i, (name, text) in enumerate((("dark", "深色"), ("light", "浅色"))):
            btn = QPushButton(tr(text))
            btn.setObjectName("Chip")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumWidth(72)
            self._theme_group.addButton(btn, i)
            row.addWidget(btn)
            if name == ctx.theme.name:
                btn.setChecked(True)
        row.addStretch(1)
        appearance.body.addLayout(row)
        self._theme_group.idClicked.connect(self._on_theme)

        lang_row = QHBoxLayout()
        lang_label = QLabel(tr("界面语言"))
        lang_label.setObjectName("FieldLabel")
        lang_row.addWidget(lang_label)
        lang_row.addStretch(1)
        self.lang_btn = QPushButton()
        self.lang_btn.setObjectName("SortBtn")
        self.lang_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.lang_btn.setIcon(icon("chevron_down", ctx.tokens.muted, 14))
        menu = QMenu(self.lang_btn)
        group = QActionGroup(menu)
        current_lang = ctx.settings.get("language")
        for text, code in LANGS:
            act = menu.addAction(text)
            act.setCheckable(True)
            act.setData(code)
            if code == current_lang:
                act.setChecked(True)
                self.lang_btn.setText(text)
            group.addAction(act)
        if not self.lang_btn.text():
            self.lang_btn.setText(lang_name(DEFAULT_LANG))
        menu.triggered.connect(self._on_language)
        self.lang_btn.setMenu(menu)
        lang_row.addWidget(self.lang_btn)
        appearance.body.addLayout(lang_row)
        note = QLabel(tr("语言切换即时生效，无需重启"))
        note.setObjectName("Subtle")
        appearance.body.addWidget(note)

        side_row = QHBoxLayout()
        side_text = QVBoxLayout()
        side_text.setSpacing(2)
        side_label = QLabel(tr("显示侧边栏"))
        side_label.setObjectName("FieldLabel")
        side_hint = QLabel(tr("关掉后给列表腾出空间，Ctrl+B 随时切换"))
        side_hint.setObjectName("Subtle")
        side_text.addWidget(side_label)
        side_text.addWidget(side_hint)
        side_row.addLayout(side_text)
        side_row.addStretch(1)
        self.sidebar_switch = Switch(ctx.tokens, bool(ctx.settings.get("showSidebar", True)))
        self.sidebar_switch.toggled.connect(self.sidebarChanged)
        side_row.addWidget(self.sidebar_switch)
        appearance.body.addLayout(side_row)
        detail_row = QHBoxLayout()
        detail_text = QVBoxLayout()
        detail_text.setSpacing(2)
        detail_label = QLabel(tr("显示详情面板"))
        detail_label.setObjectName("FieldLabel")
        detail_hint = QLabel(tr("关掉后列表铺满整宽，选中项仍会在后台同步（Ctrl+D）"))
        detail_hint.setObjectName("Subtle")
        detail_text.addWidget(detail_label)
        detail_text.addWidget(detail_hint)
        detail_row.addLayout(detail_text)
        detail_row.addStretch(1)
        self.detail_switch = Switch(ctx.tokens, bool(ctx.settings.get("showDetail", True)))
        self.detail_switch.toggled.connect(self.detailChanged)
        detail_row.addWidget(self.detail_switch)
        appearance.body.addLayout(detail_row)
        root.addWidget(appearance)

        # ---- 库 ----
        library = Card(tr("修改器库"))
        path_label = QLabel(tr("下载与安装目录"))
        path_label.setObjectName("FieldLabel")
        library.body.addWidget(path_label)
        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self.path_edit = QLineEdit(str(ctx.installed.directory()))
        self.path_edit.setObjectName("PathField")
        self.path_edit.setClearButtonEnabled(True)
        self.path_edit.setToolTip(tr("修改器会下载并安装到这个目录，路径可以直接编辑"))
        self.path_edit.editingFinished.connect(self._on_path_edited)
        path_row.addWidget(self.path_edit, 1)
        browse = QPushButton(tr("浏览…"))
        browse.clicked.connect(self._pick_dir)
        path_row.addWidget(browse)
        open_btn = QPushButton(tr("打开"))
        open_btn.setObjectName("Ghost")
        open_btn.clicked.connect(self._open_dir)
        path_row.addWidget(open_btn)
        library.body.addLayout(path_row)
        self._path_hint = QLabel("")
        self._path_hint.setObjectName("Subtle")
        self._path_hint.setWordWrap(True)
        self._path_hint.setVisible(False)
        library.body.addWidget(self._path_hint)
        root.addWidget(library)

        # ---- 数据源 ----
        sources = Card(tr("数据源"))
        self._source_switches: dict[str, Switch] = {}
        current = ctx.settings.get("sources") or {}
        for key, text, desc in (
            ("gcm", "GCM 数据库", "官方维护的修改器索引，含版本号"),
            ("fling", "FLiNG", "网页抓取，作者 Hexinton 等"),
            ("xiaoxing", "小幸", "国产修改器，需要解锁"),
            ("ct", "Cheat Table", "the-cheat-script 社区脚本"),
        ):
            sw = Switch(ctx.tokens, bool(current.get(key, True)))
            sw.toggled.connect(lambda _checked=False: self._emit_sources())
            src_row = QHBoxLayout()
            src_row.setSpacing(12)
            name = QLabel(tr(text) if text != "FLiNG" else text)
            name.setObjectName("Value")
            name.setMinimumWidth(96)
            src_row.addWidget(name)
            hint = QLabel(tr(desc))
            hint.setObjectName("Subtle")
            src_row.addWidget(hint)
            src_row.addStretch(1)
            src_row.addWidget(sw)
            sources.body.addLayout(src_row)
            self._source_switches[key] = sw

        names_row = QHBoxLayout()
        names_row.setSpacing(12)
        names_label = QLabel(tr("显示中文游戏名"))
        names_label.setObjectName("Value")
        names_label.setMinimumWidth(96)
        names_row.addWidget(names_label)
        names_hint = QLabel(tr("从 Steam 补全中文名，关掉就只用原始英文名"))
        names_hint.setObjectName("Subtle")
        names_row.addWidget(names_hint)
        names_row.addStretch(1)
        self.names_switch = Switch(ctx.tokens, bool(ctx.settings.get("steamNames", True)))
        self.names_switch.toggled.connect(self.namesChanged)
        names_row.addWidget(self.names_switch)
        sources.body.addLayout(names_row)
        root.addWidget(sources)

        # ---- 下载源地址 ----
        urls = Card(tr("下载源地址"))
        note = QLabel(tr("抓取与下载的站点地址，可改成镜像或反代；改完点顶栏的刷新重新抓取"))
        note.setObjectName("Subtle")
        note.setWordWrap(True)
        urls.body.addWidget(note)
        self._url_edits: dict[str, QLineEdit] = {}
        current_urls = ctx.settings.get("sourceUrls") or {}
        for key, text in (
            ("fling", "风灵月影 FLiNG"),
            ("ct", "Cheat Table 站点"),
            ("xiaoxing", "小幸站点"),
        ):
            line = QHBoxLayout()
            line.setSpacing(10)
            label = QLabel(tr(text) if text != "风灵月影 FLiNG" else tr("风灵月影（FLiNG）"))
            label.setObjectName("FieldLabel")
            label.setMinimumWidth(140)
            line.addWidget(label)
            edit = QLineEdit(str(current_urls.get(key, "")))
            edit.setPlaceholderText("https://")
            line.addWidget(edit, 1)
            edit.editingFinished.connect(self._emit_urls)
            urls.body.addLayout(line)
            self._url_edits[key] = edit
        reset_row = QHBoxLayout()
        reset_row.addStretch(1)
        reset = QPushButton(tr("恢复默认地址"))
        reset.setObjectName("Ghost")
        reset.clicked.connect(self._reset_urls)
        reset_row.addWidget(reset)
        urls.body.addLayout(reset_row)
        root.addWidget(urls)

        # ---- 关于 ----
        about = Card(tr("关于"))
        about.body.addWidget(QLabel(f"GCM Next {APP_VERSION}"))
        hint = QLabel(tr("数据目录：") + display_path(DATA_DIR))
        hint.setObjectName("PathBox")
        hint.setWordWrap(True)
        about.body.addWidget(hint)
        credit = QLabel(
            tr("重构自 dyang886/Game-Cheats-Manager · PyQt6 · 设计系统驱动主题")
        )
        credit.setObjectName("Subtle")
        about.body.addWidget(credit)
        root.addWidget(about)
        root.addStretch(1)

    # ---- 事件 ----
    def set_theme_name(self, name: str) -> None:
        """外部切了主题（顶栏按钮/快捷键）时，把这里的深/浅色选中态同步过去。"""
        btn = self._theme_group.button(0 if name == "dark" else 1)
        if btn is not None and not btn.isChecked():
            btn.setChecked(True)

    def _on_theme(self, idx: int) -> None:
        self.themeChanged.emit("dark" if idx == 0 else "light")

    def _on_language(self, action) -> None:
        self.lang_btn.setText(action.text())
        self.languageChanged.emit(action.data())

    def _apply_path(self, raw: str) -> bool:
        """校验并应用手输/选择的目录，返回是否成功。"""
        text = str(raw or "").strip().strip('"').strip()
        if not text:
            self.path_edit.setText(str(self.ctx.installed.directory()))
            return False
        text = os.path.expandvars(os.path.expanduser(text))
        target = Path(text)
        existed = target.is_dir()
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError:
            self._path_hint.setText(tr("无法创建或访问该目录"))
            self._path_hint.setObjectName("DangerHint")
            self._restyle_hint()
            self.path_edit.setText(str(self.ctx.installed.directory()))
            return False
        self.path_edit.setText(str(target))
        self._path_hint.setText(
            tr("目录不存在，已自动创建") if not existed else ""
        )
        self._path_hint.setObjectName("Subtle" if not existed else "Subtle")
        self._restyle_hint()
        self.pathChanged.emit(str(target))
        return True

    def _restyle_hint(self) -> None:
        self._path_hint.style().unpolish(self._path_hint)
        self._path_hint.style().polish(self._path_hint)
        self._path_hint.setVisible(bool(self._path_hint.text()))

    def _on_path_edited(self) -> None:
        current = str(self.ctx.installed.directory())
        if self.path_edit.text().strip() == current:
            return
        self._apply_path(self.path_edit.text())

    def _pick_dir(self) -> None:
        from PyQt6.QtWidgets import QFileDialog

        path = QFileDialog.getExistingDirectory(
            self, tr("选择修改器目录"), str(self.ctx.installed.directory())
        )
        if path:
            self.path_edit.setText(path)
            self._apply_path(path)

    def _open_dir(self) -> None:
        import os

        os.startfile(str(self.ctx.installed.directory()))  # noqa: S606

    def _emit_sources(self) -> None:
        self.sourcesChanged.emit({k: sw.isChecked() for k, sw in self._source_switches.items()})

    def _emit_urls(self) -> None:
        urls = {k: edit.text().strip().rstrip("/") for k, edit in self._url_edits.items()}
        self.urlsChanged.emit(urls)

    def _reset_urls(self) -> None:
        from ...settings_store import DEFAULTS

        defaults = DEFAULTS.get("sourceUrls") or {}
        for key, edit in self._url_edits.items():
            edit.setText(str(defaults.get(key, "")))
        self._emit_urls()

    def set_tokens(self, tokens: Tokens) -> None:
        for sw in self._source_switches.values():
            sw.set_tokens(tokens)
