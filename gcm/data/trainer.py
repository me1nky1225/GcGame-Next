"""统一的修改器数据模型：本地已安装与在线库共用同一个结构。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..i18n import t, translator
from ..util import initials

_CJK = re.compile(r"[㐀-鿿]")


@dataclass
class Trainer:
    name: str
    path: Path | None = None
    home: Path | None = None  # 安装目录里的顶层条目（删除时整条移走，而不是只移 exe）
    source: str = "本地"
    author: str = ""
    version: str = ""
    kind: str = "exe"  # exe / ct / dir / archive / catalog
    updated: float = 0.0
    launched: int = 0
    last_launch: float = 0.0
    size_mb: float = 0.0
    desc: str = ""
    url: str = ""  # 在线项的来源页；下载时用它解析真实文件地址
    external: bool = False  # 只能打开官方网页（网盘/防盗链），应用内不下载
    installed: bool = True
    tags: list[str] = field(default_factory=list)
    # ---- Steam 补全（可能为空）----
    appid: int = 0
    name_zh: str = ""
    cover: str = ""  # 本地封面图路径
    alias: str = ""  # 用英文训练器文件名猜出的英文游戏名，供 Steam 查询

    # ---- 展示派生 ----
    @property
    def initials(self) -> str:
        return initials(self.title)

    @property
    def title(self) -> str:
        """中文界面优先显示中文名；原名本身就是中文时优先用原名。"""
        if translator.code == "en_US":
            return self.name
        if _CJK.search(self.name):
            return self.name
        if translator.show_chinese and self.name_zh:
            return self.name_zh
        return self.name

    @property
    def alt_title(self) -> str:
        """另一种语言的名字，用于副标题/详情，避免信息丢失。"""
        if not self.name_zh:
            return ""
        other = self.name if self.title == self.name_zh else self.name_zh
        return "" if other == self.title else other

    @property
    def cover_key(self) -> str:
        return self.name

    @property
    def has_update(self) -> bool:
        return "可更新" in self.tags

    def subtitle(self) -> str:
        parts: list[str] = []
        alt = self.alt_title
        if alt and alt != self.title:
            parts.append(alt)
        if self.author and self.author.lower() not in (self.source.lower(), ""):
            parts.append(self.author)
        if self.version:
            parts.append(f"v{self.version}")
        if self.size_mb:
            parts.append(f"{self.size_mb:.0f} MB")
        if self.launched:
            parts.append(t("使用过 {n} 次").format(n=self.launched))
        return " · ".join(parts) or ("已安装" if self.installed else "在线")

    def search_text(self) -> str:
        return " ".join(
            [self.name, self.name_zh, self.desc, self.author, self.source, self.version]
        ).lower()
