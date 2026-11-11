"""底部下载队列条。"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget

from ...data.downloads import DownloadQueue, Task
from ...i18n import t


class QueueBar(QWidget):
    def __init__(self, queue: DownloadQueue, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("QueueBar")
        self.setFixedHeight(46)
        self._queue = queue

        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(12)

        self.label = QLabel(t("下载队列空闲"))
        self.label.setObjectName("Value")
        self.bar = QProgressBar()
        self.bar.setFixedWidth(220)
        self.bar.setFixedHeight(5)
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        self.pct = QLabel("")
        self.pct.setObjectName("Subtle")
        self.status = QLabel("")
        self.status.setObjectName("Subtle")
        self.status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        lay.addWidget(self.label)
        lay.addWidget(self.bar)
        lay.addWidget(self.pct)
        lay.addStretch(1)
        lay.addWidget(self.status)

        queue.updated.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        tasks = [t for t in self._queue.tasks if t.status in ("downloading", "paused", "installing")]
        if not tasks:
            self.label.setText(t("下载队列空闲"))
            self.bar.setValue(0)
            self.bar.setVisible(False)
            self.pct.setText("")
            done = [t for t in self._queue.tasks if t.status == "done"]
            failed = [t for t in self._queue.tasks if t.status == "failed"]
            tail = " · ".join(
                part
                for part in (
                    t("已完成 {n}").format(n=len(done)) if done else "",
                    t("失败 {n}").format(n=len(failed)) if failed else "",
                )
                if part
            )
            self.status.setText(tail)
            return
        task: Task = tasks[0]
        self.bar.setVisible(True)
        if task.status == "installing":
            self.label.setText(t("正在安装 {name}").format(name=task.name))
            self.bar.setValue(100)
            self.pct.setText(t("安装中"))
            self.status.setText(t("队列 {n}").format(n=len(self._queue.active())))
            return
        self.label.setText(t("正在下载 {name}").format(name=task.name))
        self.bar.setValue(task.progress)
        self.pct.setText(f"{task.progress}%")
        total = len(self._queue.active())
        speed = self._queue.total_speed()
        if task.status == "paused":
            self.status.setText(t("队列 {n} · {speed}").format(n=total, speed=t("已暂停")))
        elif speed > 0:
            self.status.setText(
                t("队列 {n} · {speed}").format(n=total, speed=f"{speed:.1f} MB/s")
                + f" · {task.eta}"
            )
        else:
            self.status.setText(t("队列 {n}").format(n=total))
