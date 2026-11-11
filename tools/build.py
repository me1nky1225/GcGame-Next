"""打包成可分发目录：python tools/build.py

输出 `dist/GCM Next/GCM Next.exe`（onedir：启动快，Qt 不需要解压到临时目录）。
`vendor/7z` 会一起打进去，装 rar/7z 压缩包时才不需要用户另外装 7-Zip。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "GCM Next"
DIST = Path(os.environ.get("GCM_DIST_DIR") or (ROOT / "dist" / NAME))

VERSION_TEMPLATE = """VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(0, 1, 0, 0),
    prodvers=(0, 1, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '080404b0',
        [StringStruct('CompanyName', 'GCM Next'),
         StringStruct('FileDescription', 'Game Cheats Manager Next'),
         StringStruct('FileVersion', '0.1.0'),
         StringStruct('InternalName', '{name}'),
         StringStruct('OriginalFilename', '{name}.exe'),
         StringStruct('ProductName', 'GCM Next'),
         StringStruct('ProductVersion', '0.1.0-poc')])
    ]),
    VarFileInfo([VarStruct('Translation', [2052, 1200])])
  ]
)
"""


PRUNE = (
    # 纯 raster 绘制，不用 OpenGL；这个软件渲染后端有 20 MB
    ("_internal/PyQt6/Qt6/bin/opengl32sw.dll",),
    ("_internal/PyQt6/Qt6/bin/Qt6Pdf.dll",),
    ("_internal/PyQt6/Qt6/bin/Qt6Network.dll",),
    ("_internal/PyQt6/Qt6/plugins/networkinformation",),
    ("_internal/PyQt6/Qt6/plugins/tls",),
)


def prune(dist: Path) -> list[str]:
    """去掉用不到的 Qt 组件，省 ~27 MB。删之前先确认 exe 还能起（build 后自检）。"""
    removed: list[str] = []
    for (rel,) in PRUNE:
        target = dist / rel
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
            removed.append(rel)
        elif target.is_file():
            target.unlink()
            removed.append(rel)
    return removed


def main() -> int:
    if not (ROOT / "assets" / "app.ico").is_file():
        print("缺少 assets/app.ico，先跑 tools/make_icon.py")
        return 1

    version_file = ROOT / "build" / "version_info.txt"
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_file.write_text(VERSION_TEMPLATE.format(name=NAME), encoding="utf-8")

    for path in (ROOT / "build" / NAME, DIST, ROOT / "dist" / f"{NAME}.spec"):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        NAME,
        "--icon",
        str(ROOT / "assets" / "app.ico"),
        "--add-data",
        f"{ROOT / 'assets'}{';'}assets",
        "--add-data",
        f"{ROOT / 'vendor'}{';'}vendor",
        "--add-data",
        f"{ROOT / 'gcm' / 'data' / 'steam_seed.json'}{';'}gcm/data",
        "--distpath",
        str(DIST.parent),
        "--version-file",
        str(version_file),
        "--exclude-module",
        "tkinter",
        "--exclude-module",
        "PyQt6.QtWebEngineCore",
        "--exclude-module",
        "PyQt6.QtQml",
        str(ROOT / "main.py"),
    ]
    print(" ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT))
    if proc.returncode != 0:
        print("PyInstaller 失败")
        return proc.returncode

    exe = DIST / f"{NAME}.exe"
    if not exe.is_file():
        print("没有生成 exe：", exe)
        return 1
    for rel in prune(DIST):
        print("pruned", rel)
    total = sum(f.stat().st_size for f in DIST.rglob("*") if f.is_file())
    print(f"\nOK  {exe}\n    {exe.stat().st_size / 1048576:.1f} MB exe · 整目录 {total / 1048576:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
