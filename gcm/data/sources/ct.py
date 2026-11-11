"""the-cheat-script 在线源（CT）。

站点是 Blogger：
- 目录：`/feeds/posts/default?alt=json&max-results=N&start-index=M`，一次最多 150 条，
  返回 title / published / alternate link，比爬 sitemap 高效得多（全站 2200+ 条）。
- 下载：文章正文里放的是 Yandex Disk 公共链接，走
  `cloud-api.yandex.net/v1/disk/public/resources/download?public_key=...`
  就能换到带签名的直链（必须带 UA，否则 429），直链里含 `.CT` 文件名。
"""
from __future__ import annotations

import html as html_lib
import json
import re
import time
import urllib.error
import urllib.parse
from datetime import datetime

from ...net.http import UA, get_text, request
from ..trainer import Trainer

BASE = "https://www.thecheatscript.com"
FEED = BASE + "/feeds/posts/default"
PAGE_SIZE = 150

# "Thank You For Your Application v1.2.1 | Cheat Engine Table v2.0"
_TITLE_SUFFIX = re.compile(r"\s*[|｜].*$")
_VERSION = re.compile(r"\bv?(\d+(?:\.\d+){1,3})\b")
_YANDEX = re.compile(
    r"https?://(?:disk\.yandex\.(?:com|ru)|yadi\.sk)/d/[A-Za-z0-9_\-]+", re.I
)
_YADEX_API = "https://cloud-api.yandex.net/v1/disk/public/resources/download"


def _clean_title(raw: str) -> tuple[str, str]:
    """返回 (游戏名, 版本)。"""
    title = html_lib.unescape(raw).strip()
    title = _TITLE_SUFFIX.sub("", title).strip()
    version = ""
    match = _VERSION.search(title)
    if match:
        version = match.group(1)
        title = (title[: match.start()] + title[match.end() :]).strip(" -–—")
    return re.sub(r"\s+", " ", title).strip(), version


def _timestamp(text: str) -> float:
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def fetch_catalog(pages: int = 16, timeout: float = 30.0, base: str = "") -> list[Trainer]:
    """抓取博客文章列表（默认最多 16×150 = 2400 条，够覆盖全站）。

    `base` 可在设置里改成镜像/反代地址，默认 https://www.thecheatscript.com。
    """
    feed = (base or BASE).rstrip("/") + "/feeds/posts/default"
    items: list[Trainer] = []
    seen: set[str] = set()
    for page in range(pages):
        start = page * PAGE_SIZE + 1
        url = f"{feed}?alt=json&max-results={PAGE_SIZE}&start-index={start}"
        try:
            raw = get_text(url, timeout=timeout, encoding="utf-8")
            data = json.loads(raw)
        except (ValueError, OSError):
            break
        entries = data.get("feed", {}).get("entry", [])
        if not entries:
            break
        for entry in entries:
            raw_title = entry.get("title", {}).get("$t", "")
            link = ""
            for candidate in entry.get("link", []):
                if candidate.get("rel") == "alternate":
                    link = candidate.get("href", "")
                    break
            if not link:
                continue
            name, version = _clean_title(raw_title)
            if not name or name in seen:
                continue
            seen.add(name)
            items.append(
                Trainer(
                    name=name,
                    source="CT",
                    author="ColonelRVH",
                    version=version,
                    kind="catalog",
                    installed=False,
                    updated=_timestamp(entry.get("published", {}).get("$t", "")),
                    desc=link,
                    url=link,
                )
            )
    if not items:
        raise RuntimeError("CT 目录为空（可能被限流）")
    return items


def resolve_download(page_url: str, timeout: float = 30.0) -> str:
    """文章页 → Yandex 公共链接 → 直链。

    Yandex 的公共资源接口对无 Referer 的请求比较敏感，偶尔直接回 429，
    所以带 Referer + 有限次退避重试。
    """
    html = get_text(page_url, timeout=timeout)
    match = _YANDEX.search(html)
    if not match:
        raise RuntimeError("文章里没有找到 Yandex 网盘链接")
    public_key = urllib.parse.quote(match.group(0), safe="")
    api = f"{_YADEX_API}?public_key={public_key}"
    last = ""
    for attempt in range(3):
        try:
            with request(
                api,
                referer="https://disk.yandex.com/",
                headers={"Accept": "application/json"},
                timeout=timeout,
            ) as resp:
                payload = json.loads(resp.read().decode("utf-8", "replace"))
            href = payload.get("href") or ""
            if href:
                return href
            last = payload.get("description") or payload.get("error") or "没有返回直链"
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}"
            if exc.code != 429:
                break
        except (OSError, ValueError) as exc:
            last = str(exc)
        time.sleep(1.5 + attempt * 2.0)
    if "429" in last:
        raise RuntimeError("Yandex 网盘接口限流（429），过几分钟再试，或点「详情」打开官方页面")
    raise RuntimeError(f"Yandex 没有返回直链：{last}")


def file_hint(page_url: str, timeout: float = 30.0) -> str:
    """直链里带 filename=...，用它在下载前就知道扩展名。"""
    match = re.search(r"[?&]filename=([^&]+)", page_url)
    if not match:
        return ""
    return urllib.parse.unquote(match.group(1))


def download_headers(page_url: str) -> dict[str, str]:
    return {
        "User-Agent": UA,
        "Referer": page_url or BASE + "/",
        "Accept": "*/*",
    }
