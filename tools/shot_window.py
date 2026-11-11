"""在真实窗口里抓一张整窗截图（含原生标题栏），用于文档/验收。"""
from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes

os.environ.pop("QT_QPA_PLATFORM", None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from gcm.bootstrap import build_context  # noqa: E402
from gcm.ui.main_window import MainWindow  # noqa: E402
from shot import demo_tasks  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else "window.png"
page = int(sys.argv[2]) if len(sys.argv) > 2 else 0

app = QApplication([])
ctx = build_context(app)
for i, trainer in enumerate(ctx.installed.items()):
    trainer.launched = [6, 24, 3][i] if i < 3 else 0
ctx.queue.tasks.extend(demo_tasks())
ctx.queue.updated.emit()
win = MainWindow(ctx)
win.resize(1400, 900)
win.show()
win._goto(page)
for _ in range(30):
    app.processEvents()

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
hwnd = int(win.winId())
rect = wintypes.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
w, h = rect.right - rect.left, rect.bottom - rect.top

hdc = user32.GetWindowDC(hwnd)
mem_dc = gdi32.CreateCompatibleDC(hdc)
bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
gdi32.SelectObject(mem_dc, bmp)
user32.PrintWindow(hwnd, mem_dc, 2)

from PyQt6.QtGui import QImage, QPixmap  # noqa: E402

# BITMAPINFOHEADER 读取 BGRA
class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


bi = BITMAPINFO()
bi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
bi.bmiHeader.biWidth = w
bi.bmiHeader.biHeight = -h
bi.bmiHeader.biPlanes = 1
bi.bmiHeader.biBitCount = 32
bi.bmiHeader.biCompression = 0
buf = ctypes.create_string_buffer(w * h * 4)
gdi32.GetDIBits(mem_dc, bmp, 0, h, buf, ctypes.byref(bi), 0)

img = QImage(buf.raw, w, h, w * 4, QImage.Format.Format_ARGB32)
QPixmap.fromImage(img.copy()).save(out)
gdi32.DeleteObject(bmp)
gdi32.DeleteDC(mem_dc)
user32.ReleaseDC(hwnd, hdc)
print(f"saved {out} {w}x{h}")
