"""右侧详情面板。"""
from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from ...data.trainer import Trainer
from ...i18n import t as tr
from ...theme.tokens import Tokens
from ...util import fmt_size, humanize


class CoverArt(QWidget):
    def __init__(self, tokens: Tokens, parent=None) -> None:
        super().__init__(parent)
        self.tokens = tokens
        self._name = ""
        self._sub = ""
        self._cover = ""
        self._pix: QPixmap | None = None
        self.setFixedHeight(132)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_tokens(self, tokens: Tokens) -> None:
        self.tokens = tokens
        self.update()

    def set_trainer(self, trainer: Trainer | None) -> None:
        self._name = trainer.title if trainer else ""
        self._sub = trainer.source if trainer else ""
        self._cover = trainer.cover if trainer else ""
        self._pix = None
        self.update()

    def _load(self) -> QPixmap | None:
        if self._pix is not None or not self._cover:
            return self._pix
        pix = QPixmap(self._cover)
        self._pix = None if pix.isNull() else pix
        return self._pix

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        rect = QRectF(self.rect()).adjusted(0, 0, 0, 0)
        path = QPainterPath()
        path.addRoundedRect(rect, 16, 16)
        p.setClipPath(path)
        if not self._name:
            p.fillPath(path, QColor(self.tokens.card))
            return
        pix = self._load()
        if pix is not None:
            # 封面按「填满」裁切，保持比例
            scaled = pix.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            p.drawPixmap(
                int((self.width() - scaled.width()) / 2),
                int((self.height() - scaled.height()) / 2),
                scaled,
            )
            shade = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            shade.setColorAt(0.0, QColor(0, 0, 0, 0))
            shade.setColorAt(1.0, QColor(0, 0, 0, 150))
            p.fillPath(path, shade)
        else:
            c1, c2 = self.tokens.cover(self._name)
            grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
            grad.setColorAt(0.0, QColor(c1))
            grad.setColorAt(1.0, QColor(c2))
            p.fillPath(path, grad)

            glow = QLinearGradient(rect.topRight(), rect.bottomLeft())
            glow.setColorAt(0.0, QColor(255, 255, 255, 46))
            glow.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.fillPath(path, glow)

        if pix is None:
            # 只有渐变兜底时才把名字画在封面上；真封面自带 logo，不重复
            f = QFont(self.tokens.font_family)
            f.setPixelSize(16)
            f.setWeight(QFont.Weight.Bold)
            p.setFont(f)
            p.setPen(QColor("#ffffff"))
            p.drawText(
                rect.adjusted(16, 0, -16, -14),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
                self._name,
            )


class DetailPanel(QWidget):
    launchRequested = pyqtSignal(object)
    folderRequested = pyqtSignal(object)
    removeRequested = pyqtSignal(object)

    def __init__(self, tokens: Tokens, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("DetailPanel")
        self.tokens = tokens
        self._trainer: Trainer | None = None
        self.setFixedWidth(340)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 24, 16, 24)
        root.setSpacing(14)

        self.cover = CoverArt(tokens)
        root.addWidget(self.cover)

        self.title = QLabel(tr("未选择"))
        self.title.setObjectName("H2")
        root.addWidget(self.title)

        self.subtitle = QLabel("")
        self.subtitle.setObjectName("Subtle")
        root.addWidget(self.subtitle)

        self.kv_box = QVBoxLayout()
        self.kv_box.setSpacing(9)
        self._kv: dict[str, QLabel] = {}
        for key in ("来源", "类型", "大小", "上次启动", "启动次数"):
            row = QWidget()
            lay = QHBoxLayout(row)
            lay.setContentsMargins(0, 0, 0, 0)
            left = QLabel(tr(key))
            left.setObjectName("FieldLabel")
            value = QLabel("-")
            value.setObjectName("Value")
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lay.addWidget(left)
            lay.addStretch(1)
            lay.addWidget(value)
            self._kv[key] = value
            self.kv_box.addWidget(row)
        root.addLayout(self.kv_box)

        self.path_label = QLabel("")
        self.path_label.setObjectName("PathBox")
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(self.path_label)

        root.addStretch(1)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.primary = QPushButton(tr("启动"))
        self.primary.setObjectName("Primary")
        self.primary.setMinimumHeight(34)
        self.primary.clicked.connect(self._on_primary)
        self.folder = QPushButton(tr("目录"))
        self.folder.setMinimumHeight(34)
        self.folder.clicked.connect(self._on_folder)
        actions.addWidget(self.primary, 1)
        actions.addWidget(self.folder, 1)
        root.addLayout(actions)

        self.set_trainer(None)

    # ---------- 主题 ----------
    def set_tokens(self, tokens: Tokens) -> None:
        self.tokens = tokens
        self.cover.set_tokens(tokens)

    # ---------- 数据 ----------
    def current(self) -> Trainer | None:
        return self._trainer

    def set_trainer(self, trainer: Trainer | None) -> None:
        self._trainer = trainer
        self.cover.set_trainer(trainer)
        if trainer is None:
            self.title.setText(tr("未选择"))
            self.subtitle.setText(tr("从左侧列表选择一个修改器"))
            for key in self._kv:
                self._kv[key].setText("-")
            self.path_label.setText("—")
            self.primary.setEnabled(False)
            self.folder.setEnabled(False)
            return

        self.title.setText(trainer.title)
        parts = [
            p
            for p in (
                trainer.alt_title,
                trainer.author if trainer.author and trainer.author != trainer.source else "",
                f"v{trainer.version}" if trainer.version else "",
            )
            if p
        ]
        self.subtitle.setText(
            " · ".join(parts) or (tr("已安装") if trainer.installed else tr("在线资源"))
        )
        self._kv["来源"].setText(trainer.source)
        self._kv["类型"].setText(
            tr(
                {
                    "exe": "独立 exe",
                    "ct": "Cheat Table",
                    "dir": "目录型",
                    "archive": "压缩包",
                    "catalog": "在线资源",
                }.get(trainer.kind, trainer.kind)
            )
        )
        self._kv["大小"].setText(fmt_size(trainer.size_mb) if trainer.size_mb else "-")
        self._kv["上次启动"].setText(humanize(trainer.last_launch) if trainer.installed else "-")
        self._kv["启动次数"].setText(
            tr("{n} 次").format(n=trainer.launched) if trainer.launched else tr("从未")
        )

        if trainer.installed and trainer.path is not None:
            self.path_label.setText(str(trainer.path))
        else:
            self.path_label.setText(trainer.desc or tr("在线资源，下载后可离线使用"))

        if trainer.installed:
            self.primary.setText(tr("启动"))
            self.folder.setText(tr("目录"))
        elif trainer.external:
            self.primary.setText(tr("打开网页"))
            self.folder.setText(tr("复制链接"))
        else:
            self.primary.setText(tr("获取"))
            self.folder.setText(tr("详情"))
        self.primary.setEnabled(True)
        self.folder.setEnabled(True)

    # ---------- 动作 ----------
    def _on_primary(self) -> None:
        if self._trainer is not None:
            self.launchRequested.emit(self._trainer)

    def _on_folder(self) -> None:
        if self._trainer is not None:
            self.folderRequested.emit(self._trainer)
