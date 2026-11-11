"""已安装修改器的扫描、启动、删除，以及使用记录。"""
from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from ..paths import TRASH_DIR, USAGE_FILE
from .trainer import Trainer

SOURCE_ALIASES = {
    "风灵": "FLiNG",
    "fling": "FLiNG",
    "小幸": "小幸",
    "xiaoxing": "小幸",
    "gcm": "GCM",
    "ct": "CT",
    "the_cheat_script": "CT",
}
TRAINER_EXTS = {".exe", ".ct", ".cetrainer"}
ARCHIVE_EXTS = {".zip", ".7z", ".rar"}


def parse_entry_name(raw: str) -> tuple[str, str, str]:
    """把 `[风灵]《侠盗猎车5: 增强版》修改器` 这类名字拆成 (游戏名, 来源, 作者)。"""
    text = raw.strip()
    lower = text.lower()
    for ext in (".cetrainer", ".exe", ".ct", ".zip", ".7z", ".rar"):
        if lower.endswith(ext):
            text = text[: -len(ext)]
            break

    source = "本地"
    m = re.match(r"^\[([^\]]+)\]\s*", text)
    if m:
        tag = m.group(1).strip()
        source = SOURCE_ALIASES.get(tag.lower(), tag)
        text = text[m.end():]

    author = ""
    m = re.search(r"\s*\[([^\]]+)\]\s*$", text)
    if m:
        author = m.group(1).strip()
        text = text[: m.start()]

    text = re.sub(r"《(.+?)》", r"\1", text)
    text = re.sub(r"(?i)\s*\b(trainer|cheat table)\b\s*", " ", text)
    text = text.replace("修改器", " ").strip(" -_·:：")
    name = re.sub(r"\s{2,}", " ", text).strip()
    return (name or raw.strip(), source, author)


def _english_alias(path: Path | None) -> str:
    """从训练器文件名里猜一个英文游戏名（FLiNG 的文件名通常是英文全名）。

    `Grand Theft Auto V Enhanced v1.0.811 Plus 22 Trainer.exe`
      → `Grand Theft Auto V Enhanced`
    猜不出来（比如全是中文文件名）就返回空串。
    """
    if path is None:
        return ""
    stem = path.stem if path.suffix else path.name
    text = re.sub(r"(?i)\b(v|ver\.?)\s*\d[\w.]*", " ", stem)
    text = re.sub(r"(?i)\b(plus|update|hotfix|dlc)\b.*$", " ", text)
    text = re.sub(r"(?i)\b(trainer|cheat\s*table|steam|multiplayer)\b", " ", text)
    text = re.sub(r"[_\-\[\]()]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" ._")
    if not text or not re.search(r"[A-Za-z]{3}", text):
        return ""
    if re.search(r"[\u3400-\u9fff]", text):
        return ""
    return text


def _folder_size_mb(path: Path) -> float:
    total = 0
    count = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += (Path(root) / f).stat().st_size
            except OSError:
                continue
            count += 1
            if count > 4000:
                break
        if count > 4000:
            break
    return total / (1024 * 1024)


class InstalledIndex(QObject):
    changed = pyqtSignal()

    def __init__(self, settings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._usage = self._load_usage()
        self.trainers: list[Trainer] = []

    # ---------- 目录与使用记录 ----------
    def items(self) -> list[Trainer]:
        return self.trainers

    def directory(self) -> Path:
        return Path(self._settings.get("downloadPath", ""))

    def set_directory(self, path: Path) -> None:
        self._settings.set("downloadPath", str(path))

    def _load_usage(self) -> dict:
        try:
            if USAGE_FILE.exists():
                return json.loads(USAGE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save_usage(self) -> None:
        try:
            USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
            USAGE_FILE.write_text(
                json.dumps(self._usage, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    # ---------- 扫描 ----------
    def refresh(self) -> None:
        root = self.directory()
        items: list[Trainer] = []
        if root.is_dir():
            try:
                entries = sorted(root.iterdir(), key=lambda p: p.name.lower())
            except OSError:
                entries = []
            for entry in entries:
                if entry.name.startswith(".") or entry.name == "gcm_info.json":
                    continue
                trainer = self._build(entry)
                if trainer is not None:
                    items.append(trainer)
        self.trainers = items
        # 列表项是新建对象，先把磁盘缓存里的中文名/封面贴回来，再通知界面刷新，
        # 否则删掉一个修改器后其它行的封面会全变成色块
        hook = getattr(self, "on_rebuild", None)
        if hook is not None:
            try:
                hook()
            except Exception:
                pass
        self.changed.emit()

    def _build(self, entry: Path) -> Trainer | None:
        try:
            stat = entry.stat()
        except OSError:
            return None
        name, source, author = parse_entry_name(entry.name)
        usage = self._usage.get(entry.name, {})

        kind = "dir"
        target = entry
        size_mb = 0.0
        version = ""

        if entry.is_file():
            suffix = entry.suffix.lower()
            if suffix not in TRAINER_EXTS | ARCHIVE_EXTS:
                return None
            kind = "ct" if suffix in (".ct", ".cetrainer") else "exe"
            if suffix in ARCHIVE_EXTS:
                kind = "archive"
            size_mb = stat.st_size / (1024 * 1024)
        else:
            info = entry / "gcm_info.json"
            if info.is_file():
                try:
                    meta = json.loads(info.read_text(encoding="utf-8"))
                    version = str(meta.get("version", "") or "")
                    name = meta.get("name") or name
                    source = SOURCE_ALIASES.get(str(meta.get("origin", "")).lower(), source)
                    author = meta.get("author") or author
                    ext = str(meta.get("extension", "") or "").lower()
                    if ext == "none":
                        target = entry
                    else:
                        target = entry / ext if ext else entry
                except Exception:
                    pass
            if not target.is_file():
                candidates = [
                    p for p in entry.iterdir()
                    if p.is_file() and p.suffix.lower() in (".exe", ".ct", ".cetrainer")
                ]
                candidates.sort(key=lambda p: (p.suffix.lower() != ".exe", p.name.lower()))
                target = candidates[0] if candidates else entry
                if target.suffix.lower() in (".ct", ".cetrainer"):
                    kind = "ct"
                else:
                    kind = "exe" if target.is_file() else "dir"
            size_mb = _folder_size_mb(entry)

        trainer = Trainer(
            name=name,
            path=target,
            source=source,
            author=author,
            version=version,
            kind=kind,
            updated=stat.st_mtime,
            launched=int(usage.get("count", 0)),
            last_launch=float(usage.get("last", 0.0)),
            size_mb=size_mb,
            alias=_english_alias(target),
            home=entry,
        )
        if trainer.kind == "dir":
            trainer.desc = "目录型修改器"
        return trainer

    # ---------- 操作 ----------
    def launch(self, trainer: Trainer) -> tuple[bool, str]:
        if trainer.path is None:
            return False, "找不到修改器文件"
        try:
            os.startfile(str(trainer.path))  # noqa: S606 - Windows 关联启动
        except OSError as exc:
            return False, f"启动失败：{exc}"
        rec = self._usage.setdefault(trainer.name, {"count": 0, "last": 0.0})
        rec["count"] = int(rec.get("count", 0)) + 1
        rec["last"] = time.time()
        self._save_usage()
        trainer.launched += 1
        trainer.last_launch = time.time()
        return True, "已启动"

    def open_folder(self, trainer: Trainer) -> tuple[bool, str]:
        if trainer.path is None:
            return False, "找不到路径"
        target = trainer.path if trainer.path.is_dir() else trainer.path.parent
        try:
            os.startfile(str(target))  # noqa: S606
        except OSError as exc:
            return False, f"打开失败：{exc}"
        return True, ""

    def remove(self, trainer: Trainer) -> tuple[bool, str]:
        # 整个条目移走：目录型修改器如果只移 exe，会留下一个空壳条目
        victim = trainer.home or trainer.path
        if victim is None or not victim.exists():
            return False, "文件不存在"
        try:
            TRASH_DIR.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            dest = TRASH_DIR / f"{stamp}__{victim.name}"
            if dest.exists():
                dest = TRASH_DIR / f"{stamp}-{int(time.time() % 1000)}__{victim.name}"
            shutil.move(str(victim), str(dest))
        except Exception as exc:  # noqa: BLE001
            return False, f"删除失败：{exc}"
        self.refresh()
        return True, "已移到回收目录"
