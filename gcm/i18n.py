"""运行时文案表：中 / 繁 / 英三语，切换不需要重启。

设计要点：
* 词表以**简体中文原文**为键，值依次是 (English, 繁體中文)。写代码时直接
  `t("启动")`，找不到就回落到原文，所以漏翻只会露出中文，不会崩。
* 需要插值的句子把占位符写进键里，例如 `t("{n} 分钟前").format(n=3)`。
* 只在构造界面和更新文案时调用 `t()`；界面重建（切换语言）由主窗口负责。
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

LANGS = [("zh_CN", "简体中文"), ("zh_TW", "繁體中文"), ("en_US", "English")]
DEFAULT_LANG = "zh_CN"

# 中文原文: (英文, 繁体)
TABLE: dict[str, tuple[str, str]] = {
    # ---------- 侧栏 / 顶栏 ----------
    "我的修改器": ("My trainers", "我的修改器"),
    "发现": ("Discover", "探索"),
    "下载队列": ("Downloads", "下載佇列"),
    "设置": ("Settings", "設定"),
    "管理": ("Manage", "管理"),
    "修改器管理器": ("Trainer manager", "修改器管理器"),
    "数据库未加载": ("Database not loaded", "資料庫未載入"),
    "数据库 {n} 个修改器": ("{n} trainers in the index", "資料庫 {n} 個修改器"),
    "导入修改器": ("Import", "匯入修改器"),
    "刷新列表（F5）": ("Refresh (F5)", "重新整理（F5）"),
    "切换到浅色主题": ("Switch to light theme", "切換到淺色主題"),
    "切换到深色主题": ("Switch to dark theme", "切換到深色主題"),
    "搜索游戏或修改器": ("Search games or trainers", "搜尋遊戲或修改器"),
    "搜索已安装的修改器（拼音或首字母）": (
        "Search installed trainers",
        "搜尋已安裝的修改器",
    ),
    "搜索在线修改器（拼音或首字母）": (
        "Search online trainers",
        "搜尋線上修改器",
    ),
    "搜索下载任务": ("Search downloads", "搜尋下載任務"),
    # ---------- 列表 / 页面 ----------
    "全部": ("All", "全部"),
    "按更新时间排序": ("Sort by updated", "依更新時間排序"),
    "按名称排序": ("Sort by name", "依名稱排序"),
    "启动": ("Launch", "啟動"),
    "获取": ("Get", "取得"),
    "网页": ("Web", "網頁"),
    "详情": ("Details", "詳情"),
    "打开网页": ("Open page", "開啟網頁"),
    "复制链接": ("Copy link", "複製連結"),
    "打开所在目录": ("Open folder", "開啟資料夾"),
    "删除（移到回收站）": ("Delete (to recycle bin)", "刪除（移至資源回收筒）"),
    "去发现": ("Browse trainers", "前往探索"),
    "还没有安装修改器": ("No trainers installed yet", "尚未安裝修改器"),
    "扫描目录里还没有修改器": ("Nothing in the trainer folder yet", "掃描目錄裡還沒有修改器"),
    "换个关键词试试": ("Try another keyword", "換個關鍵字試試"),
    "没有匹配的修改器": ("No matching trainers", "沒有符合的修改器"),
    "换个关键词试试，或检查「设置 → 数据源」是否开启": (
        "Try another keyword, or check Sources in Settings",
        "換個關鍵字試試，或檢查「設定 → 資料來源」是否開啟",
    ),
    "在「发现」里获取，或点右上角「导入修改器」添加本地文件": (
        "Get one from Discover, or import a local file",
        "在「探索」裡取得，或點右上角「匯入修改器」新增本機檔案",
    ),
    "在「发现」里点「获取」，下载任务会出现在这里": (
        "Pick Get in Discover and downloads show up here",
        "在「探索」裡點「取得」，下載任務會出現在這裡",
    ),
    "后台下载与解压进度": ("Background downloads and extraction", "背景下載與解壓縮進度"),
    "队列是空的": ("Queue is empty", "佇列是空的"),
    "清除已完成": ("Clear finished", "清除已完成"),
    "暂停": ("Pause", "暫停"),
    "继续": ("Resume", "繼續"),
    "移除": ("Remove", "移除"),
    "重试": ("Retry", "重試"),
    "完成": ("Done", "完成"),
    "排队中": ("Queued", "排隊中"),
    "安装中": ("Installing", "安裝中"),
    "下载失败": ("Download failed", "下載失敗"),
    "解压并写入库目录…": ("Extracting into the library…", "解壓縮並寫入庫目錄…"),
    "连接中…": ("Connecting…", "連線中…"),
    "准备中…": ("Preparing…", "準備中…"),
    "下载中…": ("Downloading…", "下載中…"),
    "等待开始": ("Waiting to start", "等待開始"),
    "继续下载…": ("Resuming…", "繼續下載…"),
    "已暂停": ("Paused", "已暫停"),
    "已暂停 · {size}": ("Paused · {size}", "已暫停 · {size}"),
    "已完成 · {size} MB · 已加入「我的修改器」": (
        "Done · {size} MB · added to My trainers",
        "已完成 · {size} MB · 已加入「我的修改器」",
    ),
    "{n} 个任务 · {m} 个进行中": ("{n} tasks · {m} active", "{n} 個任務 · {m} 個進行中"),
    "已取消": ("Cancelled", "已取消"),
    "已完成 · 已加入「我的修改器」": (
        "Done · added to My trainers",
        "已完成 · 已加入「我的修改器」",
    ),
    # ---------- 设置页 ----------
    "外观": ("Appearance", "外觀"),
    "深色": ("Dark", "深色"),
    "浅色": ("Light", "淺色"),
    "界面语言": ("Language", "介面語言"),
    "修改器库": ("Trainer library", "修改器庫"),
    "下载与安装目录": ("Download & install folder", "下載與安裝目錄"),
    "浏览…": ("Browse…", "瀏覽…"),
    "修改器会下载并安装到这个目录，路径可以直接编辑": (
        "Trainers are downloaded and installed here — edit the path directly",
        "修改器會下載並安裝到這個目錄，路徑可以直接編輯",
    ),
    "目录不存在，已自动创建": ("Folder did not exist - created it", "目錄不存在，已自動建立"),
    "无法创建或访问该目录": ("Cannot create or access that folder", "無法建立或存取該目錄"),
    "下载目录已改为 {path}": ("Download folder changed to {path}", "下載目錄已改為 {path}"),
    "正在进行的下载仍会写入旧目录": (
        "Downloads already running keep writing to the old folder",
        "進行中的下載仍會寫入舊目錄",
    ),
    "打开": ("Open", "開啟"),
    "数据源": ("Sources", "資料來源"),
    "GCM 数据库": ("GCM database", "GCM 資料庫"),
    "官方维护的修改器索引，含版本号": (
        "Official index with version numbers",
        "官方維護的修改器索引，含版本號",
    ),
    "网页抓取，作者 Hexinton 等": ("Scraped from the site", "網頁擷取，作者 Hexinton 等"),
    "小幸": ("XiaoXing", "小幸"),
    "国产修改器，需要解锁": ("Chinese trainer site, needs unlock", "國產修改器，需要解鎖"),
    "Cheat Table": ("Cheat Table", "Cheat Table"),
    "the-cheat-script 社区脚本": (
        "Community scripts from the-cheat-script",
        "the-cheat-script 社群腳本",
    ),
    "关于": ("About", "關於"),
    "数据目录：": ("Data folder:", "資料目錄："),
    "显示侧边栏": ("Show sidebar", "顯示側邊欄"),
    "显示详情面板": ("Show details panel", "顯示詳情面板"),
    "关掉后列表铺满整宽，选中项仍会在后台同步（Ctrl+D）": (
        "Lets the list use the full width; the selection still syncs in the background (Ctrl+D)",
        "關掉後列表鋪滿整寬，選中項仍會在後台同步（Ctrl+D）",
    ),
    "隐藏详情面板（Ctrl+D）": ("Hide details panel (Ctrl+D)", "隱藏詳情面板（Ctrl+D）"),
    "显示详情面板（Ctrl+D）": ("Show details panel (Ctrl+D)", "顯示詳情面板（Ctrl+D）"),
    "关掉后给列表腾出空间，Ctrl+B 随时切换": (
        "Gives the list more room; toggle anytime with Ctrl+B",
        "關掉後給列表騰出空間，Ctrl+B 隨時切換",
    ),
    "隐藏侧边栏（Ctrl+B）": ("Hide sidebar (Ctrl+B)", "隱藏側邊欄（Ctrl+B）"),
    "显示侧边栏（Ctrl+B）": ("Show sidebar (Ctrl+B)", "顯示側邊欄（Ctrl+B）"),
    "语言切换即时生效，无需重启": (
        "Switching applies instantly, no restart",
        "語言切換即時生效，無需重新啟動",
    ),
    "重构自 dyang886/Game-Cheats-Manager · PyQt6 · 设计系统驱动主题": (
        "Rebuilt from dyang886/Game-Cheats-Manager · PyQt6 · token-driven theming",
        "重構自 dyang886/Game-Cheats-Manager · PyQt6 · 設計系統驅動主題",
    ),
    "选择修改器目录": ("Choose trainer folder", "選擇修改器目錄"),
    # ---------- 详情面板 ----------
    "来源": ("Source", "來源"),
    "类型": ("Type", "類型"),
    "大小": ("Size", "大小"),
    "上次启动": ("Last launch", "上次啟動"),
    "启动次数": ("Launches", "啟動次數"),
    "从未": ("Never", "從未"),
    "独立 exe": ("Standalone exe", "獨立 exe"),
    "目录型": ("Folder", "目錄型"),
    "压缩包": ("Archive", "壓縮檔"),
    "目录": ("Folder", "目錄"),
    "未选择": ("Nothing selected", "未選擇"),
    "从左侧列表选择一个修改器": ("Pick a trainer from the list", "從左側清單選擇一個修改器"),
    "在线资源": ("Online resource", "線上資源"),
    "在线资源，下载后可离线使用": (
        "Online — offline once downloaded",
        "線上資源，下載後可離線使用",
    ),
    "已安装": ("Installed", "已安裝"),
    "本地": ("Local", "本機"),
    "在线": ("Online", "線上"),
    "可更新": ("Update", "可更新"),
    # ---------- 队列条 / 时间 ----------
    "下载队列空闲": ("Queue idle", "下載佇列閒置"),
    "队列 {n} · {speed}": ("Queue {n} · {speed}", "佇列 {n} · {speed}"),
    "队列 {n}": ("Queue {n}", "佇列 {n}"),
    "正在下载 {name}": ("Downloading {name}", "正在下載 {name}"),
    "正在安装 {name}": ("Installing {name}", "正在安裝 {name}"),
    "已完成 {n}": ("{n} finished", "已完成 {n}"),
    "失败 {n}": ("{n} failed", "失敗 {n}"),
    "空闲": ("Idle", "閒置"),
    "刚刚": ("just now", "剛剛"),
    "从未使用": ("never used", "從未使用"),
    "{n} 分钟前": ("{n} min ago", "{n} 分鐘前"),
    "{n} 小时前": ("{n} h ago", "{n} 小時前"),
    "{n} 天前": ("{n} d ago", "{n} 天前"),
    "{n} 个月前": ("{n} mo ago", "{n} 個月前"),
    "{n} 个修改器": ("{n} trainers", "{n} 個修改器"),
    "{n} 个 · 共 {size} · 最近更新 {stamp}": (
        "{n} trainers · {size} · updated {stamp}",
        "{n} 個 · 共 {size} · 最近更新 {stamp}",
    ),
    "使用过 {n} 次": ("used {n}×", "使用過 {n} 次"),
    "{n} 次": ("{n}×", "{n} 次"),
    "剩余 {t}": ("{t} left", "剩餘 {t}"),
    "剩余 {n} 秒": ("{n}s left", "剩餘 {n} 秒"),
    "剩余 {m} 分 {s} 秒": ("{m}m {s}s left", "剩餘 {m} 分 {s} 秒"),
    "解析下载地址…": ("Resolving the download link…", "解析下載位址…"),
    "安装中…": ("Installing…", "安裝中…"),
    "读取 FLiNG 页面…": ("Reading the FLiNG page…", "讀取 FLiNG 頁面…"),
    "读取 CT 页面…": ("Reading the CT page…", "讀取 CT 頁面…"),
    "HTTP {code}，重试 {a}/{b}…": ("HTTP {code}, retry {a}/{b}…", "HTTP {code}，重試 {a}/{b}…"),
    "连接中断，重试 {a}/{b}…": (
        "Connection dropped, retry {a}/{b}…",
        "連線中斷，重試 {a}/{b}…",
    ),
    "已安装到 {path}": ("Installed to {path}", "已安裝到 {path}"),
    "{n} 秒": ("{n}s", "{n} 秒"),
    "{n} 分 {m} 秒": ("{n}m {m}s", "{n} 分 {m} 秒"),
    # ---------- 提示 / 对话框 ----------
    "已刷新本地库，正在更新在线索引…": (
        "Library refreshed, updating the online index…",
        "已重新整理本機庫，正在更新線上索引…",
    ),
    "「{name}」已安装": ("“{name}” installed", "「{name}」已安裝"),
    "「{name}」下载失败：{msg}": ("“{name}” failed: {msg}", "「{name}」下載失敗：{msg}"),
    "「{name}」已在下载队列里": ("“{name}” is already queued", "「{name}」已在下載佇列裡"),
    "「{name}」来自 GCM 源，需要他们的签名服务才能下载；可以在「发现」里选 FLiNG 来源的条目实测下载": (
        "“{name}” comes from the GCM index, which needs their private signing service — "
        "try a FLiNG entry in Discover instead",
        "「{name}」來自 GCM 源，需要他們的簽名服務才能下載；可以在「探索」裡選 FLiNG 來源的條目實測下載",
    ),
    "已在浏览器打开「{name}」的官方页面": (
        "Opened the official page for “{name}”",
        "已在瀏覽器開啟「{name}」的官方頁面",
    ),
    "官方页面链接已复制到剪贴板": (
        "Official page link copied",
        "官方頁面連結已複製到剪貼簿",
    ),
    "这条记录没有官方网站链接": ("This entry has no website link", "這筆記錄沒有官方網站連結"),
    "把「{name}」移到回收站？": ("Move “{name}” to the recycle bin?", "把「{name}」移到資源回收筒？"),
    "删除修改器": ("Delete trainer", "刪除修改器"),
    "启动失败": ("Launch failed", "啟動失敗"),
    "删除失败": ("Delete failed", "刪除失敗"),
    "无法打开目录": ("Cannot open the folder", "無法開啟資料夾"),
    "部分文件未导入": ("Some files were not imported", "部分檔案未匯入"),
    "导入失败": ("Import failed", "匯入失敗"),
    "修改器 (*.zip *.exe *.7z);;所有文件 (*.*)": (
        "Trainers (*.zip *.exe *.7z);;All files (*.*)",
        "修改器 (*.zip *.exe *.7z);;所有檔案 (*.*)",
    ),
    "选择要导入的修改器": ("Choose trainers to import", "選擇要匯入的修改器"),
    "在线索引更新完成": ("Online index updated", "線上索引更新完成"),
    # ---------- 下载源地址 ----------
    "下载源地址": ("Download source URLs", "下載源位址"),
    "抓取与下载的站点地址，可改成镜像或反代；改完点顶栏的刷新重新抓取": (
        "Site addresses used for scraping and downloading - swap in a mirror if needed, "
        "then hit refresh in the top bar",
        "抓取與下載的站點位址，可改成鏡像或反向代理；改完點頂欄的重新整理重新抓取",
    ),
    "风灵月影（FLiNG）": ("FLiNG", "風靈月影（FLiNG）"),
    "Cheat Table 站点": ("Cheat Table site", "Cheat Table 站點"),
    "小幸站点": ("XiaoXing site", "小幸站點"),
    "恢复默认地址": ("Reset to defaults", "恢復預設位址"),
    "显示中文游戏名": ("Show Chinese game names", "顯示中文遊戲名"),
    "从 Steam 补全中文名，关掉就只用原始英文名": (
        "Fill Chinese names from Steam - turn off to keep the original English titles",
        "從 Steam 補全中文名，關掉就只用原始英文名",
    ),
    "下载源地址已保存，点顶栏刷新重新抓取": (
        "Source URLs saved - hit refresh in the top bar to re-scrape",
        "下載源位址已儲存，點頂欄重新整理重新抓取",
    ),
    "正在后台补全中文名（{n} 条），补齐后可直接搜中文": (
        "Filling in Chinese names in the background ({n}) - you can search in Chinese once done",
        "正在後台補全中文名（{n} 條），補齊後可直接搜中文",
    ),
}

_INDEX = {"zh_TW": 1, "en_US": 0}


class Translator(QObject):
    """当前语言 + 切换信号。界面在 `changed` 里整体重建。"""

    changed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._code = DEFAULT_LANG
        # 列表标题是否用 Steam 补来的中文名（设置里可关）
        self.show_chinese = True

    @property
    def code(self) -> str:
        return self._code

    def set_language(self, code: str) -> None:
        code = code if code in _INDEX or code == DEFAULT_LANG else DEFAULT_LANG
        if code == self._code:
            return
        self._code = code
        self.changed.emit(code)

    def translate(self, text: str) -> str:
        if self._code == DEFAULT_LANG:
            return text
        entry = TABLE.get(text)
        if entry is None:
            return text
        return entry[_INDEX[self._code]]


translator = Translator()


def t(text: str) -> str:
    """取当前语言下的文案；未收录时原样返回中文。"""
    return translator.translate(text)


def lang_name(code: str) -> str:
    for key, label in LANGS:
        if key == code:
            return label
    return LANGS[0][1]
