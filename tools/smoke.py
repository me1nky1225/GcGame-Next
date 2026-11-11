"""无窗口冒烟测试：主题热切换、搜索、入队、切页。"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from gcm.bootstrap import build_context  # noqa: E402
from gcm.data.search import matches  # noqa: E402
from gcm.ui.main_window import MainWindow  # noqa: E402

app = QApplication([])
ctx = build_context(app)
win = MainWindow(ctx)
win.resize(1400, 900)
win.show()
app.processEvents()

ok = True


def check(label: str, value: bool) -> None:
    global ok
    ok = ok and value
    print(("PASS " if value else "FAIL ") + label)


check(f"已安装 {len(ctx.installed.items())} 条", len(ctx.installed.items()) >= 0)
check(f"在线库 {len(ctx.catalog.items())} 条", len(ctx.catalog.items()) > 0)
counts = ctx.catalog.counts()
print("     来源分布：" + "、".join(f"{k} {v}" for k, v in sorted(counts.items())))
check("存量旧库仍在（GCM 或 CT/小幸）", any(k in counts for k in ("GCM", "CT", "小幸")))

# 搜索：拼音首字母、中文、英文子串
check("拼音首字母 hshwk 命中黑神话", matches("hshwk", "黑神话：悟空"))
check("拼音首字母 eldenring 命中英文名", matches("eldenring", "Elden Ring"))
check("中文子串 黑神话", matches("黑神话", "黑神话：悟空"))
check("英文子串 elden", matches("elden", "Elden Ring"))

# 主题热切换（先固定到深色，避免上次运行遗留在浅色上）
_saved_theme = ctx.theme.name
ctx.theme.set_theme("dark")
app.processEvents()
ctx.theme.toggle()
app.processEvents()
check("切换到浅色", ctx.theme.name == "light")
check("浅色 QSS 生效", ctx.theme.tokens.bg in app.styleSheet())
ctx.theme.toggle()
app.processEvents()
check("切回深色", ctx.theme.name == "dark")
ctx.theme.set_theme(_saved_theme)
app.processEvents()

# 入队：无地址的 GCM 旧库条目应当被拦下，有地址的才进队列
from gcm.data.trainer import Trainer  # noqa: E402

legacy = next((t for t in ctx.catalog.items() if not t.url), None)
if legacy is not None:
    win._acquire(legacy)
    app.processEvents()
    check("无下载地址的条目被拦下", len(ctx.queue.tasks) == 0)

fake = Trainer(
    name="Smoke Test Trainer",
    source="FLiNG",
    kind="catalog",
    installed=False,
    url="http://127.0.0.1:9/smoke.zip",
)
task = ctx.queue.enqueue(fake)
app.processEvents()
check("队列里有 1 个任务", len(ctx.queue.tasks) == 1)
check("任务进入下载态", task.status in ("downloading", "failed"))
ctx.queue.remove(task)
app.processEvents()
check("移除后队列清空", len(ctx.queue.tasks) == 0)

# 「网页」类条目：只打开浏览器，不进下载队列
opened: list = []
win._open_web = lambda t: opened.append(t)  # type: ignore[method-assign]
external = next((t for t in ctx.catalog.items() if t.external and not t.installed), None)
if external is not None:
    win._acquire(external)
    app.processEvents()
    check(f"外部条目「{external.name}」走打开网页", len(opened) == 1 and not ctx.queue.tasks)
else:
    check("没有外部条目可测（跳过）", True)

# 关掉一个数据源之后，列表里不应再有该来源
saved = dict(ctx.settings.get("sources") or {})
before = len([t for t in ctx.catalog.items() if t.source == "小幸"])
ctx.settings.set("sources", {**saved, "xiaoxing": False})
ctx.catalog.reapply_sources()
after = len([t for t in ctx.catalog.items() if t.source == "小幸"])
check(f"关闭小幸源后其条目被隐藏（{before} → {after}）", after == 0)
ctx.settings.set("sources", saved)
ctx.catalog.reapply_sources()
check(
    f"恢复开关后小幸条目回来（{len([t for t in ctx.catalog.items() if t.source == '小幸'])} 条）",
    len([t for t in ctx.catalog.items() if t.source == "小幸"]) == before,
)

# 语言热切换：整棵控件树重建，文案应立即变化
from gcm.i18n import t  # noqa: E402

original_lang = ctx.settings.get("language", "zh_CN")
win._goto(0)
app.processEvents()
zh_nav = [b.text() for b in win.sidebar.buttons]
check(f"中文导航文案（{' / '.join(zh_nav)}）", "我的修改器" in zh_nav)

win._set_language("en_US")
app.processEvents()
en_nav = [b.text() for b in win.sidebar.buttons]
check(f"英文热切换（{' / '.join(en_nav)}）", "My trainers" in en_nav and "Settings" in en_nav)

win._set_language("zh_TW")
app.processEvents()
tw_nav = [b.text() for b in win.sidebar.buttons]
check(f"繁体热切换（{' / '.join(tw_nav)}）", "設定" in tw_nav and "下載佇列" in tw_nav)

win._set_language("zh_CN")
app.processEvents()
back_nav = [b.text() for b in win.sidebar.buttons]
check("切回简体后恢复中文文案", back_nav == zh_nav)
ctx.settings.set("language", original_lang)
check(f"漏翻兜底：未收录文案原样返回（{t('未收录的词')}）", t("未收录的词") == "未收录的词")

# 切页
for i in range(4):
    win._goto(i)
    app.processEvents()
check("四个页面均可切换", win.pages.currentIndex() == 3)

# 下载源地址：改一个地址应立即写进设置
page = win.settings_page
before = dict(ctx.settings.get("sourceUrls") or {})
page._url_edits["fling"].setText("https://mirror.example.com/")
page._emit_urls()
after = dict(ctx.settings.get("sourceUrls") or {})
check("下载源地址可改并落盘", after.get("fling") == "https://mirror.example.com")
check("改地址不影响其它源", after.get("ct") == before.get("ct"))
page._reset_urls()
check("恢复默认地址", ctx.settings.get("sourceUrls", {}).get("fling") == "https://flingtrainer.com")

# Steam 补全：缓存命中时应能直接写回中文名
entry = {"appid": 2358720, "en": "Black Myth: Wukong", "zh": "黑神话：悟空", "cover": ""}
applied = ctx.apply_steam(entry)
check("Steam 结果能写回数据", applied or ctx.steam.store.get("Black Myth: Wukong") is not None)

# 中文名开关：关掉后标题回到原名，打开后又是中文名
hit = next((t for t in ctx.catalog.items() if t.name_zh), None)
if hit is not None:
    from gcm.i18n import translator

    translator.show_chinese = True
    zh_title = hit.title
    win.settings_page.names_switch.setChecked(False)
    win.settings_page.names_switch.toggled.emit(False)
    app.processEvents()
    check("关掉中文名后回到原名", hit.title == hit.name)
    win.settings_page.names_switch.setChecked(True)
    win.settings_page.names_switch.toggled.emit(True)
    app.processEvents()
    check("重新打开后恢复中文名", hit.title == zh_title)

# 中文搜索：内置种子（Steam 中英对照）应让「黑神话」「影之刃零」直接命中
win._goto(1)
for query in ("黑神话", "影之刃零"):
    win.discover.set_query(query)
    app.processEvents()
    hits = win.discover.model.items()
    check(f"中文搜索「{query}」有结果", bool(hits))

# 删除一个条目：整条移走（不是只移 exe），其它行封面不受影响
import tempfile
from pathlib import Path as _Path
_tmp = _Path(tempfile.mkdtemp(prefix="gcm-smoke-"))
_saved_dir = ctx.installed.directory()
for _name in ("ELDEN RING", "Palworld"):
    _d = _tmp / _name
    _d.mkdir()
    (_d / f"{_name} Trainer.exe").write_bytes(b"MZ")
ctx.installed.set_directory(_tmp)
ctx.installed.refresh()
ctx.reapply_cached_steam()
_before = {t.name: bool(t.cover) for t in ctx.installed.items()}
ctx.installed.remove([t for t in ctx.installed.items() if t.name == "ELDEN RING"][0])
_after = {t.name: bool(t.cover) for t in ctx.installed.items()}
check("删除后条目真的消失", "ELDEN RING" not in _after)
check("删除不影响其它行封面", _after.get("Palworld") == _before.get("Palworld"))
ctx.installed.set_directory(_saved_dir)
ctx.installed.refresh()
import shutil as _shutil
_shutil.rmtree(_tmp, ignore_errors=True)

# 删除/重扫后封面与中文名要靠缓存贴回来（曾经的 bug：删一个后图标全变色块）
with_cover = [t for t in ctx.installed.items() if t.cover]
if with_cover:
    ctx.installed.refresh()
    app.processEvents()
    after = [t for t in ctx.installed.items() if t.cover]
    check("重扫安装目录后封面不丢", len(after) == len(with_cover))
    zh_before = [t for t in ctx.installed.items() if t.name_zh]
    ctx.installed.refresh()
    app.processEvents()
    check("重扫安装目录后中文名不丢", len([t for t in ctx.installed.items() if t.name_zh]) == len(zh_before))

# 后台补全中文名/封面时不能把列表滚回顶部（用户报的「滚一段自动回弹」）
win._goto(1)
app.processEvents()
bar = win.discover.view.verticalScrollBar()
bar.setValue(min(3000, bar.maximum()))
app.processEvents()
_start = bar.value()
_items = ctx.catalog.items()
for _t in _items[20:60]:
    _t.name_zh = _t.name_zh or "测试中文名"
    win._on_steam_enriched(_t.name, {"en": _t.name, "zh": _t.name_zh})
    app.processEvents()
check("后台补全后滚动位置不变", abs(bar.value() - _start) < 300)

# 侧边栏可收起，且状态记进设置（收起后列表拿到更多宽度）
_saved_sidebar = bool(ctx.settings.get("showSidebar", True))
win._apply_sidebar(True)
app.processEvents()
_w_wide = win.pages.width()
win._apply_sidebar(False)
app.processEvents()
check("收起侧边栏后列表变宽", win.pages.width() > _w_wide)
check("侧边栏状态已保存", ctx.settings.get("showSidebar") is False)
win._apply_sidebar(_saved_sidebar)
app.processEvents()
check("侧边栏状态可恢复", win.sidebar.isVisible() == _saved_sidebar)

# 详情面板也能收起，列表铺满整宽（用户要的「侧边栏开关」）
_saved_detail = bool(ctx.settings.get("showDetail", True))
win._apply_detail(True)
app.processEvents()
_w_detail = win.pages.width()
win._apply_detail(False)
app.processEvents()
check("收起详情面板后列表变宽", win.pages.width() > _w_detail)
check("详情面板状态已保存", ctx.settings.get("showDetail") is False)
win._apply_detail(_saved_detail)
app.processEvents()

# 切主题后所有容器都要跟着换底色（曾出现设置页滚动区留旧底色）
from PyQt6.QtGui import QPalette as _QP
from PyQt6.QtWidgets import QScrollArea as _QSA
win._goto(3)
app.processEvents()
_theme_before = ctx.theme.name
win._set_theme("light")
app.processEvents()
_scroll = win.settings_page.findChild(_QSA)
_holder = _scroll.widget() if _scroll else None
check("切到浅色后主题生效", ctx.theme.name == "light")
check(
    "切主题后滚动区底色跟着变",
    _holder is not None
    and _holder.palette().color(_QP.ColorRole.Window).name().lower() == ctx.tokens.bg.lower(),
)
check("设置页主题选中态同步", win.settings_page._theme_group.checkedId() == 1)
win._set_theme(_theme_before)
app.processEvents()
check("切回原主题", ctx.theme.name == _theme_before)

# 下载/安装目录可以手输（用户要的自定义）
_page = win.settings_page
_orig_dir = str(ctx.installed.directory())
check("目录输入框可编辑", not _page.path_edit.isReadOnly())
_scratch = _orig_dir + r"\_smoke_dir"
_page.path_edit.setText(_scratch)
_page._on_path_edited()
app.processEvents()
check("手输目录生效", str(ctx.installed.directory()) == _scratch)
check("手输目录写进设置", str(ctx.settings.get("downloadPath")) == _scratch)
check("下载队列跟着换目录", str(ctx.queue.download_dir) == _scratch)
_page.path_edit.setText("Z:\\definitely\\missing\\path")
_page._on_path_edited()
app.processEvents()
check("非法目录被拦下", str(ctx.installed.directory()) == _scratch)
check("非法目录给出提示", bool(_page._path_hint.text()))
_page.path_edit.setText(_orig_dir)
_page._on_path_edited()
app.processEvents()
check("目录可改回", str(ctx.installed.directory()) == _orig_dir)

# 收起的面板在切页后不该自己回来
win._apply_sidebar(False)
win._apply_detail(False)
win._goto(1)
app.processEvents()
win._goto(0)
app.processEvents()
check("切页后侧边栏仍是收起的", not win.sidebar.isVisible())
check("切页后详情面板仍是收起的", not win.detail.isVisible())
win._apply_sidebar(True)
win._apply_detail(True)
app.processEvents()

print("SMOKE OK" if ok else "SMOKE FAILED")
sys.exit(0 if ok else 1)
