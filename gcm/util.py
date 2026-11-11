"""通用小工具：时间、体积、文本。"""
from __future__ import annotations

import time

from .i18n import t


def humanize(ts: float) -> str:
    if not ts:
        return t("从未")
    delta = max(0.0, time.time() - ts)
    if delta < 90:
        return t("刚刚")
    if delta < 3600:
        return t("{n} 分钟前").format(n=int(delta // 60))
    if delta < 86400:
        return t("{n} 小时前").format(n=int(delta // 3600))
    if delta < 86400 * 30:
        return t("{n} 天前").format(n=int(delta // 86400))
    if delta < 86400 * 365:
        return t("{n} 个月前").format(n=int(delta // (86400 * 30)))
    return time.strftime("%Y-%m-%d", time.localtime(ts))


def fmt_size(mb: float) -> str:
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb:.1f} MB"


def initials(name: str) -> str:
    """封面占位字：中文取首字，英文取前两个词首字母。"""
    text = name.strip()
    if not text:
        return "?"
    if any("\u4e00" <= ch <= "\u9fff" for ch in text[:1]):
        return text[0]
    words = [w for w in text.replace("-", " ").replace("_", " ").split() if w]
    if not words:
        return text[0].upper()
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()
