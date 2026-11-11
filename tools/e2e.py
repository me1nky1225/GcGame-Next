"""端到端验证：真实 FLiNG 下载 → 安装 → 出现在「我的修改器」，并验证暂停/续传。

用法：python tools/e2e.py [--keep]
"""
from __future__ import annotations

import io
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from gcm.bootstrap import build_context  # noqa: E402
from gcm.data.trainer import Trainer  # noqa: E402
from gcm.net import http  # noqa: E402
from gcm.ui.main_window import MainWindow  # noqa: E402

KEEP = "--keep" in sys.argv
app = QApplication([])
ctx = build_context(app)
win = MainWindow(ctx)
win.resize(1400, 900)
win.show()
app.processEvents()


def pump(seconds: float) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.02)


def wait_for(predicate, timeout: float, label: str) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        app.processEvents()
        time.sleep(0.05)
    print(f"TIMEOUT {label}")
    return False


# ---------- 1. 在线索引 ----------
print("抓取 FLiNG 索引…")
ctx.catalog.refresh_online()
ok = wait_for(lambda: ctx.catalog.online_count() > 0, 90, "fling index")
print(f"{'PASS' if ok else 'FAIL'} FLiNG 索引条数 = {ctx.catalog.online_count()}")
print(f"     在线库总计 = {len(ctx.catalog.items())}")

if not ok:
    sys.exit(1)

# ---------- 2. 挑一个体积小的条目 ----------
# 只有 FLiNG 的条目能直接下载；CT 走 Yandex（可能 429）、小幸只有网页
candidates = [
    t for t in ctx.catalog.items() if t.url and "flingtrainer.com" in t.url
][:14]
best: tuple[Trainer, int] | None = None
for item in candidates:
    try:
        from gcm.data.sources import fling

        direct = fling.resolve_download(item.url)
        size = http.content_length(direct, referer=item.url)
    except Exception as exc:  # noqa: BLE001
        print(f"  跳过 {item.name}: {exc}")
        continue
    if size and (best is None or size < best[1]):
        best = (item, size)
    if size and size < 12 * 1024 * 1024:
        break

if best is None:
    print("FAIL 没有可下载的条目")
    sys.exit(1)

item, size = best
print(f"选中小文件：{item.name} ({size / 1024 / 1024:.1f} MB)")

# ---------- 3. 真实下载并安装 ----------
win._acquire(item)
task = next((t for t in ctx.queue.tasks if t.name == item.name), None)
if task is None:
    print("FAIL 没有进入下载队列")
    sys.exit(1)
print(f"队列状态：{task.status}")

ok = wait_for(lambda: task.status in ("done", "failed"), 240, "download")
print(f"{'PASS' if task.status == 'done' else 'FAIL'} 下载+安装：{task.status} {task.error}")
if task.status != "done":
    sys.exit(1)

pump(0.5)
names = [t.name for t in ctx.installed.items()]
print(f"{'PASS' if item.name in names else 'FAIL'} 出现在已安装列表（共 {len(names)} 条）")
installed_dir = ctx.installed.directory() / item.name
print(f"     安装目录：{installed_dir}  exists={installed_dir.exists()}")

# ---------- 4. 暂停 / 续传（本地 Range 服务） ----------
PAYLOAD = os.urandom(6 * 1024 * 1024)


class RangeHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        rng = self.headers.get("Range")
        total = len(PAYLOAD)
        start = 0
        if rng and rng.startswith("bytes="):
            start = int(rng[6:].split("-")[0])
        body = PAYLOAD[start:]
        self.send_response(206 if start else 200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Accept-Ranges", "bytes")
        if start:
            self.send_header("Content-Range", f"bytes {start}-{total - 1}/{total}")
        self.end_headers()
        # 慢速发送，留出暂停时间窗
        step = 128 * 1024
        for i in range(0, len(body), step):
            try:
                self.wfile.write(body[i : i + step])
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return
            time.sleep(0.06)

    def log_message(self, *args) -> None:
        pass


class QuietServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address) -> None:  # noqa: D102
        pass  # 客户端中途暂停/取消时的断开是正常现象


server = QuietServer(("127.0.0.1", 0), RangeHandler)
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()

local = Trainer(
    name="Pause Resume Test",
    source="本地",
    kind="catalog",
    installed=False,
    url=f"http://127.0.0.1:{port}/payload.bin",
)
lt = ctx.queue.enqueue(local)
ok = wait_for(lambda: lt.done_mb > 0.5, 30, "local download start")
print(f"{'PASS' if ok else 'FAIL'} 本地下载已开始 {lt.done_mb:.2f} MB")

ctx.queue.toggle_pause(lt)
pump(0.6)  # 让已经发出的那一个 chunk 落地
mark = lt.done_mb
pump(1.2)
frozen = abs(lt.done_mb - mark) < 0.01
print(f"{'PASS' if frozen and lt.status == 'paused' else 'FAIL'} 暂停后进度冻结 {mark:.2f} → {lt.done_mb:.2f} MB")

ctx.queue.toggle_pause(lt)
ok = wait_for(lambda: lt.status in ("done", "failed"), 180, "local download finish")
print(f"{'PASS' if lt.status == 'done' else 'FAIL'} 续传完成：{lt.status} {lt.error}")
server.shutdown()

# ---------- 5. 清理 ----------
ctx.queue.clear_finished()
if not KEEP:
    for name in (item.name, "Pause Resume Test"):
        target = ctx.installed.directory() / name
        if target.exists():
            import shutil

            shutil.rmtree(target, ignore_errors=True)
    ctx.installed.refresh()
    print("已清理测试安装目录")

print("E2E OK")
sys.exit(0)
