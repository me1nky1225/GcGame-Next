"""抓任意进程的主窗口（含原生标题栏）：python tools/grab_window.py <进程名> <out.png>

用 PrintWindow + PW_RENDERFULLCONTENT 抓，再切掉 1px 边框。
必须先 SetProcessDPIAware，否则 GetWindowRect 返回虚拟化尺寸，只截到左上角。
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


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


def hwnd_of(process_name: str) -> tuple[int, int, int, int]:
    pid = 0
    handles: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def enum_proc(hwnd, _lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if buf.value and user32.IsWindowVisible(hwnd):
                handles.append(hwnd)
        return True

    user32.EnumWindows(enum_proc, 0)
    pids: dict[int, str] = {}
    for hwnd in handles:
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        pids[hwnd] = str(owner.value)

    import subprocess

    out = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        encoding="gbk",
        errors="replace",
    ).stdout
    wanted = {line.split('","')[1] for line in out.splitlines() if line.startswith('"')}
    for hwnd in reversed(handles):
        if pids.get(hwnd) in wanted:
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            return hwnd, rect.right - rect.left, rect.bottom - rect.top, int(pids[hwnd])
    raise SystemExit(f"找不到 {process_name} 的可见窗口")


def grab(hwnd: int, width: int, height: int, out: Path) -> None:
    hdc_window = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_window)
    hbitmap = gdi32.CreateCompatibleBitmap(hdc_window, width, height)
    gdi32.SelectObject(hdc_mem, hbitmap)

    user32.PrintWindow(hwnd, hdc_mem, 2)  # PW_RENDERFULLCONTENT：DWM 合成的窗口也能抓

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = width
    bmi.bmiHeader.biHeight = -height  # 负数 = 自上而下
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0

    buf = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(hdc_mem, hbitmap, 0, height, buf, ctypes.byref(bmi), 0)

    from PyQt6.QtGui import QImage

    image = QImage(buf, width, height, QImage.Format.Format_ARGB32).copy()
    image.save(str(out), "PNG")

    gdi32.DeleteObject(hbitmap)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(hwnd, hdc_window)


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    name, out = sys.argv[1], Path(sys.argv[2])
    user32.SetProcessDPIAware()
    hwnd, w, h, pid = hwnd_of(name)
    print(f"hwnd={hwnd} pid={pid} size={w}x{h}")
    grab(hwnd, w, h, out)
    print("saved", out, out.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
