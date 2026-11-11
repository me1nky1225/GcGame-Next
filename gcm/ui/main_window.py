"""主窗口：侧栏 + 顶栏 + 页面栈 + 详情面板 + 队列条。"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QGuiApplication, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..context import AppContext
from ..i18n import t, translator
from ..paths import APP_NAME
from ..theme.tokens import Tokens
from ..util import fmt_size
from .pages.discover import DiscoverPage
from .pages.downloads import DownloadsPage
from .pages.library import LibraryPage
from .pages.settings import SettingsPage
from .icons import icon
from .sidebar import Sidebar
from .topbar import TopBar
from .widgets.detail_panel import DetailPanel
from .widgets.queue_bar import QueueBar
from .widgets.toast import Toast

PAGES = [
    ("library", "搜索已安装的修改器（拼音或首字母）"),
    ("discover", "搜索在线修改器（拼音或首字母）"),
    ("downloads", "搜索下载任务"),
    ("settings", ""),
]


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self._warmed = False
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1100, 700)
        size = ctx.settings.get("window") or {}
        self.resize(int(size.get("w", 1320)), int(size.get("h", 860)))

        self._build()
        self._wire()
        self._apply_tokens(ctx.tokens)
        self._goto(0)
        self._sync_counts()
        self._sync_title_bar(ctx.tokens.name)

    # ---------- 构建 ----------
    def _build(self) -> None:
        """搭好整棵控件树。切换语言时整棵重搭，比逐控件改文案可靠。"""
        ctx = self.ctx
        central = QWidget()
        central.setObjectName("Root")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar(ctx.tokens)
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        self.topbar = TopBar(ctx.tokens)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.pages = QStackedWidget()

        self.library = LibraryPage(ctx)
        self.discover = DiscoverPage(ctx)
        self.downloads_page = DownloadsPage(ctx)
        self.settings_page = SettingsPage(ctx)
        for page in (self.library, self.discover, self.downloads_page, self.settings_page):
            self.pages.addWidget(page)

        body.addWidget(self.pages, 1)
        self.detail = DetailPanel(ctx.tokens)
        body.addWidget(self.detail)

        self.queue_bar = QueueBar(ctx.queue)

        right.addWidget(self.topbar)
        right.addLayout(body, 1)
        right.addWidget(self.queue_bar)
        root.addLayout(right, 1)
        self.setCentralWidget(central)

        self.toast = Toast(central)
        self._apply_sidebar(bool(ctx.settings.get("showSidebar", True)), save=False)
        self._apply_detail(bool(ctx.settings.get("showDetail", True)), save=False)

    # ---------- 原生标题栏 ----------
    def _sync_title_bar(self, theme_name: str) -> None:
        """让 Windows 标题栏跟随深/浅色，避免深色界面顶一条白边。"""
        try:
            import ctypes

            hwnd = int(self.winId())
            dark = ctypes.c_int(1 if theme_name == "dark" else 0)
            for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE / 旧版
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(dark), ctypes.sizeof(dark)
                ) == 0:
                    break
        except Exception:
            pass

    # ---------- 连接 ----------
    def _wire(self) -> None:
        self._wire_ui()
        self._wire_context()

    def _wire_ui(self) -> None:
        """控件之间的连线。重建界面时要重新连一遍。"""
        self.sidebar.navigate.connect(self._goto)
        self.topbar.searchChanged.connect(self._on_search)
        self.topbar.themeToggled.connect(self.ctx.theme.toggle)
        self.topbar.refreshRequested.connect(self._refresh_all)
        self.topbar.importRequested.connect(self._import)
        self.topbar.navToggled.connect(self._on_nav_clicked)
        self.topbar.detailToggled.connect(self._toggle_detail)

        self.library.selectionChanged.connect(self.detail.set_trainer)
        self.library.launchRequested.connect(self._launch)
        self.library.folderRequested.connect(self._open_folder)
        self.library.removeRequested.connect(self._remove)
        self.library.discoverRequested.connect(lambda: self._goto(1))

        self.discover.selectionChanged.connect(self.detail.set_trainer)
        self.discover.acquireRequested.connect(self._acquire)

        self.detail.launchRequested.connect(self._on_detail_primary)
        self.detail.folderRequested.connect(self._on_detail_folder)
        self.detail.removeRequested.connect(self._remove)

        self.settings_page.themeChanged.connect(self._set_theme)
        self.settings_page.pathChanged.connect(self._set_download_path)
        self.settings_page.languageChanged.connect(self._set_language)
        self.settings_page.sourcesChanged.connect(self._set_sources)
        self.settings_page.namesChanged.connect(self._set_steam_names)
        self.settings_page.urlsChanged.connect(self._set_source_urls)
        self.settings_page.sidebarChanged.connect(self._apply_sidebar)
        self.settings_page.detailChanged.connect(self._apply_detail)

        # 列表滚到哪里，就后台补那一行对应的 Steam 中文名和封面
        self.library.view.set_cover_needed(self._need_cover)
        self.discover.view.set_cover_needed(self._need_cover)

    def _wire_context(self) -> None:
        """数据层信号只连一次；它们指向 MainWindow 的方法，重建界面不受影响。"""
        if getattr(self, "_context_wired", False):
            return
        self._context_wired = True
        ctx = self.ctx

        ctx.theme.changed.connect(self._on_theme_changed)
        ctx.installed.changed.connect(self._sync_counts)
        ctx.catalog.changed.connect(self._sync_counts)
        ctx.catalog.changed.connect(self._warm_steam)
        ctx.catalog.status.connect(lambda text: self.toast.show_message(text, "info", 3000))
        ctx.queue.updated.connect(self._sync_counts)
        ctx.queue.completed.connect(self._on_download_done)
        ctx.queue.failed.connect(self._on_download_failed)
        ctx.steam.enriched.connect(self._on_steam_enriched)
        ctx.steam.queryResolved.connect(self._on_steam_query)
        translator.changed.connect(self._on_language_changed)

        QShortcut(QKeySequence("Ctrl+K"), self, activated=self._focus_search)
        QShortcut(QKeySequence("F5"), self, activated=self._refresh_all)
        QShortcut(QKeySequence("Ctrl+B"), self, activated=self._toggle_sidebar)
        QShortcut(QKeySequence("Ctrl+D"), self, activated=self._toggle_detail)
        for i in range(4):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, activated=lambda i=i: self._goto(i))

    # ---------- 侧边栏 ----------
    def _toggle_sidebar(self) -> None:
        self._apply_sidebar(not bool(getattr(self, "_pref_sidebar", True)))

    def _apply_sidebar(self, visible: bool, *, save: bool = True) -> None:
        """收起侧边栏：列表拿到 208px 的横向空间；导航改由顶栏按钮的菜单提供。"""
        self._pref_sidebar = bool(visible)
        self.sidebar.setVisible(bool(visible))
        if hasattr(self.topbar, "set_sidebar_visible"):
            self.topbar.set_sidebar_visible(bool(visible))
        if save:
            self.ctx.settings.set("showSidebar", bool(visible))
        if hasattr(self, "settings_page") and hasattr(self.settings_page, "sidebar_switch"):
            self.settings_page.sidebar_switch.setChecked(bool(visible), emit=False)

    def _toggle_detail(self) -> None:
        self._apply_detail(not bool(getattr(self, "_pref_detail", True)))

    def _apply_detail(self, visible: bool, *, save: bool = True) -> None:
        """收起右侧详情面板：列表拿到 340px，详情仍在选中时后台同步。"""
        self._pref_detail = bool(visible)
        self.detail.setVisible(bool(visible) and self.pages.currentIndex() in (0, 1))
        if hasattr(self.topbar, "set_detail_visible"):
            self.topbar.set_detail_visible(bool(visible))
        if save:
            self.ctx.settings.set("showDetail", bool(visible))
        if hasattr(self, "settings_page") and hasattr(self.settings_page, "detail_switch"):
            self.settings_page.detail_switch.setChecked(bool(visible), emit=False)

    def _on_nav_clicked(self) -> None:
        if self.sidebar.isVisible():
            self._apply_sidebar(False)
            return
        menu = QMenu(self)
        names = [tr("我的修改器"), tr("发现"), tr("下载队列"), tr("设置")]
        icons_ = ["grid", "compass", "download", "settings"]
        current = self.pages.currentIndex()
        for i, (text, icon_name) in enumerate(zip(names, icons_)):
            act = menu.addAction(icon(icon_name, self.ctx.tokens.fg2, 16), text)
            act.setCheckable(True)
            act.setChecked(i == current)
            act.triggered.connect(lambda _checked=False, i=i: self._goto(i))
        menu.addSeparator()
        menu.addAction(tr("显示侧边栏（Ctrl+B）")).triggered.connect(
            lambda: self._apply_sidebar(True)
        )
        menu.exec(self.topbar.nav_btn.mapToGlobal(self.topbar.nav_btn.rect().bottomLeft()))

    def _on_language_changed(self, _code: str) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        """整棵控件树重搭：语言切换后所有文案立即变，不需要重启。"""
        index = self.pages.currentIndex() if hasattr(self, "pages") else 0
        query = self.topbar.search.text() if hasattr(self, "topbar") else ""
        old = self.centralWidget()
        self._build()
        self._wire_ui()
        self._apply_tokens(self.ctx.tokens)
        self._goto(index)
        if query:
            self.topbar.search.setText(query)
            self._on_search(query)
        self._sync_counts()
        if old is not None:
            old.deleteLater()

    # ---------- 导航 ----------
    def _goto(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self.sidebar.select(index)
        _key, placeholder = PAGES[index]
        show_detail = index in (0, 1)
        show_search = index in (0, 1)
        self.detail.setVisible(show_detail and bool(getattr(self, "_pref_detail", True)))
        self.topbar.search.setVisible(show_search)
        if show_search:
            self.topbar.search.setPlaceholderText(t(placeholder))
            self.topbar.search.clear()
        if index == 0:
            self.library.refresh()
        elif index == 1:
            self.discover.refresh()

    def _focus_search(self) -> None:
        self.topbar.search.setFocus()
        self.topbar.search.selectAll()

    def _on_search(self, text: str) -> None:
        index = self.pages.currentIndex()
        if index == 0:
            self.library.set_query(text)
        elif index == 1:
            self.discover.set_query(text)

    def _refresh_all(self) -> None:
        self.ctx.installed.refresh()
        self.library.refresh()
        self.discover.refresh()
        self.ctx.catalog.refresh_online()
        self.toast.show_message(t("已刷新本地库，正在更新在线索引…"), "info", 2500)

    def _on_download_done(self, task) -> None:
        self.ctx.installed.refresh()
        self.library.refresh()
        self.detail.set_trainer(None)
        self.toast.show_message(t("「{name}」已安装").format(name=task.name), "ok", 5000)

    def _on_download_failed(self, task, message: str) -> None:
        self.toast.show_message(
            t("「{name}」下载失败：{msg}").format(name=task.name, msg=message), "error", 6000
        )

    # ---------- Steam 补全 ----------
    def _on_steam_enriched(self, _name: str, entry: dict) -> None:
        if not self.ctx.apply_steam(entry):
            return
        # 重新按当前搜索词筛一遍：中文名刚补上的条目要能立刻被搜到
        self.library.refresh()
        self.discover.refresh()
        current = self.detail.current()
        if current is not None:
            self.detail.set_trainer(current)

    def _on_steam_query(self, query: str, entry: dict | None) -> None:
        """中文搜索没有结果时，悄悄查一次 Steam，把中文名补进数据再筛一遍。"""
        if entry:
            self.ctx.apply_steam(entry)
            self.discover.model.refresh()
        if self.topbar.search.text().strip().lower() == query.strip().lower():
            self.discover.set_query(self.topbar.search.text())

    def _sync_counts(self) -> None:
        installed = len(self.ctx.installed.items())
        downloads = len(self.ctx.queue.active())
        self.sidebar.set_counts(installed, downloads)
        total = len(self.ctx.catalog.items())
        self.sidebar.set_db_info(t("数据库 {n} 个修改器").format(n=f"{total:,}"))

    # ---------- 主题 ----------
    def _on_theme_changed(self, tokens: Tokens) -> None:
        self._apply_tokens(tokens)
        self.settings_page.set_theme_name(tokens.name)
        self.ctx.settings.set("theme", tokens.name)
        self._sync_title_bar(tokens.name)

    def _set_theme(self, name: str) -> None:
        self.ctx.theme.set_theme(name)

    def _apply_tokens(self, tokens: Tokens) -> None:
        self.sidebar.set_tokens(tokens)
        self.topbar.set_tokens(tokens)
        self.library.set_tokens(tokens)
        self.discover.set_tokens(tokens)
        self.downloads_page.set_tokens(tokens)
        self.settings_page.set_tokens(tokens)
        self.detail.set_tokens(tokens)

    # ---------- 动作 ----------
    def _launch(self, trainer) -> None:
        ok, msg = self.ctx.installed.launch(trainer)
        if not ok:
            QMessageBox.warning(self, t("启动失败"), msg)
            return
        self.detail.set_trainer(trainer)
        self.library.refresh()

    def _open_folder(self, trainer) -> None:
        ok, msg = self.ctx.installed.open_folder(trainer)
        if not ok:
            QMessageBox.warning(self, t("无法打开目录"), msg)

    def _remove(self, trainer) -> None:
        if trainer is None or not trainer.installed:
            return
        answer = QMessageBox.question(
            self,
            t("删除修改器"),
            t("把「{name}」移到回收站？").format(name=trainer.name)
            + f"\n\n{fmt_size(trainer.size_mb)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        ok, msg = self.ctx.installed.remove(trainer)
        if not ok:
            QMessageBox.warning(self, t("删除失败"), msg)
        else:
            self.detail.set_trainer(None)

    def _acquire(self, trainer) -> None:
        if trainer is None:
            return
        if trainer.installed:
            self._launch(trainer)
            return
        if trainer.external:
            self._open_web(trainer)
            return
        if not trainer.url:
            self.toast.show_message(
                t("「{name}」来自 GCM 源，需要他们的签名服务才能下载；"
                  "可以在「发现」里选 FLiNG 来源的条目实测下载").format(name=trainer.name),
                "warn",
                6000,
            )
            self._goto(1)
            return
        if self.ctx.queue.is_queued(trainer.name):
            self.toast.show_message(
                t("「{name}」已在下载队列里").format(name=trainer.name), "info", 2500
            )
            self._goto(2)
            return
        self.ctx.queue.enqueue(trainer)
        self._goto(2)

    def _on_detail_primary(self, trainer) -> None:
        if trainer is None:
            return
        if trainer.installed:
            self._launch(trainer)
        else:
            self._acquire(trainer)

    def _on_detail_folder(self, trainer) -> None:
        if trainer is None:
            return
        if trainer.installed:
            self._open_folder(trainer)
        elif trainer.external:
            QGuiApplication.clipboard().setText(trainer.url)
            self.toast.show_message(t("官方页面链接已复制到剪贴板"), "ok", 2500)
        else:
            QMessageBox.information(
                self,
                trainer.name,
                t("{desc}\n\nAuthor: {author}\nVersion: {version}").format(
                    desc=trainer.desc or t("在线资源"),
                    author=trainer.author or "—",
                    version=trainer.version or "—",
                ),
            )

    def _open_web(self, trainer) -> None:
        if not trainer.url:
            self.toast.show_message(t("这条记录没有官方网站链接"), "warn", 3000)
            return
        QDesktopServices.openUrl(QUrl(trainer.url))
        self.toast.show_message(
            t("已在浏览器打开「{name}」的官方页面").format(name=trainer.name), "info", 4000
        )

    # ---------- 设置 ----------
    def _set_download_path(self, path: str) -> None:
        target = Path(path)
        moving = target != self.ctx.installed.directory()
        self.ctx.settings.set("downloadPath", str(target))
        self.ctx.installed.set_directory(target)
        self.ctx.queue.download_dir = target
        self.ctx.installed.refresh()
        self.library.refresh()
        self._sync_counts()
        if moving:
            self.toast.show_message(t("下载目录已改为 {path}").format(path=str(target)), "ok")
            if any(t.status in ("downloading", "queued", "paused") for t in self.ctx.queue.tasks):
                self.toast.show_message(t("正在进行的下载仍会写入旧目录"), "warn")

    def _set_language(self, code: str) -> None:
        self.ctx.settings.set("language", code)
        translator.set_language(code)

    def _set_sources(self, values: dict) -> None:
        self.ctx.settings.set("sources", values)
        self.ctx.catalog.reapply_sources()
        self.ctx.catalog.refresh_online()
        self.discover.refresh()
        self._sync_counts()

    def _set_source_urls(self, urls: dict) -> None:
        self.ctx.settings.set("sourceUrls", urls)
        self.toast.show_message(t("下载源地址已保存，点顶栏刷新重新抓取"), "ok", 3500)

    def _set_steam_names(self, enabled: bool) -> None:
        self.ctx.settings.set("steamNames", bool(enabled))
        translator.show_chinese = bool(enabled)
        self.library.model.refresh()
        self.discover.model.refresh()
        current = self.detail.current()
        if current is not None:
            self.detail.set_trainer(current)

    # ---------- Steam 名称 / 封面 ----------
    def _warm_steam(self) -> None:
        """索引加载完后，后台补一批中文名，让中文搜索有词可用。"""
        if self._warmed:
            return
        self._warmed = True
        # 已有 appid 但没有本地封面的（内置种子就是这种）：补封面
        for trainer in self.ctx.catalog.items():
            if trainer.appid and not trainer.cover:
                self.ctx.steam.request(trainer.name, urgent=True)
        for trainer in self.ctx.installed.items():
            if not trainer.cover:
                self.ctx.steam.request(trainer.alias or trainer.name, urgent=True)
        names = [t.name for t in self.ctx.catalog.items() if not t.name_zh][:300]
        if not names:
            return
        queued = self.ctx.steam.warm(names, limit=300)
        if queued:
            self.toast.show_message(
                t("正在后台补全中文名（{n} 条），补齐后可直接搜中文").format(n=queued), "info", 4000
            )

    def _need_cover(self, trainer) -> None:
        if trainer is None:
            return
        # 可见行的封面优先插队，不然会排在后台 300 条补全后面
        self.ctx.steam.request(getattr(trainer, "alias", "") or trainer.name, urgent=True)

    # ---------- 导入 ----------
    def _import(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            t("导入修改器"),
            str(Path.home()),
            t("修改器 (*.zip *.exe *.7z);;所有文件 (*.*)"),
        )
        if not files:
            return
        target = self.ctx.installed.directory()
        target.mkdir(parents=True, exist_ok=True)
        added = 0
        errors: list[str] = []
        for raw in files:
            src = Path(raw)
            try:
                if src.suffix.lower() == ".zip":
                    folder = target / src.stem
                    if folder.exists():
                        errors.append(f"{src.name}：同名目录已存在")
                        continue
                    with zipfile.ZipFile(src) as zf:
                        names = zf.namelist()
                        if names and names[0].endswith("/"):
                            zf.extractall(target)
                        else:
                            folder.mkdir(parents=True, exist_ok=True)
                            zf.extractall(folder)
                else:
                    dest = target / src.name
                    if dest.exists():
                        errors.append(f"{src.name}：同名文件已存在")
                        continue
                    shutil.copy2(src, dest)
                added += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{src.name}：{exc}")
        self.ctx.installed.refresh()
        if added:
            self.library.refresh()
        if errors:
            QMessageBox.warning(self, t("部分文件未导入"), "\n".join(errors[:6]))

    # ---------- 收尾 ----------
    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "toast") and self.toast.isVisible():
            self.toast._place()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.ctx.settings.update(
            {"window": {"w": self.width(), "h": self.height()}}
        )
        super().closeEvent(event)
