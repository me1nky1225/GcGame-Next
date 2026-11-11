"""设计令牌（Design Tokens）。

所有颜色、圆角、间距集中在这里，QSS 与自绘控件都从这里取值，
杜绝 `style_sheet.py` 那种两套 290 行复制粘贴的写法。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Tokens:
    name: str

    # 表面
    bg: str
    rail: str
    card: str
    card_hover: str
    card_press: str
    line: str
    line_strong: str

    # 文字
    fg: str
    fg2: str
    muted: str
    on_accent: str

    # 强调色
    accent: str
    accent_hover: str
    accent_press: str
    accent_soft: str

    # 语义色
    ok: str
    warn: str
    danger: str
    danger_soft: str

    # 形状
    radius_s: int = 8
    radius_m: int = 12
    radius_l: int = 16

    # 间距
    s1: int = 4
    s2: int = 8
    s3: int = 12
    s4: int = 16
    s5: int = 24
    s6: int = 32

    font_family: str = "Microsoft YaHei UI"
    font_mono: str = "Cascadia Mono"

    # 来源徽章：source -> (前景, 背景, 边框)
    badges: dict = field(default_factory=dict)

    def badge(self, source: str) -> tuple[str, str, str]:
        return self.badges.get(
            source, self.badges.get("__default__", (self.fg2, self.card_hover, self.line_strong))
        )

    def cover(self, key: str) -> tuple[str, str]:
        """按条目名生成稳定的封面渐变色，避免依赖不存在的封面图。"""
        palettes = [
            ("#7c3aed", "#4338ca"),
            ("#0ea5e9", "#0e7490"),
            ("#f59e0b", "#b45309"),
            ("#ef4444", "#9f1239"),
            ("#10b981", "#047857"),
            ("#8b5cf6", "#6d28d9"),
            ("#64748b", "#334155"),
            ("#ec4899", "#9d174d"),
        ]
        return palettes[sum(key.encode("utf-8")) % len(palettes)]


DARK = Tokens(
    name="dark",
    bg="#0f1115",
    rail="#14161b",
    card="#191c22",
    card_hover="#1e222a",
    card_press="#232833",
    line="#262b34",
    line_strong="#323845",
    fg="#e8ebf2",
    fg2="#b3bac8",
    muted="#7f8798",
    on_accent="#ffffff",
    accent="#3b82f6",
    accent_hover="#4f8dfb",
    accent_press="#2f6fe0",
    accent_soft="#1e2a40",
    ok="#34d399",
    warn="#fbbf24",
    danger="#f87171",
    danger_soft="rgba(248, 113, 113, 0.14)",
    badges={
        "GCM": ("#93c5fd", "rgba(59, 130, 246, 0.16)", "rgba(59, 130, 246, 0.30)"),
        "FLiNG": ("#fca5a5", "rgba(239, 68, 68, 0.14)", "rgba(239, 68, 68, 0.28)"),
        "小幸": ("#fcd34d", "rgba(245, 158, 11, 0.14)", "rgba(245, 158, 11, 0.28)"),
        "CT": ("#6ee7b7", "rgba(16, 185, 129, 0.14)", "rgba(16, 185, 129, 0.28)"),
        "本地": ("#cbd5e1", "rgba(148, 163, 184, 0.14)", "rgba(148, 163, 184, 0.28)"),
        "__default__": ("#cbd5e1", "rgba(148, 163, 184, 0.14)", "rgba(148, 163, 184, 0.28)"),
    },
)

LIGHT = Tokens(
    name="light",
    bg="#f6f7f9",
    rail="#ffffff",
    card="#ffffff",
    card_hover="#f3f5f8",
    card_press="#e9edf4",
    line="#e4e7ee",
    line_strong="#d3d8e3",
    fg="#151922",
    fg2="#3d4557",
    muted="#78818f",
    on_accent="#ffffff",
    accent="#2563eb",
    accent_hover="#1d4ed8",
    accent_press="#1e40af",
    accent_soft="#e9effd",
    ok="#059669",
    warn="#b45309",
    danger="#dc2626",
    danger_soft="rgba(220, 38, 38, 0.09)",
    badges={
        "GCM": ("#1d4ed8", "rgba(37, 99, 235, 0.10)", "rgba(37, 99, 235, 0.26)"),
        "FLiNG": ("#b91c1c", "rgba(220, 38, 38, 0.09)", "rgba(220, 38, 38, 0.24)"),
        "小幸": ("#a16207", "rgba(202, 138, 4, 0.10)", "rgba(202, 138, 4, 0.24)"),
        "CT": ("#047857", "rgba(5, 150, 105, 0.10)", "rgba(5, 150, 105, 0.24)"),
        "本地": ("#475569", "rgba(71, 85, 105, 0.08)", "rgba(71, 85, 105, 0.22)"),
        "__default__": ("#475569", "rgba(71, 85, 105, 0.08)", "rgba(71, 85, 105, 0.22)"),
    },
)

THEMES = {"dark": DARK, "light": LIGHT}
