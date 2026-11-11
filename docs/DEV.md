# GCM Next · 开发笔记

> 面向改代码的人：模块清单、设计系统、与旧版的差异、每个坑的成因与修法。
> 面向使用者的介绍见仓库根目录的 [README](../README.md)。

---

# GCM Next — 修改器管理器（PoC）

对 `E:\PcApp\Game Cheats Manager`（dyang886/Game-Cheats-Manager 2.3.2 冻结版）的前端重构原型。
按方案 B 重写：**PyQt6 + 设计 token 驱动主题 + 模型/委托自绘列表 + 单窗口四页导航**，
目标是把「两个搜索框 + 菜单栏」的旧界面换成可扩展的现代桌面应用骨架。

![主界面](docs/shots/app-window.png)

## 现在能做什么

| 页面 | 能力 |
| --- | --- |
| 我的修改器 | 扫描真实安装目录（`%APPDATA%\GCM Trainers`），卡片列表、**Steam 封面与中文名**、来源徽章、排序、搜索（中文/拼音/首字母）、启动并计数、打开目录、删除（进回收目录，不真删） |
| 发现 | 四源合库 **3187 条**：本地旧库 273 + FLiNG 抓取 712 + CT（the-cheat-script）2141 + 小幸 61；分源缓存到磁盘，按数据源开关过滤；**英文条目自动补中文名（可搜「黑神话」「影之刃零」）**；FLiNG 条目可直接下载，CT 条目解析 Yandex 直链，小幸只提供官方网页 |
| 下载队列 | 真实下载：解析下载页 → 带 Referer 直链 → 断点续传 → zip/7z/rar 解压 → 写入 `gcm_info.json` → 出现在「我的修改器」；支持暂停/继续/重试/取消，底部常驻队列条 |
| 设置 | 深/浅色实时切换、**简/繁/英三语热切换（无需重启）**、库目录、四个数据源开关、**下载源地址（可改成镜像/反代）**、关于 |

顶栏 Ctrl+K 聚焦搜索、F5 刷新、Ctrl+1..4 切页；窗口尺寸、主题、语言持久化到 `%APPDATA%\GCM Next\settings.json`。

![发现页](docs/shots/discover-dark.png)
![搜中文「黑神话」](docs/shots/discover-search.png)
![下载队列](docs/shots/downloads-dark.png)
![浅色主题](docs/shots/library-light.png)
![英文界面](docs/shots/library-en.png)
![繁体界面](docs/shots/library-tw.png)

## 运行

```bat
run.bat            :: 首次会自动建 .venv 并装依赖
```

或手动：

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

要求 Python 3.10+（开发环境 3.12.9），依赖 PyQt6 6.9.1 / pypinyin / rapidfuzz。

## 打包成 exe

```bat
.venv\Scripts\python.exe tools\make_icon.py     :: 生成 assets/icon-*.png（改了 Logo 才需要跑）
.venv\Scripts\python.exe tools\build.py         :: PyInstaller onedir → dist\GCM Next\GCM Next.exe
```

- 采用 **onedir**（不是 onefile）：Qt 不需要每次解压到临时目录，冷启动快，杀软误报也少。
- 产物约 **77 MB**（`GCM Next.exe` 2.1 MB + `_internal/`）：构建末尾会剪掉用不到的
  `opengl32sw.dll`（软件 OpenGL，19.7 MB）、`Qt6Pdf.dll`、`Qt6Network.dll`——界面全是 raster 绘制，不需要它们；
  剪完已实测启动、渲染、下载安装链路都正常。
- `assets/` 与 `vendor/7z/` 通过 `--add-data` 打进包里，运行时用 `gcm.paths.bundled_dir()`
  （冻结后是 `sys._MEIPASS`）定位；`installer.find_7z()` 优先用它，用户机器不必装 7-Zip。
- 版本信息由 `tools/build.py` 生成的 `build/version_info.txt` 注入（0.1.0-poc）。
- 分发时整个 `dist\GCM Next\` 目录一起拷走，双击 `GCM Next.exe` 即可（不需要装 Python）。

## 开发工具

```bat
.venv\Scripts\python.exe tools\smoke.py                     :: 无窗口冒烟测试（54 项：搜索/主题/入队/三语热切换/数据源开关/源地址/Steam 回写/切页）
.venv\Scripts\python.exe tools\e2e.py                       :: 端到端：抓 FLiNG 索引 → 真实下载一个小训练器 → 解压安装 → 校验列表 → 本地 Range 服务验证暂停/续传
.venv\Scripts\python.exe tools\shot.py 0 light docs\shots\library-light.png
                                                            :: 0=我的修改器 1=发现 2=下载队列 3=设置〔第 4 个参数可传 zh_CN/zh_TW/en_US〕
.venv\Scripts\python.exe tools\shot_window.py out.png 1     :: 抓含原生标题栏的整窗截图
.venv\Scripts\python.exe tools\scan_i18n.py                 :: 扫出还没收进 i18n 词表的中文字面量
```

## 目录结构

```
main.py                 程序入口（from gcm.bootstrap import run）
gcm/
  bootstrap.py          组装 AppContext → MainWindow → app.exec
  context.py            AppContext(settings, theme, installed, catalog, queue)
  paths.py              %APPDATA%\GCM Next 相关路径、旧版目录常量
  settings_store.py     JSON 设置，QObject + changed 信号
  i18n.py               三语词表（中文原文为键）+ Translator 单例 + t()，切换即整树重建
  util.py               humanize / fmt_size / initials
  theme/
    tokens.py           深/浅两套 token（颜色、圆角、间距、字体、徽章、封面渐变）
    qss.py              由 token 生成整份 QSS
    manager.py          ThemeManager：切主题即换 stylesheet + palette，无需重启
  data/
    trainer.py          Trainer 数据模型（本地/在线共用，带 url/appid/name_zh/cover）
    steam.py            Steam 商店查询：名字 → appid / 中英双名 / 封面（磁盘缓存 + 否定缓存）
    enrich.py           SteamEnricher 后台线程：只在列表可见或中文搜空时查询 + 启动后后台批量补 300 条，串行 + 限速
    installed.py        扫描已安装目录、启动、删除、usage 计数
    catalog.py          在线库：旧库 JSON + 三源抓取 + 分源磁盘缓存 + 合并去重 + 开关过滤
    sources/fling.py    FLiNG 索引解析、下载页解析、请求头
    sources/ct.py       the-cheat-script：Blogger JSON feed → Yandex Disk 直链解析
    sources/xiaoxing.py 小幸：WordPress REST API，条目只提供官方网页
    downloader.py       DownloadJob：解析 → Range 续传 → 进度/阶段信号 → 安装
    installer.py        zip/7z/rar 解压、zip-slip 校验、入口 exe 选择、写 gcm_info.json
    downloads.py        下载队列：并发 2、暂停/继续/取消/重试、汇总速度
    search.py           子串 → 拼音首字母 → rapidfuzz 模糊
  net/http.py           带 UA/Cookie 的请求封装（gzip、Content-Disposition 文件名）
  ui/
    icons.py            QPainter 现画的矢量图标（无 PNG 资源）
    sidebar.py topbar.py main_window.py
    widgets/            trainer_list（模型+委托）、detail_panel、queue_bar、search_field、switch、toast
    pages/              library、discover、downloads、settings
tools/                  smoke.py（无窗口冒烟）、e2e.py（真实下载+安装+暂停续传）、shot.py、shot_window.py、
                        grab_window.py（抓任意进程窗口）、scan_i18n.py、make_icon.py、build.py（PyInstaller 打包）
assets/                 icon-*.png（QPainter 现画）+ app.ico
vendor/7z/              随包分发的 7-Zip（解 rar/7z 用；LGPL）
docs/shots/             深/浅两套页面截图与真实窗口截图
```

## 设计系统

- 颜色：`bg / rail / card / card_hover / line / line_strong / fg / fg2 / muted / accent / accent_soft / ok / warn / danger`
- 尺寸：`radius_s=8 / radius_m=12 / radius_l=16`，间距 `s1..s6`，字体 `Microsoft YaHei UI` + `Cascadia Mono`（路径框）
- 组件：`#Primary / #Ghost / #IconButton / #NavButton / #Chip / #SortBtn / #Card / #PathBox / #Kbd / #EmptyTitle` 等，全部在 `theme/qss.py` 里由 token 拼出，业务代码不再写内联样式
- 徽章：GCM 蓝 / FLiNG 红 / 小幸 琥珀 / CT 绿，浅色主题自动换深一档前景色保证对比度
- 封面：按名字查 Steam（`storesearch` 拿 appid + 中文名、`appdetails` 拿 `header_image`），图片缓存到 `%APPDATA%\GCM Next\covers\<appid>.jpg`；
  随包带 `gcm/data/steam_seed.json`（44 个热门游戏的中英名 + appid + 封面地址），**断网也能用中文搜到「黑神话」「影之刃零」**；
  查不到时退回 `tokens.cover(key)` 的 8 套渐变 + 首字母（按名称哈希稳定取色）

## 与旧版的差别（这次重构到底改了什么）

| 维度 | 旧版 2.3.2 | GCM Next PoC |
| --- | --- | --- |
| 布局 | 左右两个同款搜索框 + 纯文字列表 + 底部两个全宽按钮 | 左侧导航 + 顶栏搜索 + 卡片列表 + 右侧详情面板 + 底部队列条 |
| 列表行 | 一行一个文件名 | 46px 封面、标题、来源徽章、作者、版本、大小、使用次数、上次启动、启动胶囊 |
| 主题 | 两份约 290 行、结构重复的 QSS 字符串，切主题要重启 | 单份模板 + token，运行时热切换（含 Windows 标题栏深色） |
| 状态 | 模块级全局 `settings` dict + 88 处直接读写 | `SettingsStore` 单例 + 信号；数据层 `InstalledIndex / Catalog / DownloadQueue` 各自发信号 |
| 图标 | 5 张 PNG（主题/箭头/勾选），换色要重出图 | QPainter 现画，颜色随 token 传参 |
| 搜索 | 子串匹配 | 子串 → 拼音首字母 → 模糊（rapidfuzz） |
| 下载进度 | 把进度伪装成列表项插进结果列表，开始下载会清空搜索结果 | 独立队列模型 + 底部队列条，互不干扰 |
| i18n | gettext + 三种语言的 .po/.mo，切语言要重启 | `gcm/i18n.py` 单文件词表（中文原文为键，值为英文/繁体），切语言发信号重建控件树，即时生效 |
| 数据源 | 四个来源的 JSON 都从 GCM 私有签名 CDN 拉 | FLiNG/CT/小幸 各自直连公开站点（Blogger feed / WordPress API / 站点 HTML），分源缓存，可单独开关 |

## PoC 里哪些是「真的」、哪些是「壳」

真：已安装目录扫描、`gcm_info.json` 解析、启动/打开目录/删除、旧库读取与清洗（去重、去替换字符）、搜索算法、主题热切换、
三语热切换、设置持久化、导入 zip 解压、FLiNG 在线索引抓取（712 条）、CT 索引抓取（2141 条）、小幸索引抓取（61 条）、
分源缓存与开关过滤、FLiNG 训练器真实下载（Referer 直链 + Range 续传 + 暂停/重试）、zip/7z/rar 解压与安装、下载完成后自动刷新列表与 Toast 提示、
Steam 中文名与封面补全（含中文搜索兜底：搜不到时查一次 Steam，把中文名写回再筛）、下载源地址可配置。
壳（有意留白）：GCM 源下载（官方走私有签名服务 `get_signed_download_url`，本仓库版本 `SIGNED_URL_DOWNLOAD_ENDPOINT = ''`，无签名服务无法复刻，点「获取」会明确提示）、
小幸条目的自动下载（正文只给 MediaFire/百度网盘，前者对脚本 403、后者要登录 → 只打开官方网页）、CT 下载在 Yandex 限流（HTTP 429）时需要过一会儿再试、自动更新与开机自启。

## 下一步（按优先级）

1. 已安装侧补「有更新」对比与按来源筛选（元数据已在 `gcm_info.json` 里）
2. 打包发布：PyInstaller onedir + 应用图标，替换 `E:\PcApp\Game Cheats Manager` 时迁移旧设置
3. 健壮性：下载并发上限可配、7z 缺失时的纯 zip 兜底提示、错误上报到日志文件
4. GCM 源：如果拿到签名服务，接上 `catalog.py` 里预留的下载分支
5. 提示与引导：首次启动的数据源说明、下载失败的可操作提示（现在只有文案）

## 开发注记

- **`%APPDATA%` 重定向**：`gcm/paths.py` 的 `_canonical()` 会把数据目录解析成真实路径。理由有两个：
  Roaming 可能被企业策略重定向/是目录联接；用 Microsoft Store 版 Python 运行时，写入 `%APPDATA%` 会被重定向到
  `...\Packages\PythonSoftwareFoundation.Python.*\LocalCache\...`，本进程看得见、子进程（7z）看不见。
  解析后 7z 才能读到下载的临时文件。PyInstaller 冻结版不会触发这条路径。
- **FLiNG 直链**：最后一跳必须带 `Referer: https://flingtrainer.com/` + 浏览器 UA，否则 403。
- **GCM 源不可下载**：上游 `src/scripts/config.py` 的签名端点来自私有 `secret_config`，缺失时抛
  `RuntimeError('Request signing is unavailable in this build')`，所以「获取」只对 FLiNG 条目可用。
- **CT 直链**：文章里的 Yandex Disk 公共链接经 `cloud-api.yandex.net` 换直链，必须带 UA；该接口会按出口 IP 整体限流
  （`{"error":"TooManyRequestsError"}`，HTTP 429），所以下载失败时提示「过几分钟再试」而不是重试到底。
- **小幸**：WordPress REST API 只给标题与文章链接；正文是 MediaFire/百度网盘，脚本拿不到 → 条目标记 `external=True`，
  「获取」变「网页」，详情面板变「打开网页 / 复制链接」。
- **Steam 补全**：`storesearch` 用 `l=schinese&cc=cn` 搜中文名能同时拿到 appid 与封面；用英文名搜则 `l=english&cc=us`。
  注意它是**整词匹配**：`黑神话` 搜不到、`黑神话：悟空` 才行，所以中文搜索依赖「本地 name_zh 索引」而不是现场查询；
  索引来源三处：内置种子 → 后台 warm（启动后 300 条）→ 列表可见行的 urgent 请求。网络超时**不写否定缓存**（只有真的搜不到才缓存 6 小时）。
  两个接口在本机偶尔整段超时（8s 超时 + 重试一次），所以做成后台线程按需查询、结果与「查不到」都进缓存（6 小时内不重试），
  列表照常用渐变兜底，不阻塞界面。
- **列表项重建**：`InstalledIndex.refresh()` 每次都新建 `Trainer` 对象，而 Steam 中文名/封面只存在内存里，
  所以刷新末尾要过一遍 `ctx.reapply_cached_steam()`（`bootstrap` 里挂到 `installed.on_rebuild`），
  否则删掉一个修改器后其它行的图标会全部退回色块。删除时移动的是安装目录里的**顶层条目**（`trainer.home`），
  不是 exe，否则目录型修改器会留下空壳条目。

- **下载目录可直接编辑**：设置页「修改器库 → 下载与安装目录」不再是只读框，
  可以直接输入（支持 `%APPDATA%` 这类环境变量与 `~`），回车后自动建目录、写设置、
  同步下载队列的目标目录并刷新列表；非法路径会红字提示并退回上一个目录。

- **两侧面板都能收**：顶栏最左的方块按钮 / `Ctrl+B` 收起左侧导航（改由按钮弹出的页面菜单导航）；
  顶栏右侧的方块按钮 / `Ctrl+D` 收起详情面板。两处都能在「设置 → 外观」里切换，状态存 `showSidebar` / `showDetail`。

- **切主题要重刷整棵树**：`ThemeManager.apply()` 除了换全局 QSS 与 palette，还会对
  `QApplication.allWidgets()` 逐个 `setPalette` + `unpolish/polish`（约 95 ms）；
  QSS 里给 `QScrollArea`、`QScrollArea > QWidget > QWidget`、`QStackedWidget` 显式上底色，
  否则滚动区会留着上一个主题的底色（曾出现设置页切浅色后一大块黑底）。

- **刷新别重置模型**：`refresh()` 先比较条目名列表，一致就只 `model.refresh()`（dataChanged 重画），
  不一致才 `set_items` 并手动恢复 `verticalScrollBar` 位置。否则后台补中文名/封面会让列表滚回顶部。

- **下载源地址**：`settings.json` 里的 `sourceUrls` 会作为 `base` 传给三个源的抓取函数（FLiNG 用 `{base}/all-trainers/`、
  CT 用 `{base}/feeds/posts/default`、小幸用 `{base}/wp-json/wp/v2/posts`），改成反代后点顶栏刷新即可重新抓取。
