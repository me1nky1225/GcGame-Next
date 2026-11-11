"""最小 HTTP 层：统一 UA / Referer / Cookie / 重定向，够下载器和抓取用。"""
from __future__ import annotations

import gzip
import http.cookiejar
import urllib.error
import urllib.parse
import urllib.request

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

_OPENER: urllib.request.OpenerDirector | None = None
_COOKIES: http.cookiejar.CookieJar | None = None


def opener() -> urllib.request.OpenerDirector:
    global _OPENER, _COOKIES
    if _OPENER is None:
        _COOKIES = http.cookiejar.CookieJar()
        _OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_COOKIES))
    return _OPENER


def request(
    url: str,
    referer: str = "",
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
    method: str = "GET",
) -> urllib.response.addinfourl:
    req = urllib.request.Request(url, method=method)
    req.add_header("User-Agent", UA)
    req.add_header("Accept", "*/*")
    req.add_header("Accept-Language", "en-US,en;q=0.9,zh-CN;q=0.8")
    if referer:
        req.add_header("Referer", referer)
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    return opener().open(req, timeout=timeout)


def get_text(url: str, referer: str = "", timeout: float = 30.0, encoding: str = "utf-8") -> str:
    with request(url, referer=referer, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return raw.decode(encoding, "replace")


def get_bytes(url: str, referer: str = "", timeout: float = 30.0) -> bytes:
    with request(url, referer=referer, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return raw


def quote(text: str) -> str:
    return urllib.parse.quote(text, safe="")


def content_length(url: str, referer: str = "", timeout: float = 20.0) -> int:
    """拿到最终跳转后的大小；拿不到返回 0。"""
    try:
        with request(url, referer=referer, timeout=timeout) as resp:
            return int(resp.headers.get("Content-Length") or 0)
    except (urllib.error.URLError, OSError, ValueError):
        return 0


def filename_from_headers(headers, url: str = "") -> str:
    """从 Content-Disposition 或 URL 末尾猜文件名。"""
    disp = headers.get("Content-Disposition") or ""
    marker = "filename*="
    if marker in disp:
        part = disp.split(marker, 1)[1].split(";")[0].strip().strip('"')
        if "''" in part:
            part = part.split("''", 1)[1]
        return urllib.parse.unquote(part)
    if "filename=" in disp:
        return disp.split("filename=", 1)[1].split(";")[0].strip().strip('"')
    name = urllib.parse.unquote(urllib.parse.urlparse(url).path.rsplit("/", 1)[-1])
    return name or "download.bin"
