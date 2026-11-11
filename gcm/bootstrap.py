"""启动入口：装配依赖、应用主题、打开主窗口。"""
from __future__ import annotations

import sys

from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import QApplication

from .context import AppContext
from .data.catalog import Catalog
from .data.downloads import DownloadQueue
from .data.enrich import SteamEnricher
from .data.installed import InstalledIndex
from .i18n import translator
from .paths import APP_NAME, asset_path, ensure_dirs
from .settings_store import SettingsStore
from .theme.manager import ThemeManager
from .ui.main_window import MainWindow


def build_context(app: QApplication) -> AppContext:
    settings = SettingsStore()
    translator.set_language(settings.get("language", "zh_CN"))
    translator.show_chinese = bool(settings.get("steamNames", True))
    theme = ThemeManager(app, settings.get("theme", "dark"))
    theme.apply()

    installed = InstalledIndex(settings)
    installed.refresh()

    catalog = Catalog(settings)
    catalog.load()

    queue = DownloadQueue(installed.directory())
    steam = SteamEnricher()
    steam.start()
    ctx = AppContext(
        settings=settings,
        theme=theme,
        installed=installed,
        catalog=catalog,
        queue=queue,
        steam=steam,
    )
    # 内置热门游戏的中英名对照：不联网也能用中文搜到
    for entry in steam.store.seed_entries():
        ctx.apply_steam(entry)
    # 每次重扫安装目录后，把缓存里的中文名/封面重新贴到新对象上
    # （否则删掉一个修改器后，其它行的封面会全部退回色块）
    installed.on_rebuild = ctx.reapply_cached_steam
    return ctx


def run(argv: list[str] | None = None) -> int:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName("GCM Next")
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei UI", 9))

    icon_file = asset_path("app.ico")
    if icon_file.is_file():
        app.setWindowIcon(QIcon(str(icon_file)))

    ensure_dirs()
    ctx = build_context(app)
    window = MainWindow(ctx)
    window.show()
    return app.exec()
