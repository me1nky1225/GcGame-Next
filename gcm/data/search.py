"""搜索匹配：子串 + 拼音首字母 + 模糊。"""
from __future__ import annotations

from functools import lru_cache

from pypinyin import Style, lazy_pinyin
from rapidfuzz import fuzz


@lru_cache(maxsize=16384)
def initials(text: str) -> str:
    try:
        parts = lazy_pinyin(text, style=Style.FIRST_LETTER, errors=lambda x: [x])
    except Exception:
        return ""
    return "".join(ch for ch in "".join(parts).lower() if ch.isalnum())


@lru_cache(maxsize=16384)
def haystack(name: str, extra: str) -> tuple[str, str]:
    flat = f"{name} {extra}".lower()
    return flat, initials(name)


def matches(query: str, name: str, extra: str = "") -> bool:
    q = (query or "").strip().lower().replace(" ", "")
    if not q:
        return True
    flat, ini = haystack(name, extra)
    compact = flat.replace(" ", "")
    if q in compact or (ini and q in ini):
        return True
    if len(q) >= 3:
        return fuzz.partial_ratio(q, compact) >= 82
    return False
