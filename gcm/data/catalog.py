"""在线库：旧版 GCM 数据库（只读）+ 三条可抓取的公开源（FLiNG / CT / 小幸）。

每个源抓完都落一份缓存到 `DATA_DIR/cache/<key>.json`：
启动先用缓存把界面填满，再在后台按设置里开启的源刷新。
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from ..paths import DATA_DIR, LEGACY_DB_DIR
from .sources import ct, fling, xiaoxing
from .trainer import Trainer

_CJK = re.compile(r"[\u3400-\u9fff]")

ORIGIN_MAP = {
    "fling": "FLiNG",
    "xiaoxing": "小幸",
    "the_cheat_script": "CT",
    "ct_other": "CT",
    "gcm": "GCM",
    "other": "GCM",
}

CACHE_DIR = DATA_DIR / "cache"

DEMO = [
    ("Elden Ring", "GCM", "Hexinton", "2026.06.19", 58.9, 12),
    ("Elden Ring Nightreign", "GCM", "Shina", "2026.07.02", 41.2, 15),
    ("Palworld", "GCM", "chenstack", "2026.07.16", 33.8, 26),
    ("黑神话：悟空", "小幸", "小幸", "2026.08.28", 22.4, 18),
    ("Cyberpunk 2077", "FLiNG", "FLiNG", "2026.06.30", 64.1, 21),
    ("Baldur's Gate 3", "CT", "Zanzer", "2026.05.30", 2.6, 9),
    ("Forza Horizon 6", "GCM", "Shina", "2026.07.23", 47.7, 14),
    ("Stardew Valley", "CT", "3DM", "2026.04.20", 1.8, 7),
    ("Monster Hunter Wilds", "GCM", "Hexinton", "2026.08.11", 52.3, 19),
    ("Kingdom Come: Deliverance II", "FLiNG", "FLiNG", "2026.05.12", 38.9, 11),
    ("Silent Hill f", "GCM", "Shina", "2026.09.02", 29.5, 8),
    ("Ghost of Tsushima", "小幸", "小幸", "2026.03.18", 19.7, 13),
    ("Red Dead Redemption 2", "FLiNG", "FLiNG", "2026.02.26", 71.4, 23),
    ("Satisfactory", "CT", "Zanzer", "2026.06.05", 3.1, 6),
    ("Dragon's Dogma 2", "GCM", "chenstack", "2026.04.09", 26.8, 10),
    ("Lies of P", "FLiNG", "FLiNG", "2026.01.30", 24.2, 12),
    ("Nier: Automata", "CT", "3DM", "2025.11.14", 1.4, 5),
    ("Hogwarts Legacy", "GCM", "Hexinton", "2026.07.08", 44.6, 16),
]


def _clean(text: str) -> str:
    """清掉旧库里被写坏的替换字符，避免界面出现 ���。"""
    return text.replace("\ufffd", "").strip() if "\ufffd" in text else text.strip()


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


# key -> (显示名, 抓取函数, 缓存 key)
SOURCES: dict[str, tuple[str, Callable[[], list[Trainer]], str]] = {
    "fling": ("FLiNG", fling.fetch_catalog, "fling"),
    "ct": ("CT", ct.fetch_catalog, "ct"),
    "xiaoxing": ("小幸", xiaoxing.fetch_catalog, "xiaoxing"),
}


class _SourceFetch(QThread):
    ready = pyqtSignal(str, list)
    failed = pyqtSignal(str, str)

    def __init__(self, key: str, fetch: Callable[[], list[Trainer]], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._key = key
        self._fetch = fetch
    def run(self) -> None:
        try:
            items = self._fetch()
            if items:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                _cache_path(self._key).write_text(
                    json.dumps([asdict(t) for t in items], ensure_ascii=False),
                    encoding="utf-8",
                )
            self.ready.emit(self._key, items)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(self._key, str(exc))


class Catalog(QObject):
    changed = pyqtSignal()
    status = pyqtSignal(str)

    def __init__(self, settings=None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._items: list[Trainer] = []
        self._legacy: list[Trainer] = []
        self._store: dict[str, list[Trainer]] = {}
        self._workers: dict[str, _SourceFetch] = {}
        self.source_desc = "内置演示数据"

    # ---------- 查询 ----------
    def items(self) -> list[Trainer]:
        return self._items

    def online_count(self) -> int:
        return sum(len(v) for v in self._store.values())

    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self._items:
            counts[item.source] = counts.get(item.source, 0) + 1
        return counts

    def enabled(self, key: str) -> bool:
        if self._settings is None:
            return True
        sources = self._settings.get("sources") or {}
        return bool(sources.get(key, True))

    # ---------- 载入 ----------
    def load(self) -> None:
        self._legacy = self._load_legacy()
        for key in SOURCES:
            cached = self._load_cache(key)
            if cached:
                self._store[key] = cached
        self._rebuild()
        self.changed.emit()

    def _rebuild(self) -> None:
        merged: dict[str, Trainer] = {}
        legacy_count = 0
        for item in self._legacy:
            if item.source in ("CT", "小幸") and not self._source_on_label(item.source):
                continue
            merged[self._key(item.name)] = item
            legacy_count += 1
        online = 0
        for key, (label, _fetch, _cache) in SOURCES.items():
            if not self.enabled(key):
                continue
            for item in self._store.get(key, []):
                online += 1
                slot = self._key(item.name)
                current = merged.get(slot)
                # 在线项能下载/能跳转，优先于旧库里同名但没地址的条目
                if current is None or (item.url and not current.url):
                    merged[slot] = item
        items = sorted(merged.values(), key=lambda t: t.name.lower())
        self._items = items
        parts = [f"旧库 {legacy_count} 条"]
        for key, (label, _f, _c) in SOURCES.items():
            if self.enabled(key) and self._store.get(key):
                parts.append(f"{label} {len(self._store[key])} 条")
        self.source_desc = " · ".join(parts) if online or legacy_count else "内置演示数据"
        if not items:
            self._items = self._load_demo()

    @staticmethod
    def _key(name: str) -> str:
        return re.sub(r"\s+", " ", name).strip().lower()

    def _source_on_label(self, label: str) -> bool:
        for key, (name, _f, _c) in SOURCES.items():
            if name == label:
                return self.enabled(key)
        return True

    # ---------- 在线刷新 ----------
    def _fetcher(self, key: str) -> Callable[[], list[Trainer]]:
        """把设置里的站点地址（镜像/反代）绑进抓取函数。"""
        fetch = SOURCES[key][1]
        base = ""
        if self._settings is not None:
            base = str((self._settings.get("sourceUrls") or {}).get(key) or "")
        if not base:
            return fetch
        return lambda: fetch(base=base)

    def refresh_online(self, force: bool = False) -> None:
        started = 0
        for key, (label, fetch, _cache) in SOURCES.items():
            if not self.enabled(key):
                continue
            worker = self._workers.get(key)
            if worker is not None and worker.isRunning():
                continue
            if not force and self._store.get(key):
                continue
            worker = _SourceFetch(key, self._fetcher(key), self)
            worker.ready.connect(self._on_ready)
            worker.failed.connect(self._on_failed)
            self._workers[key] = worker
            worker.start()
            started += 1
        if started:
            names = "、".join(SOURCES[k][0] for k in SOURCES if self.enabled(k))
            self.status.emit(f"正在抓取 {names} 索引…")

    def _on_ready(self, key: str, items: list[Trainer]) -> None:
        label = SOURCES.get(key, (key,))[0]
        self._store[key] = items
        self._rebuild()
        self.status.emit(f"{label} 索引已更新：{len(items)} 条")
        self.changed.emit()

    def _on_failed(self, key: str, message: str) -> None:
        label = SOURCES.get(key, (key,))[0]
        self.status.emit(f"{label} 抓取失败：{message}")

    def reapply_sources(self) -> None:
        """设置页改了数据源开关后重新合并（不重新抓取）。"""
        self._rebuild()
        self.changed.emit()

    # ---------- 缓存与旧库 ----------
    def _load_cache(self, key: str) -> list[Trainer]:
        path = _cache_path(key)
        if not path.is_file():
            return []
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
        items: list[Trainer] = []
        for row in rows:
            try:
                source = row.get("source", SOURCES.get(key, ("",))[0])
                desc = row.get("desc", "")
                name_zh = row.get("name_zh", "")
                # 小幸的标题本来就是「中文 / English」，desc 里就是中文名；
                # 老缓存没有 name_zh 字段，这里补一下，中文搜索才能命中
                if not name_zh and source == "小幸" and _CJK.search(desc or ""):
                    name_zh = desc
                items.append(
                    Trainer(
                        name=row["name"],
                        source=source,
                        author=row.get("author", ""),
                        version=row.get("version", ""),
                        kind="catalog",
                        installed=False,
                        updated=float(row.get("updated") or 0.0),
                        desc=desc,
                        url=row.get("url", ""),
                        external=bool(row.get("external") or False),
                        name_zh=name_zh,
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return items

    def _load_legacy(self) -> list[Trainer]:
        db = Path(LEGACY_DB_DIR) / "gcm_trainers.json"
        if not db.is_file():
            return []
        try:
            raw = db.read_text(encoding="utf-8", errors="replace")
            data = json.loads(raw, strict=False)
        except Exception:
            return []
        rows = data if isinstance(data, list) else data.get("trainers", [])
        items: list[Trainer] = []
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("custom_name_zh") or row.get("game_name") or "").strip()
            name = _clean(re.sub(r"\s*修改器$", "", name))
            if not name or name.lower() == "none" or name in seen:
                continue
            seen.add(name)
            origin = str(row.get("origin", "")).lower()
            url = str(row.get("official_url") or "")
            desc = url if url.startswith("http") else ""
            author = _clean(str(row.get("author", "") or ""))
            items.append(
                Trainer(
                    name=name,
                    source=ORIGIN_MAP.get(origin, "GCM"),
                    author=author,
                    version=str(row.get("version", "") or ""),
                    kind="catalog",
                    installed=False,
                    desc=desc,
                    url=url if url.startswith("http") else "",
                    external=bool(url.startswith("http")),
                )
            )
        return items

    def _load_demo(self) -> list[Trainer]:
        return [
            Trainer(
                name=name,
                source=source,
                author=author,
                version=version,
                kind="catalog",
                size_mb=size,
                launched=uses,
                installed=False,
            )
            for name, source, author, version, size, uses in DEMO
        ]
