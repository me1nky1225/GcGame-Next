"""真实下载引擎：解析地址 → 断点续传 → 安装。

一个任务一个 QThread。暂停 = 断开连接并保留 .part，恢复时用 Range 续传；
取消 = 删掉 .part。暂停/恢复靠重新发起请求实现，避免长连接空转超时。
"""
from __future__ import annotations

import shutil
import threading
import time
import urllib.error
import urllib.parse
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from ..i18n import t
from ..net import http
from . import installer
from .sources import ct, fling
from .trainer import Trainer

CHUNK = 256 * 1024
MB = 1024 * 1024
MAX_ATTEMPTS = 3


class _Paused(Exception):
    """暂停：保留已下载部分，等恢复。"""


class _Cancelled(Exception):
    """取消：删掉临时文件。"""


class DownloadJob(QThread):
    progressed = pyqtSignal(str, float, float, float)  # tid, done_mb, total_mb, speed_mb
    stage = pyqtSignal(str, str)  # tid, 状态文案
    finished_ok = pyqtSignal(str, str)  # tid, 安装目录
    failed = pyqtSignal(str, str)  # tid, 错误信息
    cancelled = pyqtSignal(str)  # tid

    def __init__(self, tid: str, trainer: Trainer, download_dir: Path, temp_dir: Path) -> None:
        super().__init__()
        self.tid = tid
        self.trainer = trainer
        self.download_dir = download_dir
        self.temp_dir = temp_dir
        self._pause = threading.Event()
        self._cancel = threading.Event()
        self._done_bytes = 0
        self._total_bytes = 0
        self._suffix_hint = ""

    # ---------- 外部控制 ----------
    def pause(self) -> None:
        self._pause.set()

    def resume(self) -> None:
        self._pause.clear()

    def cancel(self) -> None:
        self._cancel.set()
        self._pause.clear()

    @property
    def paused(self) -> bool:
        return self._pause.is_set()

    # ---------- 主流程 ----------
    def run(self) -> None:
        try:
            self.stage.emit(self.tid, t("解析下载地址…"))
            url, referer = self._resolve()
            payload = self._fetch(url, referer)
            if payload is None:
                self.cancelled.emit(self.tid)
                return
            self.stage.emit(self.tid, t("安装中…"))
            target = installer.install(payload, self.trainer, self.download_dir)
            self.finished_ok.emit(self.tid, str(target))
        except _Cancelled:
            self.cancelled.emit(self.tid)
        except _Paused:
            self.stage.emit(self.tid, t("已暂停"))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(self.tid, str(exc) or exc.__class__.__name__)

    def _resolve(self) -> tuple[str, str]:
        url = (self.trainer.url or "").strip()
        if not url:
            raise RuntimeError("这条记录没有可下载地址（GCM 源需要他们的签名服务）")
        if self.trainer.external:
            raise RuntimeError("这条来源只提供官方网页，请在浏览器里下载")
        if "flingtrainer.com/trainer/" in url:
            self.stage.emit(self.tid, t("读取 FLiNG 页面…"))
            return fling.resolve_download(url), url
        if "thecheatscript.com" in url:
            self.stage.emit(self.tid, t("读取 CT 页面…"))
            return ct.resolve_download(url), url
        return url, ""

    def _headers(self, referer: str) -> dict[str, str]:
        if "flingtrainer.com" in referer:
            return fling.download_headers(referer)
        if "thecheatscript.com" in referer or "yandex" in referer:
            return ct.download_headers(referer)
        return {}

    # ---------- 下载 ----------
    def _fetch(self, url: str, referer: str) -> Path | None:
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        headers = self._headers(referer)
        stem = installer.safe_folder_name(self.trainer.name)
        part = self.temp_dir / f"{stem}.part"

        attempts = 0
        while True:
            if self._cancel.is_set():
                part.unlink(missing_ok=True)
                raise _Cancelled
            # 上一次请求把文件下完才断的：直接收尾，别再发 Range 被拒
            if part.exists() and self._total_bytes and part.stat().st_size >= self._total_bytes:
                return self._finalize(part, stem)
            try:
                return self._stream(url, referer, headers, part, stem)
            except _Paused:
                self.stage.emit(self.tid, t("已暂停"))
                while self._pause.is_set() and not self._cancel.is_set():
                    time.sleep(0.2)
                if self._cancel.is_set():
                    part.unlink(missing_ok=True)
                    raise _Cancelled
                self.stage.emit(self.tid, t("继续下载…"))
                continue
            except _Cancelled:
                part.unlink(missing_ok=True)
                raise
            except urllib.error.HTTPError as exc:
                if exc.code == 416:
                    if self._suffix_hint and part.exists() and part.stat().st_size > 0:
                        return self._finalize(part, stem)
                    # 没有后缀信息就别猜，从头再来
                    part.unlink(missing_ok=True)
                    self._total_bytes = 0
                    continue
                if exc.code in (403, 404):
                    raise RuntimeError(f"下载失败：HTTP {exc.code}（来源可能已失效）") from exc
                attempts += 1
                if attempts >= MAX_ATTEMPTS:
                    raise RuntimeError(f"下载失败：HTTP {exc.code}") from exc
                self.stage.emit(
                self.tid,
                t("HTTP {code}，重试 {a}/{b}…").format(
                    code=exc.code, a=attempts, b=MAX_ATTEMPTS - 1
                ),
            )
                time.sleep(1.2 * attempts)
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                attempts += 1
                if attempts >= MAX_ATTEMPTS:
                    raise RuntimeError(f"下载失败：{exc}") from exc
                self.stage.emit(
                self.tid,
                t("连接中断，重试 {a}/{b}…").format(a=attempts, b=MAX_ATTEMPTS - 1),
            )
                time.sleep(1.2 * attempts)

    def _finalize(self, part: Path, stem: str) -> Path:
        final = self.temp_dir / (stem + (self._suffix_hint or ".bin"))
        _move(part, final)
        return final

    def _stream(
        self, url: str, referer: str, headers: dict[str, str], part: Path, stem: str
    ) -> Path:
        start = part.stat().st_size if part.exists() else 0
        request_headers = dict(headers)
        if start:
            request_headers["Range"] = f"bytes={start}-"

        resp = http.request(url, referer=referer, headers=request_headers, timeout=60)
        try:
            if start and getattr(resp, "status", 200) != 206:
                start = 0
                part.unlink(missing_ok=True)
            total = start + int(resp.headers.get("Content-Length") or 0)
            self._total_bytes = total
            self._done_bytes = start
            if total:
                self.progressed.emit(self.tid, start / MB, total / MB, 0.0)

            window: list[tuple[float, int]] = []
            with part.open("ab" if start else "wb") as fh:
                while True:
                    if self._cancel.is_set():
                        raise _Cancelled
                    if self._pause.is_set():
                        raise _Paused
                    chunk = resp.read(CHUNK)
                    if not chunk:
                        break
                    fh.write(chunk)
                    self._done_bytes += len(chunk)
                    now = time.monotonic()
                    window.append((now, self._done_bytes))
                    while len(window) > 2 and now - window[0][0] > 1.2:
                        window.pop(0)
                    span = window[-1][0] - window[0][0]
                    speed = (window[-1][1] - window[0][1]) / span / MB if span > 0.25 else 0.0
                    self.progressed.emit(
                        self.tid,
                        self._done_bytes / MB,
                        max(total, self._done_bytes) / MB,
                        speed,
                    )
            final = self.temp_dir / (stem + self._suffix(resp, url))
            self._suffix_hint = final.suffix
        finally:
            try:
                resp.close()
            except Exception:  # noqa: BLE001
                pass

        _move(part, final)
        return final

    def _suffix(self, resp, url: str) -> str:
        final_url = resp.geturl() or url
        name = http.filename_from_headers(resp.headers, final_url)
        suffix = Path(name).suffix.lower()
        if suffix in installer.ARCHIVE_EXTS or suffix in installer.EXEC_EXTS:
            return suffix
        # Yandex 直链把文件名放在 query 里：?filename=Foo.CT
        hint = ct.file_hint(final_url)
        if hint:
            hint_suffix = Path(hint).suffix.lower()
            if hint_suffix in installer.ARCHIVE_EXTS or hint_suffix in installer.EXEC_EXTS:
                return hint_suffix
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "zip" in ctype:
            return ".zip"
        if "7z" in ctype or "x-7z" in ctype:
            return ".7z"
        if "rar" in ctype:
            return ".rar"
        if "xml" in ctype:
            return ".ct"
        if "download" in ctype or "octet-stream" in ctype or "exe" in ctype:
            return ".exe"
        return suffix or ".bin"


def cleanup_temp(temp_dir: Path) -> None:
    shutil.rmtree(temp_dir, ignore_errors=True)


def _move(src: Path, dst: Path) -> None:
    """同一目录下改名，但 Roaming 目录可能被重定向到别的卷，失败就退化成复制。"""
    try:
        src.replace(dst)
    except OSError:
        shutil.move(str(src), str(dst))
