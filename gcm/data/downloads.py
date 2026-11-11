"""下载队列：真实下载任务 + 并发调度 + 暂停/恢复/取消/重试。"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from ..i18n import t
from ..paths import DATA_DIR
from .downloader import DownloadJob
from .trainer import Trainer

MAX_ACTIVE = 2


@dataclass
class Task:
    tid: str
    trainer: Trainer
    total_mb: float = 0.0
    done_mb: float = 0.0
    speed: float = 0.0
    status: str = "queued"  # queued / downloading / paused / installing / done / failed
    error: str = ""
    stage: str = "等待开始"
    created: float = field(default_factory=time.time)
    job: DownloadJob | None = field(default=None, repr=False)

    @property
    def name(self) -> str:
        return self.trainer.name

    @property
    def source(self) -> str:
        return self.trainer.source

    @property
    def progress(self) -> int:
        if self.total_mb <= 0:
            return 0 if self.status != "done" else 100
        return min(100, int(self.done_mb / self.total_mb * 100))

    @property
    def eta(self) -> str:
        if self.speed <= 0.01 or self.total_mb <= 0:
            return ""
        remain = max(0.0, self.total_mb - self.done_mb) / self.speed
        if remain < 60:
            return t("剩余 {n} 秒").format(n=int(remain))
        return t("剩余 {m} 分 {s} 秒").format(m=int(remain // 60), s=int(remain % 60))


class DownloadQueue(QObject):
    updated = pyqtSignal()
    completed = pyqtSignal(object)  # Task
    failed = pyqtSignal(object, str)  # Task, message

    def __init__(self, download_dir: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.download_dir = download_dir
        self.temp_dir = DATA_DIR / "tmp"
        self.tasks: list[Task] = []
        self._seq = 0

    # ---------- 查询 ----------
    def active(self) -> list[Task]:
        return [t for t in self.tasks if t.status in ("queued", "downloading", "paused", "installing")]

    def running(self) -> list[Task]:
        return [t for t in self.tasks if t.status in ("downloading", "installing")]

    def total_speed(self) -> float:
        return sum(t.speed for t in self.tasks if t.status == "downloading")

    def find(self, tid: str) -> Task | None:
        return next((t for t in self.tasks if t.tid == tid), None)

    def is_queued(self, name: str) -> bool:
        return any(t.name == name and t.status in ("queued", "downloading", "paused", "installing") for t in self.tasks)

    # ---------- 入队 ----------
    def enqueue(self, trainer: Trainer) -> Task:
        existing = next((t for t in self.tasks if t.name == trainer.name and t.status == "downloading"), None)
        if existing:
            return existing
        self._seq += 1
        task = Task(tid=f"t{self._seq}", trainer=trainer)
        self.tasks.insert(0, task)
        self.updated.emit()
        self._pump()
        return task

    # ---------- 操作 ----------
    def toggle_pause(self, task: Task) -> None:
        if task.status == "downloading" and task.job is not None:
            task.job.pause()
            task.status = "paused"
            task.speed = 0.0
            task.stage = t("已暂停")
        elif task.status == "paused" and task.job is not None:
            task.job.resume()
            task.status = "downloading"
            task.stage = t("继续下载…")
        self.updated.emit()

    def retry(self, task: Task) -> None:
        if task.status not in ("failed",):
            return
        task.status = "queued"
        task.error = ""
        task.done_mb = 0.0
        task.speed = 0.0
        task.stage = t("等待开始")
        self.updated.emit()
        self._pump()

    def remove(self, task: Task) -> None:
        if task.job is not None:
            task.job.cancel()
            task.job.wait(3000)
        if task in self.tasks:
            self.tasks.remove(task)
        self.updated.emit()
        self._pump()

    def clear_finished(self) -> None:
        for task in list(self.tasks):
            if task.status == "done":
                self.tasks.remove(task)
        self.updated.emit()

    # ---------- 调度 ----------
    def _pump(self) -> None:
        while len(self.running()) < MAX_ACTIVE:
            pending = next((t for t in reversed(self.tasks) if t.status == "queued"), None)
            if pending is None:
                return
            self._start(pending)

    def _start(self, task: Task) -> None:
        job = DownloadJob(task.tid, task.trainer, self.download_dir, self.temp_dir)
        job.progressed.connect(self._on_progress)
        job.stage.connect(self._on_stage)
        job.finished_ok.connect(self._on_ok)
        job.failed.connect(self._on_failed)
        job.cancelled.connect(self._on_cancelled)
        task.job = job
        task.status = "downloading"
        task.stage = t("准备中…")
        job.start()

    # ---------- 信号 ----------
    def _on_progress(self, tid: str, done_mb: float, total_mb: float, speed: float) -> None:
        task = self.find(tid)
        if task is None:
            return
        task.done_mb = done_mb
        task.total_mb = total_mb
        task.speed = speed
        self.updated.emit()

    def _on_stage(self, tid: str, text: str) -> None:
        task = self.find(tid)
        if task is None:
            return
        task.stage = text
        if "安装" in text:
            task.status = "installing"
            task.speed = 0.0
        self.updated.emit()

    def _on_ok(self, tid: str, path: str) -> None:
        task = self.find(tid)
        if task is None:
            return
        task.status = "done"
        task.speed = 0.0
        task.done_mb = task.total_mb or task.done_mb
        task.stage = t("已安装到 {path}").format(path=path)
        task.job = None
        self.updated.emit()
        self.completed.emit(task)
        self._pump()

    def _on_failed(self, tid: str, message: str) -> None:
        task = self.find(tid)
        if task is None:
            return
        task.status = "failed"
        task.speed = 0.0
        task.error = message
        task.stage = message
        task.job = None
        self.updated.emit()
        self.failed.emit(task, message)
        self._pump()

    def _on_cancelled(self, tid: str) -> None:
        task = self.find(tid)
        if task is not None:
            task.job = None
            if task.status not in ("done",):
                task.status = "failed"
                task.error = t("已取消")
                task.stage = t("已取消")
            self.updated.emit()
        self._pump()
