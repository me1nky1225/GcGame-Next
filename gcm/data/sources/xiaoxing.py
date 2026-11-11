"""小幸（xiaoxingjie.com）在线源。

站点是 WordPress，走 REST API 最稳：
`/wp-json/wp/v2/posts?per_page=100&page=N` 返回 title / link / modified，
文章标题形如「黑神话：悟空 多功能修改器 V1.7.0  /  Black Myth: Wukong Trainer」。

下载：文章里的直链是 MediaFire / 百度网盘，MediaFire 对非浏览器请求返回 403，
百度网盘要登录。所以这个源定位为「目录 + 一键打开官方页面」，不假装能下。
"""
from __future__ import annotations

import html as html_lib
import json
import re
from datetime import datetime

from ...net.http import get_text, request
from ..trainer import Trainer

BASE = "https://www.xiaoxingjie.com"
API = BASE + "/wp-json/wp/v2/posts"
PER_PAGE = 100

_ADDON = re.compile(r"(多功能)?(修改器|作弊器|助手)")
_VERSION = re.compile(r"[Vv](\d+(?:\.\d+){1,3})")
_SLASH = re.compile(r"\s*[/|｜]\s*")


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(value)).strip()


def _parse_title(raw: str) -> tuple[str, str, str]:
    """返回 (显示名, 中文名, 版本)。显示名优先用英文名，缺失时用中文名。"""
    title = _clean(raw)
    parts = [p for p in _SLASH.split(title) if p]
    chinese = parts[0] if parts else title
    english = parts[1] if len(parts) > 1 else ""
    english = re.sub(r"\s*Trainer\s*$", "", english, flags=re.I).strip()
    version = ""
    match = _VERSION.search(title)
    if match:
        version = match.group(1)
    chinese = _VERSION.sub("", chinese)
    chinese = _ADDON.sub("", chinese).strip(" -–—")
    name = english or chinese
    if not name:
        name = title
    return name, chinese, version


def _timestamp(text: str) -> float:
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return 0.0


def fetch_catalog(max_pages: int = 6, timeout: float = 30.0, base: str = "") -> list[Trainer]:
    """按 WordPress REST 分页抓文章；`base` 可在设置里改镜像地址。"""
    api = (base or BASE).rstrip("/") + "/wp-json/wp/v2/posts"
    items: list[Trainer] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        url = f"{api}?per_page={PER_PAGE}&page={page}&_fields=title,link,modified"
        try:
            with request(url, timeout=timeout, headers={"Accept": "application/json"}) as resp:
                total_pages = int(resp.headers.get("X-WP-TotalPages") or 1)
                payload = json.loads(resp.read().decode("utf-8", "replace"))
        except (ValueError, OSError):
            break
        if not payload:
            break
        for post in payload:
            name, chinese, version = _parse_title(post.get("title", {}).get("rendered", ""))
            link = post.get("link", "")
            if not name or not link or name in seen:
                continue
            seen.add(name)
            items.append(
                Trainer(
                    name=name,
                    source="小幸",
                    author="xiaoxing",
                    version=version,
                    kind="catalog",
                    installed=False,
                    updated=_timestamp(post.get("modified", "")),
                    desc=chinese or link,
                    name_zh=chinese,
                    url=link,
                    external=True,
                )
            )
        if page >= total_pages:
            break
    if not items:
        raise RuntimeError("小幸目录为空（接口可能变了）")
    return items


def download_headers(page_url: str) -> dict[str, str]:
    return {"Referer": page_url or BASE + "/", "Accept": "text/html,*/*"}
