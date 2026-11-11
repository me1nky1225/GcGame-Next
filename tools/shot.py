"""开发用截图脚本：python tools/shot.py <page> <theme> <out.png>"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication  # noqa: E402
from PyQt6.QtCore import QTimer  # noqa: E402

from gcm.bootstrap import build_context  # noqa: E402
from gcm.data.downloads import Task  # noqa: E402
from gcm.data.trainer import Trainer  # noqa: E402
from gcm.i18n import translator, t  # noqa: E402
from gcm.ui.main_window import MainWindow  # noqa: E402


def demo_tasks() -> list[Task]:
    """截图用的假下载任务，不联网。"""
    def make(name: str, source: str, author: str, status: str, done: float, total: float, speed: float) -> Task:
        trainer = Trainer(
            name=name,
            source=source,
            author=author,
            version="v1.2",
            kind="catalog",
            installed=False,
        )
        task = Task(tid=f"shot-{name}", trainer=trainer)
        task.total_mb = total
        task.done_mb = done
        task.speed = speed
        task.status = status
        return task

    running = make("Elden Ring Nightreign", "GCM", "Hexinton", "downloading", 24.6, 58.9, 2.7)
    running.stage = t("解析下载地址…")
    done = make("Palworld", "FLiNG", "FLiNG", "done", 38.2, 38.2, 0.0)
    done.stage = t("已完成")
    return [running, done]


def prewarm(ctx, page: int, limit: int = 6, budget: float = 40.0) -> None:
    """提前把封面/中文名灌好，避免截图时还在异步加载。"""
    import time

    started = time.time()
    source = ctx.installed.items() if page == 0 else ctx.catalog.items()
    for trainer in source[:limit]:
        if time.time() - started > budget:
            print("prewarm: budget reached")
            break
        if trainer.cover:
            continue
        try:
            entry = ctx.steam.store.lookup(trainer.name)
            if not entry or entry.get("miss"):
                continue
            entry["cover_path"] = ctx.steam.store.cover_file(entry)
            ctx.apply_steam(entry)
        except Exception:
            continue


def main() -> int:
    page = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    theme = sys.argv[2] if len(sys.argv) > 2 else ""
    out = sys.argv[3] if len(sys.argv) > 3 else "shot.png"
    lang = sys.argv[4] if len(sys.argv) > 4 else ""
    query = sys.argv[5] if len(sys.argv) > 5 else ""

    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    ctx = build_context(app)
    if lang:
        translator.set_language(lang)
    if theme:
        ctx.theme.set_theme(theme)
    if page in (0, 1):
        prewarm(ctx, page)

    # 演示数据：让截图接近设计稿
    for i, trainer in enumerate(ctx.installed.items()):
        trainer.launched = [6, 24, 3][i] if i < 3 else 0
    ctx.queue.tasks.extend(demo_tasks())
    ctx.queue.updated.emit()

    window = MainWindow(ctx)
    window.resize(1400, 900)
    window.show()
    window._goto(page)
    if os.environ.get("GCM_SHOT_NO_DETAIL") == "1":
        window._apply_detail(False, save=False)
    if os.environ.get("GCM_SHOT_NOSIDEBAR") == "1":
        window._apply_sidebar(False, save=False)
    if query:
        window.topbar.search.setText(query)
        window.discover.set_query(query)
        window.discover.refresh()

    def snap() -> None:
        window.grab().save(out, "PNG")
        print("saved", out, window.width(), window.height())
        app.quit()

    QTimer.singleShot(1000, snap)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
