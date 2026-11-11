"""应用级依赖容器：页面只依赖 ctx，不直接摸全局单例。"""
from __future__ import annotations

from dataclasses import dataclass

from .data.catalog import Catalog
from .data.downloads import DownloadQueue
from .data.enrich import SteamEnricher
from .data.installed import InstalledIndex
from .settings_store import SettingsStore
from .theme.manager import ThemeManager


@dataclass
class AppContext:
    settings: SettingsStore
    theme: ThemeManager
    installed: InstalledIndex
    catalog: Catalog
    queue: DownloadQueue
    steam: SteamEnricher

    @property
    def tokens(self):
        return self.theme.tokens

    def reapply_cached_steam(self) -> int:
        """重新扫描后（删除/安装/换目录）把磁盘缓存里的中文名与封面贴回去。

        列表项是每次 `refresh()` 重建的新对象，Steam 信息只存在于内存里，
        不贴回去就会出现「删掉一个之后其它行的图标全变回色块」。
        """
        fixed = 0
        for trainer in list(self.installed.items()) + list(self.catalog.items()):
            if trainer.appid and trainer.cover and trainer.name_zh:
                continue
            keys = [getattr(trainer, "alias", "") or "", trainer.name, trainer.name_zh or ""]
            for key in keys:
                if not key:
                    continue
                entry = self.steam.store.get(key)
                if entry and not entry.get("miss"):
                    if self.apply_steam(entry):
                        fixed += 1
                    break
        return fixed

    def apply_steam(self, entry: dict) -> bool:
        """把一条 Steam 查询结果写回列表数据，返回是否有改动。

        只按名字精确匹配（英文名或中文名），所以不会串到别的游戏上。
        """
        names = {
            str(entry.get("en") or "").strip().lower(),
            str(entry.get("zh") or "").strip().lower(),
        }
        names.discard("")
        if not names:
            return False
        changed = False
        for trainer in list(self.catalog.items()) + list(self.installed.items()):
            candidates = {
                trainer.name.strip().lower(),
                (trainer.name_zh or "").strip().lower(),
                (getattr(trainer, "alias", "") or "").strip().lower(),
            }
            if not (candidates - {""}) & names:
                continue
            if entry.get("appid") and trainer.appid != int(entry["appid"]):
                trainer.appid = int(entry["appid"])
                changed = True
            if entry.get("zh") and trainer.name_zh != str(entry["zh"]):
                trainer.name_zh = str(entry["zh"])
                changed = True
            cover = str(entry.get("cover_path") or "") or self.steam.store.cached_cover(entry)
            if cover and trainer.cover != cover:
                trainer.cover = cover
                changed = True
        return changed
