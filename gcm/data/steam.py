"""Steam 商店查询：给英文名的修改器补上中文名、AppID 和封面图。

两个公开接口（都不需要 key）：
- `api/storesearch` 按名字搜 appid，`l=schinese&cc=cn` 时返回中文名；
- `api/appdetails` 按 appid 取详情，`l=english` 拿英文名、`header_image` 拿封面。

查询结果按「小写英文名」缓存到 `DATA_DIR/cache/steam.json`，封面图缓存到
`DATA_DIR/covers/<appid>.jpg`，所以同一款游戏只会联网一次。
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from ..net import http
from ..paths import DATA_DIR

SEARCH_API = "https://store.steampowered.com/api/storesearch/"
DETAIL_API = "https://store.steampowered.com/api/appdetails"
CACHE_DIR = DATA_DIR / "cache"
COVER_DIR = DATA_DIR / "covers"
CACHE_FILE = CACHE_DIR / "steam.json"
# 随包带一份热门游戏的中英名对照，首次运行就能用中文搜到（不用先联网）
SEED_FILE = Path(__file__).with_name("steam_seed.json")

# 主标题里这些词不参与匹配，避免 "Black Myth: Wukong Deluxe Edition" 之类误伤
_NOISE = re.compile(r"\b(deluxe|ultimate|premium|edition|definitive|complete)\b", re.I)
class _NetError(RuntimeError):
    """Steam 接口连不上/超时——区别于「查到了但没有这个游戏」。"""


_CJK = re.compile(r"[\u3400-\u9fff]")
MISS_TTL = 6 * 3600  # 查不到的记录 6 小时内不再重试


def _key(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().lower()


def _terms(name: str) -> list[str]:
    """同一款游戏常有各种后缀，按「原名 → 去括号 → 去副标题」依次试。"""
    base = re.sub(r"\s+", " ", name).strip()
    out: list[str] = [base]
    trimmed = re.sub(r"[（(][^）)]*[）)]", "", base).strip()
    if trimmed and trimmed != base:
        out.append(trimmed)
    for sep in ("：", ":", " — ", " - "):
        if sep in base:
            head = base.split(sep)[0].strip()
            if len(head) >= 2 and head not in out:
                out.append(head)
    return [t for t in out if t]


class SteamStore:
    """带磁盘缓存的 Steam 查询器（同步，调用方负责放到线程里）。"""

    def __init__(self) -> None:
        self._data: dict[str, dict] = {}
        self._load()

    # ---------- 缓存 ----------
    def _load(self) -> None:
        self._data = {}
        if CACHE_FILE.is_file():
            try:
                self._data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}
        # 内置种子只补缺，不覆盖用户已经联网拿到的结果
        if SEED_FILE.is_file():
            try:
                seed = json.loads(SEED_FILE.read_text(encoding="utf-8"))
            except Exception:
                seed = {}
            for key, entry in seed.items():
                if key not in self._data:
                    self._data[key] = entry

    def save(self) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    def get(self, name: str) -> dict | None:
        return self._data.get(_key(name))

    def seed_entries(self) -> list[dict]:
        """内置热门游戏条目（不含 miss 标记），启动时批量写回列表。"""
        return [v for v in self._data.values() if v.get("appid")]

    def store(self, name_en: str, entry: dict) -> None:
        self._data[_key(name_en)] = entry
        if entry.get("zh"):
            # 中文名也建一条索引，中文查询可以直接命中
            self._data[_key(entry["zh"])] = entry

    # ---------- 网络 ----------
    def lookup(self, name: str, *, chinese: bool = False) -> dict | None:
        """按名字查一次：返回 {appid, en, zh, cover}。

        `chinese=True` 表示传进来的是中文名，先用中文搜索拿 appid，再补英文名。
        不传时按名字里有没有汉字自动判断。
        """
        cached = self.get(name)
        if cached:
            if cached.get("miss"):
                # 上次没查到时先别急着再打一次，Steam 这边经常超时
                age = time.time() - float(cached.get("at") or 0)
                return None if age < MISS_TTL else cached
            return cached
        if not chinese and _CJK.search(name):
            chinese = True
        appid, title = 0, ""
        network_error = False
        for term in _terms(name):
            try:
                got, title_got = self._search(term, chinese)
            except _NetError:
                network_error = True
                break
            if got:
                appid, title = got, title_got
                break
        if not appid:
            # 网络超时不要写成 miss，否则这台机器一次超时就要等 6 小时
            if not network_error:
                self._data[_key(name)] = {"miss": True, "at": int(time.time())}
            return None
        try:
            entry = self._detail(appid, title, chinese)
        except _NetError:
            # 拿不到详情就当这次没查到，但别写进 miss 缓存
            return None
        if entry:
            self.store(entry["en"] or title, entry)
            self.store(name, entry)
        return entry

    def _search(self, term: str, chinese: bool) -> tuple[int, str]:
        lang, cc = ("schinese", "cn") if chinese else ("english", "us")
        url = f"{SEARCH_API}?term={http.quote(term)}&l={lang}&cc={cc}"
        payload = self._get_json(url)
        items = (payload or {}).get("items") or []
        if not items:
            # 中文搜不到时退一步用英文搜（名字本身就是英文的条目）
            if not chinese:
                return 0, ""
            return self._search(term, False)
        best = self._pick(items, term)
        return int(best.get("id") or 0), str(best.get("name") or "")

    @staticmethod
    def _get_json(url: str, attempts: int = 2) -> dict | None:
        """Steam 的接口偶尔整段超时，重试一次再放弃（放弃时抛 _NetError）。"""
        for i in range(attempts):
            try:
                return json.loads(http.get_text(url, timeout=8.0))
            except Exception:
                if i + 1 < attempts:
                    time.sleep(1.0)
        raise _NetError(url)

    @staticmethod
    def _pick(items: list[dict], term: str) -> dict:
        """同名优先，其次去掉 Deluxe/Ultimate 这类后缀再比。"""
        want = _NOISE.sub("", _key(term)).strip(" :-")
        for item in items:
            if _key(str(item.get("name", ""))) == _key(term):
                return item
        for item in items:
            got = _NOISE.sub("", _key(str(item.get("name", "")))).strip(" :-")
            if got == want:
                return item
        # 官方游戏优先于 DLC/测试工具：有 price 字段的通常就是本体
        for item in items:
            if item.get("price"):
                return item
        return items[0]

    def _detail(self, appid: int, fallback_name: str, chinese: bool) -> dict | None:
        # 用「另一种语言」取详情：中文入口就取英文名，英文入口就取中文名
        lang, cc = ("english", "us") if chinese else ("schinese", "cn")
        data = self._appdata(appid, lang, cc)
        if not data:
            return None
        cover = str(data.get("header_image") or data.get("capsule_image") or "")
        entry = {"appid": appid, "cover": cover, "at": int(time.time())}
        if chinese:
            entry["zh"] = fallback_name
            entry["en"] = str(data.get("name") or fallback_name)
        else:
            entry["en"] = fallback_name
            entry["zh"] = str(data.get("name") or "")
        return entry

    @staticmethod
    def _appdata(appid: int, lang: str, cc: str) -> dict | None:
        payload = SteamStore._get_json(f"{DETAIL_API}?appids={appid}&l={lang}&cc={cc}")
        block = (payload or {}).get(str(appid)) or {}
        return block.get("data") if block.get("success") else None

    # ---------- 封面 ----------
    def cached_cover(self, entry: dict) -> str:
        """已经下载过的封面（不发网络请求）。"""
        appid = int(entry.get("appid") or 0)
        if not appid:
            return ""
        target = COVER_DIR / f"{appid}.jpg"
        if target.is_file() and target.stat().st_size > 512:
            return str(target)
        return ""

    def cover_file(self, entry: dict) -> str:
        """下载封面并返回本地路径；失败返回空串。"""
        appid = int(entry.get("appid") or 0)
        if not appid:
            return ""
        target = COVER_DIR / f"{appid}.jpg"
        if target.is_file() and target.stat().st_size > 512:
            return str(target)
        url = str(entry.get("cover") or "")
        if not url:
            return ""
        try:
            raw = http.get_bytes(url, timeout=25.0)
        except Exception:
            return ""
        if len(raw) < 512:
            return ""
        COVER_DIR.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        return str(target)
