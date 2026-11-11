"""运行期路径与常量。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "GCM Next"
APP_ID = "gcm-next"
APP_VERSION = "0.1.0-poc"


def _appdata() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base)


def _canonical(path: Path) -> Path:
    """解析成真实路径。

    两种情况下 `%APPDATA%\\GCM Next` 只是个别名：
    - Roaming 被重定向 / 是目录联接（企业环境常见），
    - 用 Microsoft Store 版 Python 运行时，AppData 写入会被重定向到
      `...\\Packages\\PythonSoftwareFoundation.Python.*\\LocalCache\\...`，
      此时本进程能看见文件，别的进程（7z、资源管理器）看不见。
    子进程不共享这层重定向，所以必须拿真实路径再交给它们。

    注意：`path.resolve()` 对目录本身可能原样返回别名（目录在真实位置也存在，
    被当成了重定向根），所以这里写一个探针文件、解析文件路径再取父目录。
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".gcm-probe"
        probe.write_text("", encoding="utf-8")
        try:
            return probe.resolve().parent
        finally:
            probe.unlink(missing_ok=True)
    except OSError:
        return path


DATA_DIR = _canonical(_appdata() / APP_NAME)
SETTINGS_FILE = DATA_DIR / "settings.json"
USAGE_FILE = DATA_DIR / "usage.json"
TRASH_DIR = DATA_DIR / "trash"


def display_path(path: Path) -> str:
    """给用户看的路径：DATA_DIR 一律显示成 `%APPDATA%\\GCM Next`。

    Store 版 Python 下 DATA_DIR 会解析成
    `D:\\WpSystem\\...\\LocalCache\\Roaming\\GCM Next`，直接显示太吓人。
    """
    path = Path(path)
    try:
        rest = path.relative_to(DATA_DIR)
    except ValueError:
        pass
    else:
        tail = f"\\{rest}" if str(rest) not in ("", ".") else ""
        return f"%APPDATA%\\{APP_NAME}{tail}"
    root = _appdata()
    if root and str(path).startswith(str(root)):
        return "%APPDATA%" + str(path)[len(str(root)) :]
    return str(path)

# 兼容：默认直接复用现有 GCM 的修改器目录，PoC 打开就有内容
# （只读，所以保留未解析的别名路径即可）
LEGACY_TRAINER_DIR = _appdata() / "GCM Trainers"
LEGACY_DB_DIR = _appdata() / "GCM Settings" / "db"


def default_trainer_dir() -> Path:
    if LEGACY_TRAINER_DIR.is_dir():
        return LEGACY_TRAINER_DIR
    return DATA_DIR / "Trainers"


def bundled_dir() -> Path:
    """随程序分发的资源目录（图标、vendor/7z 等）。

    PyInstaller 冻结后 `--add-data` 的内容在 `sys._MEIPASS`（onedir 下是 `_internal`），
    不是 exe 所在目录，两者要区分开。
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def asset_path(name: str) -> Path:
    return bundled_dir() / "assets" / name


def ensure_dirs() -> None:
    for d in (DATA_DIR, TRASH_DIR):
        d.mkdir(parents=True, exist_ok=True)
