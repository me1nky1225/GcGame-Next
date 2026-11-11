"""开发辅助：列出 UI 里出现的中文字面量，用来维护 i18n 词表。"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOTS = [
    "gcm/ui",
    "gcm/data/installed.py",
    "gcm/data/downloads.py",
    "gcm/data/trainer.py",
    "gcm/data/catalog.py",
    "gcm/util.py",
]


def has_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def main() -> int:
    found: dict[str, set[str]] = {}
    for root in ROOTS:
        path = pathlib.Path(root)
        files = sorted(path.rglob("*.py")) if path.is_dir() else [path]
        for file in files:
            source = file.read_text(encoding="utf-8-sig")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if has_cjk(node.value):
                        found.setdefault(str(file), set()).add(node.value)
    total = 0
    for file, values in found.items():
        total += len(values)
        print(f"--- {file}")
        for value in sorted(values):
            print("   " + value.replace("\n", "\\n"))
    print(f"共 {total} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
