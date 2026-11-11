"""生成应用图标：assets/icon-<size>.png（用 QPainter 画，和侧栏 Logo 同款）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PyQt6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPixmap  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

SIZES = (16, 24, 32, 48, 64, 128, 256)


def draw(size: int) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    inset = size * 0.04
    rect = QRectF(inset, inset, size - inset * 2, size - inset * 2)
    radius = size * 0.24

    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)

    grad = QLinearGradient(QPointF(rect.left(), rect.top()), QPointF(rect.right(), rect.bottom()))
    grad.setColorAt(0.0, QColor("#4f8cff"))
    grad.setColorAt(1.0, QColor("#7b5cff"))
    p.fillPath(path, grad)

    # 顶部一道高光，避免小尺寸下看起来是死板的纯色块
    gloss = QPainterPath()
    gloss.addRoundedRect(QRectF(rect.left(), rect.top(), rect.width(), rect.height() * 0.46), radius, radius)
    p.fillPath(gloss, QColor(255, 255, 255, 26))

    font = QFont("Segoe UI", int(size * 0.40))
    font.setWeight(QFont.Weight.Bold)
    p.setFont(font)
    p.setPen(QColor("#ffffff"))
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "GC")
    p.end()
    return pm


def main() -> int:
    app = QApplication(sys.argv[:1])  # noqa: F841  需要 QGuiApplication 实例才能渲染
    out = ROOT / "assets"
    out.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        path = out / f"icon-{size}.png"
        draw(size).save(str(path), "PNG")
        print("wrote", path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
