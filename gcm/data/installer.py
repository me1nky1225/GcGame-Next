"""下载完成后的落地：解包 → 放进库目录 → 写 gcm_info.json。

`gcm_info.json` 沿用旧版字段（version / origin / author / extension），
这样新旧两套安装目录可以互相识别。
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
import zipfile
from pathlib import Path

from ..paths import bundled_dir
from .trainer import Trainer

SAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
ARCHIVE_EXTS = {".zip", ".7z", ".rar"}
EXEC_EXTS = {".exe", ".ct", ".cetrainer"}

# 旧版安装目录里自带 7z.exe，找不到系统 7-Zip 时退而用它
_LEGACY_7Z = Path(r"E:\PcApp\Game Cheats Manager\dependency\7z\7z.exe")


def safe_folder_name(name: str) -> str:
    cleaned = SAFE.sub(" ", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(".")
    return (cleaned or "trainer")[:80]


def find_7z() -> str | None:
    # 1) 随程序分发的 7z（PyInstaller 打包后也在 _MEIPASS/vendor/7z 下）
    bundled = bundled_dir() / "vendor" / "7z" / "7z.exe"
    if bundled.is_file():
        return str(bundled)
    found = shutil.which("7z") or shutil.which("7za")
    if found:
        return found
    if _LEGACY_7Z.is_file():
        return str(_LEGACY_7Z)
    for candidate in (
        Path(r"C:\Program Files\7-Zip\7z.exe"),
        Path(r"C:\Program Files (x86)\7-Zip\7z.exe"),
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def _extract_zip(archive: Path, dest: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        for member in zf.namelist():
            target = (dest / member).resolve()
            if not str(target).startswith(str(dest.resolve())):
                raise RuntimeError(f"压缩包里有越界路径：{member}")
        zf.extractall(dest)


def _extract_7z(archive: Path, dest: Path) -> None:
    seven = find_7z()
    if not seven:
        raise RuntimeError("需要 7-Zip 才能解开这个压缩包（未找到 7z.exe）")
    proc = subprocess.run(  # noqa: S603
        [seven, "x", "-y", f"-o{dest}", str(archive)],
        capture_output=True,
        text=True,
        timeout=300,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"解压失败：{proc.stderr.strip()[:200] or proc.stdout.strip()[:200]}")


def extract_archive(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if archive.suffix.lower() == ".zip" or zipfile.is_zipfile(archive):
        _extract_zip(archive, dest)
    else:
        _extract_7z(archive, dest)


def _flatten_single_dir(root: Path) -> Path:
    """压缩包里只有一层同名目录时，把它提上来，避免 /Game/Game/x.exe。"""
    entries = [p for p in root.iterdir() if not p.name.startswith(".")]
    if len(entries) == 1 and entries[0].is_dir():
        inner = entries[0]
        for child in list(inner.iterdir()):
            target = root / child.name
            if target.exists():
                continue
            shutil.move(str(child), str(target))
        try:
            inner.rmdir()
        except OSError:
            pass
    return root


def _pick_executable(root: Path) -> str:
    files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in EXEC_EXTS]
    if not files:
        return ""
    files.sort(
        key=lambda p: (
            0 if "trainer" in p.name.lower() else 1,
            len(p.parts),
            p.name.lower(),
        )
    )
    best = files[0]
    return best.relative_to(root).as_posix()


def install(
    downloaded: Path,
    trainer: Trainer,
    download_dir: Path,
    *,
    keep_archive: bool = False,
) -> Path:
    """把下载下来的文件装成 `<库目录>/<游戏名>/`，返回安装目录。"""
    download_dir.mkdir(parents=True, exist_ok=True)
    target_dir = download_dir / safe_folder_name(trainer.name)
    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)
    target_dir.mkdir(parents=True, exist_ok=True)

    if downloaded.suffix.lower() in ARCHIVE_EXTS:
        extract_archive(downloaded, target_dir)
        _flatten_single_dir(target_dir)
    else:
        shutil.copy2(downloaded, target_dir / downloaded.name)

    extension = _pick_executable(target_dir)
    meta = {
        "name": trainer.name,
        "version": trainer.version,
        "origin": _origin_key(trainer.source),
        "author": trainer.author,
        "extension": extension or "none",
        "source": trainer.source,
        "url": trainer.url,
        "installed_at": int(time.time()),
        "installer": "gcm-next",
    }
    (target_dir / "gcm_info.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if not keep_archive:
        try:
            downloaded.unlink()
        except OSError:
            pass
    return target_dir


def _origin_key(source: str) -> str:
    return {
        "FLiNG": "fling",
        "小幸": "xiaoxing",
        "CT": "the_cheat_script",
        "GCM": "gcm",
    }.get(source, "other")
