"""FLiNG 在线源：抓 all-trainers 索引，解析到直接下载链接。

之所以单独做一条：GCM 自家下载走 signed URL（需要他们的服务端签名），
FLiNG 站点的下载是公开的，只要带 Referer 就能直连，适合做真实下载链路的样板。
"""
from __future__ import annotations

import re

from ...net.http import UA, get_text
from ..trainer import Trainer

INDEX_URL = "https://flingtrainer.com/all-trainers/"
BASE = "https://flingtrainer.com"

_ENTRY = re.compile(
    r'href="(https?://[^"/]+/trainer/[^"#?]+)"[^>]*>(.*?)</a>',
    re.S,
)
_DOWNLOAD = re.compile(r'href="(https?://[^"]+/downloads/[^"#?]+)"')
_TAGS = re.compile(r"<[^>]+>")


def _clean_text(raw: str) -> str:
    text = _TAGS.sub(" ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    return text.removesuffix(" Trainer").strip()


def _base_url(base: str = "") -> str:
    return (base or BASE).rstrip("/")


def fetch_catalog(base: str = "", timeout: float = 25.0) -> list[Trainer]:
    """返回 FLiNG 索引里的全部修改器（只带名称与页面地址）。

    `base` 可在设置里改成镜像站，默认 https://flingtrainer.com。
    """
    root = _base_url(base)
    html = get_text(f"{root}/all-trainers/", timeout=timeout)
    seen: set[str] = set()
    items: list[Trainer] = []
    for match in _ENTRY.finditer(html):
        url, raw_text = match.group(1), match.group(2)
        name = _clean_text(raw_text)
        if not name or name in seen:
            continue
        seen.add(name)
        items.append(
            Trainer(
                name=name,
                source="FLiNG",
                author="FLiNG",
                kind="catalog",
                installed=False,
                desc=url,
                url=url,
            )
        )
    return items


def resolve_download(page_url: str, timeout: float = 25.0) -> str:
    """从训练器页面取第一个下载链接（第一个通常是当前版本）。"""
    html = get_text(page_url, referer=_base_url(page_url) + "/", timeout=timeout)
    match = _DOWNLOAD.search(html)
    if not match:
        raise RuntimeError("页面上没有找到下载链接")
    return match.group(1)


def download_headers(page_url: str) -> dict[str, str]:
    return {
        "User-Agent": UA,
        "Referer": page_url or BASE + "/",
        "Accept": "application/octet-stream,*/*",
    }
