"""内置矢量图标：用 QPainter 现画，不依赖 PNG 资源与 devicePixelRatio 补丁。"""
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def _pen(painter: QPainter, color: str, width: float = 1.7) -> None:
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)


def _pixmap(name: str, color: str, size: int) -> QPixmap:
    dpr = 2.0
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.scale(size / 24.0, size / 24.0)
    _pen(p, color)

    if name == "search":
        p.drawEllipse(QRectF(4.5, 4.5, 13.0, 13.0))
        p.drawLine(QPointF(16.6, 16.6), QPointF(20.0, 20.0))
    elif name == "plus":
        p.drawLine(QPointF(12, 5), QPointF(12, 19))
        p.drawLine(QPointF(5, 12), QPointF(19, 12))
    elif name == "sun":
        p.drawEllipse(QRectF(7.6, 7.6, 8.8, 8.8))
        for i in range(8):
            import math

            a = math.radians(i * 45)
            p.drawLine(
                QPointF(12 + 7.4 * math.cos(a), 12 + 7.4 * math.sin(a)),
                QPointF(12 + 9.8 * math.cos(a), 12 + 9.8 * math.sin(a)),
            )
    elif name == "moon":
        path = QPainterPath()
        path.setFillRule(Qt.FillRule.OddEvenFill)
        path.addEllipse(QRectF(3.8, 3.8, 16.4, 16.4))
        path.addEllipse(QRectF(10.2, -1.4, 16.0, 16.0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        p.drawPath(path)
        _pen(p, color)
    elif name == "play":
        path = QPainterPath()
        path.moveTo(9.2, 6.4)
        path.lineTo(18.4, 12.0)
        path.lineTo(9.2, 17.6)
        path.closeSubpath()
        p.setBrush(QColor(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(path)
    elif name == "folder":
        path = QPainterPath()
        path.moveTo(3.6, 6.9)
        path.lineTo(9.2, 6.9)
        path.lineTo(11.2, 9.4)
        path.lineTo(20.4, 9.4)
        path.lineTo(20.4, 18.2)
        path.lineTo(3.6, 18.2)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "trash":
        p.drawLine(QPointF(4.5, 7.2), QPointF(19.5, 7.2))
        p.drawLine(QPointF(9.6, 7.2), QPointF(9.6, 4.8))
        p.drawLine(QPointF(9.6, 4.8), QPointF(14.4, 4.8))
        p.drawLine(QPointF(14.4, 4.8), QPointF(14.4, 7.2))
        path = QPainterPath()
        path.moveTo(6.6, 7.4)
        path.lineTo(7.4, 19.4)
        path.lineTo(16.6, 19.4)
        path.lineTo(17.4, 7.4)
        p.drawPath(path)
    elif name == "grid":
        for x, y in ((4.0, 4.0), (13.4, 4.0), (4.0, 13.4), (13.4, 13.4)):
            p.drawRoundedRect(QRectF(x, y, 6.6, 6.6), 2.0, 2.0)
    elif name == "compass":
        p.drawEllipse(QRectF(3.5, 3.5, 17.0, 17.0))
        path = QPainterPath()
        path.moveTo(15.6, 8.4)
        path.lineTo(10.9, 10.9)
        path.lineTo(8.4, 15.6)
        path.lineTo(13.1, 13.1)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "download":
        p.drawLine(QPointF(12, 4.2), QPointF(12, 14.6))
        p.drawLine(QPointF(7.6, 10.6), QPointF(12, 15.0))
        p.drawLine(QPointF(16.4, 10.6), QPointF(12, 15.0))
        p.drawLine(QPointF(4.6, 19.2), QPointF(19.4, 19.2))
    elif name == "settings":
        for y in (7.0, 12.0, 17.0):
            p.drawLine(QPointF(4.4, y), QPointF(19.6, y))
        p.setBrush(QColor(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(9.2, 7.0), 2.0, 2.0)
        p.drawEllipse(QPointF(15.2, 12.0), 2.0, 2.0)
        p.drawEllipse(QPointF(11.4, 17.0), 2.0, 2.0)
        _pen(p, color)
    elif name == "sidebar":
        # 一个带左侧竖栏的圆角方块：表示「显示/隐藏侧边栏」
        p.drawRoundedRect(QRectF(3.6, 5.2, 16.8, 13.6), 2.6, 2.6)
        p.drawLine(QPointF(9.4, 5.6), QPointF(9.4, 18.4))
    elif name == "panel_right":
        p.drawRoundedRect(QRectF(3.6, 5.2, 16.8, 13.6), 2.6, 2.6)
        p.drawLine(QPointF(14.6, 5.6), QPointF(14.6, 18.4))
    elif name == "chevron_down":
        p.drawLine(QPointF(7.2, 10.0), QPointF(12, 14.8))
        p.drawLine(QPointF(16.8, 10.0), QPointF(12, 14.8))
    elif name == "refresh":
        import math

        rect = QRectF(4.6, 4.6, 14.8, 14.8)
        p.drawArc(rect, 70 * 16, 290 * 16)
        theta = math.radians(0)
        cx, cy, r = 12.0, 12.0, 7.4
        px, py = cx + r * math.cos(theta), cy - r * math.sin(theta)
        tx, ty = -math.sin(theta), -math.cos(theta)
        nx, ny = -ty, tx
        tri = QPainterPath()
        tri.moveTo(px + tx * 3.0, py + ty * 3.0)
        tri.lineTo(px - tx * 0.6 + nx * 2.2, py - ty * 0.6 + ny * 2.2)
        tri.lineTo(px - tx * 0.6 - nx * 2.2, py - ty * 0.6 - ny * 2.2)
        tri.closeSubpath()
        p.setBrush(QColor(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(tri)
    elif name == "check":
        p.drawLine(QPointF(5.2, 12.4), QPointF(9.8, 17.0))
        p.drawLine(QPointF(9.8, 17.0), QPointF(18.8, 7.2))
    else:
        p.drawEllipse(QRectF(6, 6, 12, 12))

    p.end()
    return pm


def icon(name: str, color: str, size: int = 18) -> QIcon:
    return QIcon(_pixmap(name, color, size))


def pixmap(name: str, color: str, size: int = 18) -> QPixmap:
    return _pixmap(name, color, size)
