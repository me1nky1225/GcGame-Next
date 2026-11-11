"""后台补全 Steam 中文名与封面。

界面只在需要时才排队（列表可见行、以及中文搜索兜底），线程里串行请求、
每个游戏只查一次，结果进磁盘缓存，所以第二次打开就完全离线。
"""
from __future__ import annotations

import queue
import time

from PyQt6.QtCore import QThread, pyqtSignal

from .steam import SteamStore

THROTTLE = 0.18  # 秒；Steam 的 storesearch 对频率比较敏感


class SteamEnricher(QThread):
    enriched = pyqtSignal(str, object)  # 查询用的名字 → {appid, en, zh, cover, cover_path}
    queryResolved = pyqtSignal(str, object)  # 中文搜索词 → 命中的条目（可能为 None）

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.store = SteamStore()
        self._queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._urgent: queue.Queue[tuple[str, str]] = queue.Queue()
        self._seen: set[str] = set()
        self._running = True

    # ---------- 对外 ----------
    def request(self, name: str, *, urgent: bool = False) -> None:
        key = name.strip().lower()
        if not key or key in self._seen:
            return
        cached = self.store.get(name)
        if cached:
            self._seen.add(key)
            self.enriched.emit(name, self._finish(cached))
            return
        self._seen.add(key)
        (self._urgent if urgent else self._queue).put(("name", name))

    def request_query(self, query: str) -> None:
        self._urgent.put(("query", query))

    def warm(self, names: list[str], limit: int = 300) -> int:
        """后台批量补全（按列表顺序），给中文搜索攒词表。返回入队数量。"""
        added = 0
        for name in names:
            if added >= limit:
                break
            key = name.strip().lower()
            if not key or key in self._seen:
                continue
            if self.store.get(name):
                continue
            self._seen.add(key)
            self._queue.put(("name", name))
            added += 1
        return added

    def busy(self) -> int:
        return self._queue.qsize()

    def has_cached(self, name: str) -> dict | None:
        return self.store.get(name)

    def stop(self) -> None:
        self._running = False
        self._queue.put(("", ""))

    # ---------- 线程体 ----------
    def run(self) -> None:
        pending_writes = 0
        while self._running:
            try:
                kind, payload = self._urgent.get_nowait()
            except queue.Empty:
                kind, payload = "", ""
            try:
                if not kind:
                    kind, payload = self._queue.get(timeout=0.5)
            except queue.Empty:
                if pending_writes:
                    self.store.save()
                    pending_writes = 0
                continue
            if not self._running:
                break
            if kind == "name":
                entry = self.store.lookup(payload)
                if entry:
                    self.enriched.emit(payload, self._finish(entry))
                    pending_writes += 1
            elif kind == "query":
                entry = self.store.lookup(payload, chinese=True)
                if entry:
                    self.queryResolved.emit(payload, self._finish(entry))
                    pending_writes += 1
                else:
                    self.queryResolved.emit(payload, None)
            if pending_writes >= 8:
                self.store.save()
                pending_writes = 0
            time.sleep(THROTTLE)
        self.store.save()

    def _finish(self, entry: dict) -> dict:
        done = dict(entry)
        done["cover_path"] = self.store.cover_file(entry)
        return done
