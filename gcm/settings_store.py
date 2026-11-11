"""带默认值、合并与持久化的设置存储。替代原项目的全局可变 dict。"""
from __future__ import annotations

import json
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from .paths import SETTINGS_FILE, default_trainer_dir

DEFAULTS: dict[str, Any] = {
    "theme": "dark",
    "language": "zh_CN",
    "downloadPath": str(default_trainer_dir()),
    "launchAsAdmin": False,
    "checkUpdate": True,
    "autoUpdateCatalog": True,
    "sortBy": "updated",
    "sources": {"gcm": True, "fling": True, "xiaoxing": True, "ct": True},
    # 下载源的站点地址，可在「设置 → 下载源」里改（镜像/反代）
    "sourceUrls": {
        "fling": "https://flingtrainer.com",
        "ct": "https://www.thecheatscript.com",
        "xiaoxing": "https://www.xiaoxingjie.com",
    },
    "steamNames": True,
    "showSidebar": True,
    "showDetail": True,
    "window": {"w": 1320, "h": 860},
}


def _merge(defaults: dict, loaded: dict) -> dict:
    out = dict(defaults)
    for key, value in (loaded or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


class SettingsStore(QObject):
    changed = pyqtSignal(str, object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._data = self._load()

    def _load(self) -> dict:
        loaded: dict = {}
        try:
            if SETTINGS_FILE.exists():
                loaded = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            loaded = {}
        data = _merge(DEFAULTS, loaded)
        if data.get("theme") not in ("dark", "light"):
            data["theme"] = "dark"
        return data

    def save(self) -> None:
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if self._data.get(key) == value:
            return
        self._data[key] = value
        self.save()
        self.changed.emit(key, value)

    def update(self, values: dict) -> None:
        for key, value in values.items():
            self.set(key, value)
