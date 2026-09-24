#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全平台视频下载器 · yt-dlp GUI
=============================================================================

一个基于 tkinter / ttk 的浅色主题图形外壳：调用外部的 yt-dlp 与 ffmpeg 完成下载。
凡是 yt-dlp 支持的站点（B 站、抖音、小红书、YouTube、Twitter/X、Vimeo、
Twitch、微博……）本工具都可以直接使用。

设计定位
--------
本程序是「命令行拼装 + 子进程托管 + 日志回显」的薄外壳，不内嵌下载引擎：

    * 下载引擎：优先使用程序目录下的便携版 yt-dlp(.exe)，没有则回退系统 PATH
    * 音视频合并：同上，优先程序目录下的 ffmpeg(.exe)，再回退系统 PATH

界面与交互
----------
    * 浅色现代主题：#FAFAFA 底 + #FFFFFF 卡片 + #E5E7EB 细边框 + #2563EB 强调蓝
    * 适度圆角（6px）、扁平纯色填充、1px 细边框，聚焦时蓝色高亮描边
    * 布局参考 Windows 10 系统设置：分组卡片、控件对齐、留白适中
    * 按钮仅在悬浮时轻微高亮；窗口标题栏保持系统原生，只美化内容区

功能要点
--------
    1. URL 输入框：粘贴任意视频网页链接
    2. 清晰度下拉框：最高画质（默认）/ 4K·2160P / 1080P / 720P / 480P / 360P，
       切换时实时刷新底层 -f 参数（与 Cookie 并排放在同一行，节省纵向空间）
    3. Cookie 来源下拉框：不读取 Cookie / Edge / Chrome，
       切换时实时刷新底层命令；选「不读取 Cookie」命令保持纯净
       （不含任何 --cookies-from-browser 参数）
       ⚠ Windows 下从浏览器读取 Cookie 需要走 DPAPI 解密，可能失败；
         Cookie 只用于需要登录才能访问的受限内容，报错时切回
         「不读取 Cookie」即可正常下载。
    4. 复选框「下载整个合集 / 列表」：默认勾选。
       勾选 → 不加任何额外参数，粘贴合集链接会下载合集里的全部视频，
              普通单视频链接不受影响；
       取消 → 追加 --no-playlist，只下载当前链接对应的那一个视频。
       勾选状态与 URL、清晰度、Cookie 一起实时反映到命令预览区。
    5. 只读命令预览区：展示完整将要执行的 yt-dlp CMD 命令，支持复制，
       仅作查看用途（学习 / 调试用）
    6. 下载按钮：下载中禁用，避免多进程并发；结束/出错后自动恢复
    7. 日志框：实时流式回显 yt-dlp 的 stdout / stderr；
       下载合集时自动补上「合集开始 / 第 N / M 个 / 第 N 个完成 / 合集结束」分隔线，
       yt-dlp 原始的 "[download] Downloading item 3 of 12" 等输出原样保留
    8. 输出命名：每个视频按 %(title)s.%(ext)s 各自命名，合集内互不覆盖
    9. 保存位置：底部一行可交互
       * 「选择文件夹…」调系统目录选择框，决定本次下载存到哪（也可直接粘贴路径）
       * 「设为默认」把当前目录记进 ytdlp-gui.config.json，下次启动自动沿用
       * 「恢复默认」清掉记录，回到内置默认（源码=脚本目录 / exe=exe 目录）
       两个按钮会按当前状态自动灰显，不需要额外文字说明
    10. 支持把链接作为启动参数传入：YtDlpDownloader.exe "https://..."（也可直接把
        链接拖到 exe 图标上），打开后回车即可开始下载
    11. 便携二进制优先：程序目录下放 yt-dlp.exe / ffmpeg.exe 即自动优先使用，
        环境自检会标注【本地便携版】还是【系统PATH版本】
    12. 缺失依赖引导：点下载时若缺 yt-dlp / ffmpeg，弹窗给出可一键复制的 winget
        安装命令，装完重启本程序即可
    13. 可折叠「高级选项」卡片（默认收起）：代理地址、自定义附加参数、下载字幕、
        限速，以及一键重置；展开状态与各项取值都会记忆到配置文件
    14. 引擎版本：启动时后台执行 yt-dlp --version，把版本号和二进制来源显示在
        状态区域（区分便携版 / 系统 PATH 版）
    15. 视频预览：点「预览」解析当前链接（不下载），在独立窗口里显示封面缩略图 +
        标题 / 平台 / 作者 / 时长 / 上传日期 / 播放量 / 点赞数 / 简介 /
        可选清晰度 / 网页链接，支持一键复制信息或用浏览器打开

关键实现
--------
    * 预览取数：后台线程跑 yt-dlp --dump-json --playlist-items 1，复用界面上的
      Cookie / 代理 / 附加参数设置，受限内容也能解析；结果经既有队列回主线程
    * 封面显示：Tk 的 PhotoImage 只认 PNG/GIF，而封面多为 jpg/webp，
      因此借用系统里已有的 ffmpeg 走管道转成 PNG（不落临时文件、不引入 Pillow）
    * 默认基础参数：-f "bv*+ba" --add-header Referer:https://www.bilibili.com
      （「清晰度」选最高画质时输出与原始需求完全一致）
    * 二进制解析：resolve_binaries() 在启动时决定 YTDLP_BIN / FFMPEG_BIN
      （便携版取绝对路径，PATH 版保留裸命令名，便于命令预览保持简洁）
    * 配置文件：新增配置项一律"读旧 -> 合并 -> 写回"，不会覆盖或丢弃旧字段，
      完全兼容只含 default_output_dir 的老版本配置
    * 清晰度映射：其他档位用 bv*[height<=N]+ba/b[height<=N]/b，
      即"不高于 N 分辨率"优先，并逐级兜底，避免站点缺档位时报格式不可用
    * 合集开关：勾选 = 纯净（不加参数）；取消 = 追加 --no-playlist
    * 输出目录：源码运行时 = app.py 所在目录；打包成 exe 后 = exe 所在目录
      （这是"内置默认"；用户可在界面里改，并用配置文件记住自己的默认值）
    * 中文编码：向子进程注入 PYTHONIOENCODING / PYTHONUTF8 = utf-8，
      并按 utf-8 → 系统首选编码 → gbk 逐级容错解码，避免中文乱码
    * 实时日志：reader 线程按 \\r / \\n 切块写入 queue，主线程 after() 轮询刷新；
      \\r 进度行原地覆盖，超长日志自动裁剪，避免长时间下载内存膨胀
    * 打包时使用 --windowed 隐藏黑色控制台窗口；tkinter 的 tcl/tk 运行时由
      PyInstaller 自带的 hook-tkinter 收集，这里再显式声明子模块与数据兜底，
      避免打包后 GUI 启动失败

打包命令（PowerShell / cmd，--windowed 保证不弹黑色控制台窗口）：
    pyinstaller --noconfirm --clean --onefile --windowed ^
        --name YtDlpDownloader ^
        --hidden-import tkinter.ttk --hidden-import tkinter.font ^
        --hidden-import tkinter.messagebox --collect-data tkinter app.py

    * tcl/tk 运行时（tcl86t.dll / tk86t.dll / tcl 库目录）由 PyInstaller 自带的
      hook-tkinter 自动收集，这里再显式声明 tkinter 子模块与数据，双重兜底，
      避免打包后 GUI 因缺资源而启动失败。
    * [新增] 两种模式都支持，参数完全一致：把 --onefile 换成 --onedir 即可得到
      免解压启动的目录版（便携二进制 yt-dlp.exe / ffmpeg.exe 放在 exe 同目录
      依然会被优先识别）。
"""

import base64
import json
import locale
import os
import queue
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import urllib.request
from tkinter import filedialog, messagebox, ttk

# ===========================================================================
# ① 常量与全局配置
# ===========================================================================

APP_TITLE = "全平台视频下载器 · yt-dlp GUI"
APP_VERSION = "1.4.0"

# 外部依赖的可执行文件名
#   [新增] 这两个全局量改为"运行时动态赋值"：启动时由 resolve_binaries()
#   按「程序目录便携版优先 → 系统 PATH 回退」的规则重新赋值。
#   这里保留同名默认值，保证任何提前引用它们的代码路径仍然安全可用。
YTDLP_BIN = "yt-dlp"
FFMPEG_BIN = "ffmpeg"
# [新增] 二进制来源标记，用于环境自检和状态区展示
SOURCE_LOCAL = "本地便携版"
SOURCE_PATH = "系统PATH版本"
YTDLP_SOURCE = ""          # 运行时赋值：SOURCE_LOCAL / SOURCE_PATH / ""
FFMPEG_SOURCE = ""
YTDLP_RESOLVED_PATH = ""   # 运行时赋值：实际解析到的完整路径
FFMPEG_RESOLVED_PATH = ""
YTDLP_VERSION = ""         # [新增] 运行时赋值：yt-dlp --version 的结果

# ---- [新增] 浅色现代主题配色 ----
#   主背景 #FAFAFA / 卡片 #FFFFFF / 边框 #E5E7EB / 主文字 #1F2937 / 次要文字 #6B7280
#   按钮主色 #2563EB / hover #1D4ED8 / 成功 #10B981 / 警告 #F59E0B / 错误 #EF4444
C = {
    "BG":          "#FAFAFA",   # 窗口底色
    "SURFACE":     "#FFFFFF",   # 分组卡片底色
    "INPUT_BG":    "#FFFFFF",   # 输入框 / 下拉框底色
    "BORDER":      "#E5E7EB",   # 1px 细边框
    "TEXT":        "#1F2937",   # 主文字
    "TEXT_DIM":    "#6B7280",   # 次要文字
    "TEXT_MUTE":   "#9CA3AF",   # 更弱的提示文字
    "ACCENT":      "#2563EB",   # 强调色（按钮主色）
    "ACCENT_HI":   "#1D4ED8",   # 悬浮高亮
    "ACCENT_LO":   "#1E40AF",   # 按下
    "GHOST_BG":    "#F3F4F6",   # 次级按钮填充
    "GHOST_HI":    "#E5E7EB",
    "DISABLED_BG": "#E5E7EB",
    "DISABLED_FG": "#9CA3AF",
    "OK":          "#10B981",   # 成功
    "ERR":         "#EF4444",   # 错误
    "WARN":        "#F59E0B",   # 警告 / 提示
    "CMD_FG":      "#0F172A",   # 命令预览文字（浅色代码风格）
    "LOG_FG":      "#374151",   # 日志文字
    # [新增] 浅色主题下新增的专用色
    "LOG_BG":      "#F3F4F6",   # 日志区域底色（需求指定）
    "CMD_BG":      "#F6F8FA",   # 命令预览框：浅色代码风格底色
    "BORDER_HI":   "#D1D5DB",   # 悬浮时的边框
    "GHOST_LO":    "#D1D5DB",   # 次级按钮按下
    "TROUGH":      "#E5E7EB",   # 进度条槽 / 滚动条槽
    "SCROLL_BG":   "#D1D5DB",   # 滚动条滑块
    "SCROLL_HI":   "#9CA3AF",   # 滚动条滑块悬浮
    "GHOST_FG":    "#374151",   # [新增] 次级按钮文字色
}

# ---- yt-dlp 参数 ----
# 默认基础参数（需求指定）：最佳视频 + 最佳音频（-f 由「清晰度」下拉框决定），
# 并统一带上 B 站 Referer 头
DEFAULT_FORMAT = "bv*+ba"
BASE_ARGS = ["--add-header", "Referer:https://www.bilibili.com"]

# 清晰度下拉选项：(界面显示名, yt-dlp -f 格式选择器)
#   * 第一项保持原始默认值 bv*+ba（最佳视频 + 最佳音频）
#   * 其余档位用 height<=N 限定"不高于该分辨率"，并追加 /b[height<=N]/b 兜底：
#     站点没有该档位时退回预合并流、再退回任意最佳流，避免直接报
#     "Requested format is not available" 而下载失败
QUALITY_CHOICES = [
    ("最高画质（默认）", DEFAULT_FORMAT),
    ("4K / 2160P",   "bv*[height<=2160]+ba/b[height<=2160]/b"),
    ("1080P",        "bv*[height<=1080]+ba/b[height<=1080]/b"),
    ("720P",         "bv*[height<=720]+ba/b[height<=720]/b"),
    ("480P",         "bv*[height<=480]+ba/b[height<=480]/b"),
    ("360P",         "bv*[height<=360]+ba/b[height<=360]/b"),
]
QUALITY_MAP = dict(QUALITY_CHOICES)
DEFAULT_QUALITY = QUALITY_CHOICES[0][0]

# Cookie 下拉选项；「不读取 Cookie」时命令保持纯净版本
COOKIE_OFF = "不读取 Cookie"
COOKIE_CHOICES = [COOKIE_OFF, "Edge", "Chrome"]
BROWSER_MAP = {"Edge": "edge", "Chrome": "chrome"}

# 输出文件名模板（配合 -P 指定输出目录）
# %(title)s 让合集里每个视频按各自标题命名，天然互不覆盖
OUTPUT_TEMPLATE = "%(title)s.%(ext)s"

# 保存位置配置文件（与脚本 / exe 同目录，用户点「设为默认」时才生成）
#   {"default_output_dir": "D:\\Videos"}
# 内置默认保存位置仍然是：源码运行 = 脚本所在目录，exe 运行 = exe 所在目录
CONFIG_NAME = "ytdlp-gui.config.json"

# ---- [新增] 便携二进制文件名（放在程序目录里即被优先使用）----
PORTABLE_YTDLP_NAMES = ["yt-dlp.exe", "yt-dlp"]
PORTABLE_FFMPEG_NAMES = ["ffmpeg.exe", "ffmpeg"]

# ---- [新增] 配置文件里新增的键名（老配置没有这些键时按默认值走）----
CFG_DEFAULT_DIR = "default_output_dir"
CFG_ADV_EXPANDED = "advanced_expanded"
CFG_ADV_PROXY = "advanced_proxy"
CFG_ADV_CUSTOM_ARGS = "advanced_custom_args"
CFG_ADV_SUBS = "advanced_write_subs"
CFG_ADV_LIMIT_RATE = "advanced_limit_rate"

# ---- [新增] 高级选项默认值 ----
ADV_DEFAULTS = {
    CFG_ADV_EXPANDED: False,     # 默认折叠
    CFG_ADV_PROXY: "",
    CFG_ADV_CUSTOM_ARGS: "",
    CFG_ADV_SUBS: False,
    CFG_ADV_LIMIT_RATE: "",
}

# [新增] 缺失依赖时提示的 winget 安装命令（弹窗内可一键复制）
WINGET_COMMANDS = [
    "winget install -e --id yt-dlp.yt-dlp",
    "winget install -e --id yt-dlp.FFmpeg",
]

# [新增] 限速取值校验：数字 + 可选单位 k/K/m/M/g/G，例如 500K、2M、1.5m、1024
LIMIT_RATE_RE = re.compile(r"^\d+(?:\.\d+)?[kKmMgG]?$")

# [新增] 附加参数里 --limit-rate 之类的"带值参数"不需要特殊处理，直接按 shell 规则切分
ADV_HINT_WRAP_MIN = 140      # 说明标签换行宽度下限（配合 wraplength 修复）
# [主题] 圆角半径：按钮/输入框/下拉框统一用适度圆角，复选框略小
BUTTON_RADIUS = 8            # 按钮圆角
INPUT_RADIUS = 8             # 输入框圆角
COMBO_RADIUS = 8             # 下拉框圆角
CHECK_RADIUS = 5             # 复选框圆角
BUTTON_PAD_Y = 16            # 按钮内边距（越大按钮越"厚"，更醒目）

# ---- [新增] 视频预览（解析视频信息，不下载）----
PREVIEW_TIMEOUT = 90         # 解析超时（秒）
THUMB_MAX_W = 360            # 封面图最大宽度（像素）
PREVIEW_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/120.0 Safari/537.36")
# 预览窗口里展示的字段：(显示名, info 里的候选键)
PREVIEW_FIELDS = [
    ("标题", ("title", "fulltitle")),
    ("平台", ("extractor_key", "extractor")),
    ("作者", ("uploader", "channel", "creator", "uploader_id")),
    ("时长", ("duration_string", "duration")),
    ("上传日期", ("upload_date", "release_date")),
    ("播放量", ("view_count",)),
    ("点赞数", ("like_count",)),
    ("简介", ("description",)),
]

# 日志框最多保留的行数，超出后从头部裁剪
LOG_MAX_LINES = 4000
LOG_KEEP_LINES = 3000

# 按 \r 或 \n 切分字节流
_SPLIT_RE = re.compile(rb"[\r\n]")
# 从进度行中提取百分比
_PCT_RE = re.compile(r"\[download\]\s+([\d.]+)%")
# 合集相关输出（用于在日志里插入清晰的分隔线）
_PL_ITEM_RE = re.compile(r"\[download\]\s+Downloading (?:item|video)\s+(\d+)\s+of\s+(\d+)")
_PL_START_RE = re.compile(r"Downloading playlist:\s*(.+?)\s*$")
_PL_END_RE = re.compile(r"Finished downloading playlist:\s*(.+?)\s*$")
# 分隔线样式
RULE_WIDTH = 9
# ANSI 颜色转义（yt-dlp 在允许着色时会把 "[download] Downloading item 1 of 9"
# 里的序号包上颜色码，剥掉后才能稳定匹配，同时避免日志里出现乱码控制符）
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
# 系统首选编码（中文 Windows 通常是 cp936），用于解码容错
_PREFERRED_ENC = locale.getpreferredencoding(False)

# 运行时填充的字体配置
FONTS = {"h": ("Segoe UI", 15, "bold"), "card": ("Segoe UI", 10, "bold"),
         "ui": ("Segoe UI", 10), "small": ("Segoe UI", 9),
         "mono": ("Consolas", 9)}

# Windows 下隐藏子进程控制台窗口
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def app_dir():
    """返回程序所在目录。

    * 直接 `python app.py` 运行：脚本所在文件夹
    * PyInstaller 打包后运行：exe 所在文件夹（sys.executable 指向 exe）
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


# ===========================================================================
# [新增] 外部依赖解析：程序目录便携版优先 → 系统 PATH 回退
# ===========================================================================
def find_local_binary(names):
    """在程序所在目录里查找便携版可执行文件，找到返回绝对路径，否则 None。"""
    base = app_dir()
    for name in names:
        cand = os.path.join(base, name)
        if os.path.isfile(cand):
            return cand
    return None


def resolve_binary(names, fallback_name):
    """解析单个外部依赖。

    返回 (可执行引用, 来源标记, 完整路径)：
      * 程序目录里存在便携版 → (绝对路径, SOURCE_LOCAL, 绝对路径)
      * 否则回退系统 PATH  → (裸命令名, SOURCE_PATH, which() 结果)
      * 都没有            → (裸命令名, "", None)
    便携版用绝对路径写进命令，用户一眼能看出跑的是本地那个；
    PATH 版保留裸名，命令预览保持简洁可复制。
    """
    local = find_local_binary(names)
    if local:
        return local, SOURCE_LOCAL, local
    found = shutil.which(fallback_name)
    if found:
        return fallback_name, SOURCE_PATH, found
    return fallback_name, "", None


def resolve_binaries():
    """[新增] 启动时解析 yt-dlp / ffmpeg，把结果写到全局运行态变量里。"""
    global YTDLP_BIN, FFMPEG_BIN
    global YTDLP_SOURCE, FFMPEG_SOURCE
    global YTDLP_RESOLVED_PATH, FFMPEG_RESOLVED_PATH
    YTDLP_BIN, YTDLP_SOURCE, YTDLP_RESOLVED_PATH = resolve_binary(
        PORTABLE_YTDLP_NAMES, "yt-dlp")
    FFMPEG_BIN, FFMPEG_SOURCE, FFMPEG_RESOLVED_PATH = resolve_binary(
        PORTABLE_FFMPEG_NAMES, "ffmpeg")
    return YTDLP_RESOLVED_PATH, FFMPEG_RESOLVED_PATH


def query_ytdlp_version(executable, timeout=15):
    """[新增] 执行 `yt-dlp --version` 拿引擎版本号，失败返回空串。

    在后台线程里调用，避免启动时卡界面。
    """
    if not executable:
        return ""
    try:
        out = subprocess.run(
            [executable, "--version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=timeout, creationflags=CREATE_NO_WINDOW)
        text = decode_output(out.stdout or b"").strip().splitlines()
        return text[0].strip() if text else ""
    except Exception:                                     # noqa: BLE001
        return ""


def dependency_source_text(source):
    """[新增] 把来源标记渲染成界面上显示的【…】文案。"""
    if source == SOURCE_LOCAL:
        return f"【{SOURCE_LOCAL}】"
    if source == SOURCE_PATH:
        return f"【{SOURCE_PATH}】"
    return "【未找到】"


def set_ytdlp_version(version):
    """[新增] 记录探测到的 yt-dlp 版本号（运行态变量，供环境自检等处使用）。"""
    global YTDLP_VERSION
    YTDLP_VERSION = (version or "").strip()
    return YTDLP_VERSION


# ===========================================================================
# [新增] 视频预览用到的格式化 / 抓图工具
# ===========================================================================
def format_duration(value):
    """秒数 -> 03:32 / 1:02:03 ；非法值原样返回字符串。"""
    if value in (None, ""):
        return ""
    try:
        total = int(float(value))
    except (TypeError, ValueError):
        return str(value)
    if total < 0:
        return ""
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def format_upload_date(value):
    """YYYYMMDD -> YYYY-MM-DD。"""
    text = str(value or "").strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text


def format_count(value):
    """播放量之类的数字加千分位；非数字原样返回。"""
    if value in (None, ""):
        return ""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def format_quality_list(info, limit=8):
    """从 formats 里汇总可用清晰度，例如 '1080P / 720P / 480P / 360P'。"""
    heights = set()
    for fmt in info.get("formats") or []:
        if not isinstance(fmt, dict):
            continue
        h = fmt.get("height")
        if isinstance(h, (int, float)) and h > 0:
            heights.add(int(h))
    if not heights:
        single = info.get("height")
        if isinstance(single, (int, float)) and single > 0:
            heights.add(int(single))
    if not heights:
        return ""
    ordered = sorted(heights, reverse=True)[:limit]
    return " / ".join(f"{h}P" for h in ordered)


def first_field(info, keys, default=""):
    """按候选键顺序取第一个非空值。"""
    for key in keys:
        value = info.get(key)
        if value not in (None, "", []):
            return value
    return default


def fetch_thumbnail_png(url, headers=None, max_width=THUMB_MAX_W,
                        timeout=30):
    """[新增] 下载封面并转成 PNG 字节（Tk 的 PhotoImage 不认 jpg/webp）。

    返回 (png_bytes 或 None, 错误说明)。
    转换借用系统里已有的 ffmpeg，走管道不产生临时文件；本来就是 PNG 则直接用。
    """
    if not url:
        return None, ""
    try:
        req = urllib.request.Request(url, headers=headers or
                                     {"User-Agent": PREVIEW_UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except Exception as exc:                              # noqa: BLE001
        return None, f"封面下载失败：{exc}"
    if not raw:
        return None, "封面为空"
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return raw, ""
    try:
        out = subprocess.run(
            [FFMPEG_BIN, "-hide_banner", "-loglevel", "error",
             "-i", "pipe:0", "-vf", f"scale={max_width}:-2",
             "-f", "image2pipe", "-vcodec", "png", "pipe:1"],
            input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout, creationflags=CREATE_NO_WINDOW)
    except FileNotFoundError:
        return None, "未找到 ffmpeg，无法显示封面"
    except Exception as exc:                              # noqa: BLE001
        return None, f"封面转码失败：{exc}"
    if out.returncode == 0 and (out.stdout or b"")[:8] == b"\x89PNG\r\n\x1a\n":
        return out.stdout, ""
    err = decode_output(out.stderr or b"").strip().splitlines()
    return None, ("封面转码失败：" + (err[-1] if err else "未知错误"))


def normalize_dir(path):
    """规范化用户给出的目录：去空白、展开环境变量与 ~、统一分隔符。

    选择文件夹对话框返回的是正斜杠路径（C:/Users/...），手动粘贴时还可能带
    引号或环境变量，这里统一处理成系统本地形式。
    """
    if not path:
        return ""
    path = path.strip().strip('"').strip("'")
    if not path:
        return ""
    return os.path.normpath(os.path.expandvars(os.path.expanduser(path)))


def format_command(cmd):
    """把参数列表渲染成可复制到 CMD 里执行的命令行字符串。"""
    out = []
    for arg in cmd:
        # 含空格 / 引号 / CMD 特殊字符（& | < > ^ ( ) * ?）的参数统一加双引号，
        # 这样渲染出来的命令可以原样复制到 CMD / PowerShell 里执行
        if arg == "" or re.search(r'[\s"&|<>^()*?]', arg):
            out.append('"' + arg.replace('"', r'\"') + '"')
        else:
            out.append(arg)
    return " ".join(out)


def decode_output(raw):
    """把子进程输出的原始字节解码成文本，逐级容错，避免中文乱码。

    yt-dlp 本身是 Python 程序，我们已通过环境变量要求它输出 UTF-8；
    ffmpeg 在中文 Windows 上仍可能吐出 GBK/CP936，因此这里多级回退。
    """
    if not raw:
        return ""
    for enc in ("utf-8", _PREFERRED_ENC, "gbk"):
        if not enc:
            continue
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", "replace")


# ===========================================================================
# ② 扁平按钮控件：纯色填充 + 小圆角，仅悬浮时轻微高亮
# ===========================================================================
class FlatButton(tk.Canvas):
    """ttk 原生按钮在 Windows 上难以完全贴合深色扁平风格，这里用 Canvas 自绘。

    * 纯色填充 + 3px 小圆角（偏向直角的方正造型）
    * 仅悬浮 / 按下时轻微高亮，无立体阴影
    * 宽度按文字自动测量，兼容高 DPI 缩放
    """

    def __init__(self, master, text="", command=None, kind="primary",
                 min_width=0, height=None, padx=16, font=None, state="normal"):
        try:
            bg = master.cget("bg")
        except Exception:
            bg = C["BG"]
        self._font = font or FONTS["ui"]
        self._kind = kind
        self._command = command
        self._state = state
        self._hover = False
        self._pressed = False

        # [主题] 主按钮加粗，视觉上更醒目；次级按钮保持常规字重
        if kind == "primary":
            bold = tkfont.Font(font=self._font)
            bold.configure(weight="bold")
            self._font = bold

        f = tkfont.Font(font=self._font)
        w = max(min_width, f.measure(text) + 2 * padx)
        # [主题] 按钮加厚，点击区域更明显
        h = height or (f.metrics("linespace") + BUTTON_PAD_Y)

        super().__init__(master, width=w, height=h, bg=bg, bd=0,
                         highlightthickness=0, relief="flat", takefocus=0,
                         cursor="hand2" if state == "normal" else "arrow")
        # 注意：不要用 self._w / self._h，那是 tkinter 内部保存控件路径名的属性
        self._bw, self._bh = w, h
        # [主题] 圆角按钮 + 次级按钮补一圈细边框
        self._shape = self._rounded(0, 0, w, h, BUTTON_RADIUS,
                                    fill=self._fill(), outline=self._outline())
        self._label = self.create_text(w / 2, h / 2, text=text,
                                       fill=self._fg(), font=self._font)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    # -- 绘制 -----------------------------------------------------------
    def _rounded(self, x1, y1, x2, y2, r, **kw):
        """用带平滑的多边形模拟小圆角矩形。"""
        pts = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.create_polygon(pts, smooth=True, splinesteps=8, **kw)

    def _palette(self):
        if self._kind == "primary":
            return {"normal": C["ACCENT"], "hover": C["ACCENT_HI"],
                    "active": C["ACCENT_LO"], "fg": "#ffffff",
                    "outline": "", "hover_outline": ""}
        # [主题] 次级按钮：白底 + 更清晰的灰边框，悬浮时边框与文字转主色蓝
        return {"normal": C["GHOST_BG"], "hover": C["GHOST_HI"],
                "active": C["GHOST_LO"], "fg": C["GHOST_FG"],
                "outline": C["BORDER_HI"], "hover_outline": C["ACCENT"]}

    def _fill(self):
        if self._state == "disabled":
            return C["DISABLED_BG"]
        p = self._palette()
        if self._pressed:
            return p["active"]
        if self._hover:
            return p["hover"]
        return p["normal"]

    def _fg(self):
        if self._state == "disabled":
            return C["DISABLED_FG"]
        # [主题] 次级按钮悬浮/按下时文字变主色，反馈更明显
        if self._kind != "primary" and (self._hover or self._pressed):
            return C["ACCENT"]
        return self._palette()["fg"]

    def _outline(self):
        """[主题] 按钮描边色（主按钮无描边，次级按钮用细边框）。"""
        if self._state == "disabled":
            return C["BORDER"]
        p = self._palette()
        if self._kind != "primary" and self._hover:
            return p["hover_outline"]
        return p["outline"]

    def _redraw(self):
        self.itemconfigure(self._shape, fill=self._fill(),
                           outline=self._outline())
        self.itemconfigure(self._label, fill=self._fg())
        self.configure(cursor="hand2" if self._state == "normal" else "arrow")

    # -- 事件 -----------------------------------------------------------
    def _on_enter(self, _e):
        if self._state == "normal":
            self._hover = True
            self._redraw()

    def _on_leave(self, _e):
        self._hover = False
        self._pressed = False
        self._redraw()

    def _on_press(self, _e):
        if self._state == "normal":
            self._pressed = True
            self._redraw()

    def _on_release(self, event):
        if self._state != "normal":
            return
        inside = 0 <= event.x <= self._bw and 0 <= event.y <= self._bh
        self._pressed = False
        self._redraw()
        if inside and callable(self._command):
            self._command()

    # -- 对外接口 -------------------------------------------------------
    def set_state(self, state):
        if state == self._state:
            return
        self._state = state
        if state != "normal":
            self._hover = False
            self._pressed = False
        self._redraw()

    def set_text(self, text):
        self.itemconfigure(self._label, text=text)


# ===========================================================================
# ③ 扁平复选框控件
# ===========================================================================
class FlatCheck(tk.Canvas):
    """扁平复选框（已适配浅色主题）：圆角方框 + 1px 细边框，选中时填充主色蓝并画白色对勾。

    原生 tk.Checkbutton 在 Windows 下的勾选框由系统绘制，配色难以跟随主题，
    所以这里和 FlatButton 一样自绘，保证风格统一。
    """

    BOX = 15          # 方框边长
    GAP = 8           # 方框与文字的间距

    def __init__(self, master, text="", variable=None, command=None,
                 font=None, bg=None):
        try:
            host_bg = bg or master.cget("bg")
        except Exception:
            host_bg = C["BG"]
        self._font = font or FONTS["ui"]
        self._command = command
        self._var = variable
        self._hover = False
        self._state = "normal"

        f = tkfont.Font(font=self._font)
        box = self.BOX
        w = box + self.GAP + f.measure(text)
        h = max(box, f.metrics("linespace")) + 6

        super().__init__(master, width=w, height=h, bg=host_bg, bd=0,
                         highlightthickness=0, relief="flat", takefocus=0,
                         cursor="hand2")
        self._bw, self._bh = w, h
        top = (h - box) // 2
        # [主题] 方框改为圆角矩形，未选中时白底 + 细边框
        self._box = self._rounded_box(1, top + 1, box, top + box,
                                      radius=CHECK_RADIUS, fill=C["INPUT_BG"],
                                      outline=C["BORDER"], width=1)
        # 对勾（三段折线），选中时才显示
        self._tick = self.create_line(box * 0.24, top + box * 0.52,
                                      box * 0.44, top + box * 0.72,
                                      box * 0.78, top + box * 0.30,
                                      fill="#ffffff", width=2,
                                      capstyle=tk.ROUND, joinstyle=tk.ROUND,
                                      state="hidden")
        self._text = self.create_text(box + self.GAP, h / 2, text=text,
                                      anchor="w", fill=C["TEXT"],
                                      font=self._font)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self._redraw()

    # -- 绘制 -----------------------------------------------------------
    def _rounded_box(self, x1, y1, x2, y2, radius=4, **kw):
        """[主题] 用平滑多边形画圆角方框（浅色主题下比直角方框更柔和）。"""
        pts = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        return self.create_polygon(pts, smooth=True, splinesteps=8, **kw)
    def get(self):
        return bool(self._var.get()) if self._var is not None else False

    def set(self, value):
        if self._var is not None:
            self._var.set(bool(value))
        self._redraw()

    def _redraw(self):
        checked = self.get()
        self.itemconfigure(self._box,
                           fill=C["ACCENT"] if checked else C["INPUT_BG"],
                           outline=C["ACCENT_HI"] if (checked or self._hover)
                           else C["BORDER"])
        self.itemconfigure(self._tick, state="normal" if checked else "hidden")
        self.itemconfigure(self._text, fill=C["TEXT"] if self._state == "normal"
                           else C["DISABLED_FG"])
        self.configure(cursor="hand2" if self._state == "normal" else "arrow")

    # -- 事件 -----------------------------------------------------------
    def _on_enter(self, _e):
        if self._state == "normal":
            self._hover = True
            self._redraw()

    def _on_leave(self, _e):
        self._hover = False
        self._redraw()

    def _on_click(self, _e):
        if self._state != "normal":
            return
        if self._var is not None:
            self._var.set(not self._var.get())
        self._redraw()
        if callable(self._command):
            self._command()

    def set_state(self, state):
        self._state = state
        self._redraw()


# ===========================================================================
# [新增] 圆角输入框：Canvas 画圆角边框 + 内嵌 tk.Entry
#   tkinter 原生 Entry 只能是方角，这里用"圆角外壳 + 无边框内层"的方式实现，
#   聚焦时描边变主色蓝，对外接口（pack/bind/focus_set/get…）与 Entry 保持一致。
# ===========================================================================
class RoundedEntry(tk.Canvas):
    def __init__(self, master, textvariable=None, font=None, radius=INPUT_RADIUS,
                 height=None, padx=10, bg=None, justify="left", width=None):
        try:
            host_bg = bg or master.cget("bg")
        except Exception:
            host_bg = C["SURFACE"]
        self._radius = radius
        self._padx = padx
        self._focused = False
        f = tkfont.Font(font=font or FONTS["ui"])
        h = height or (f.metrics("linespace") + 16)
        w = f.measure("0") * width + 2 * padx if width else 220

        super().__init__(master, width=w, height=h, bg=host_bg, bd=0,
                         highlightthickness=0, relief="flat", takefocus=0)
        self._entry = tk.Entry(self, textvariable=textvariable,
                               bg=C["INPUT_BG"], fg=C["TEXT"],
                               insertbackground=C["TEXT"], relief="flat", bd=0,
                               font=font or FONTS["ui"], highlightthickness=0,
                               justify=justify)
        self._shape = self.create_polygon(
            self._points(1, 1, w - 1, h - 1, radius), smooth=True, splinesteps=10,
            fill=C["INPUT_BG"], outline=C["BORDER"], width=1)
        self._win = self.create_window(padx, h // 2, window=self._entry,
                                       anchor="w",
                                       width=max(10, w - 2 * padx),
                                       height=max(10, h - 14))
        # 只把 <Configure> 绑在圆角外壳上：若同时转发给内层 Entry，
        # 会因为"外壳改高度 → 内层改尺寸 → 又触发外壳回调"而无限收缩
        super().bind("<Configure>", self._on_configure)
        # 点击圆角留白区域也能聚焦到输入框
        super().bind("<Button-1>", lambda _e: self._entry.focus_set())
        self._entry.bind("<FocusIn>", lambda _e: self._set_focus(True))
        self._entry.bind("<FocusOut>", lambda _e: self._set_focus(False))
        self._entry.bind("<Enter>", lambda _e: self._redraw(hover=True))
        self._entry.bind("<Leave>", lambda _e: self._redraw(hover=False))

    def _points(self, x1, y1, x2, y2, r):
        return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
                x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
                x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]

    def _set_focus(self, focused):
        self._focused = focused
        self._redraw()

    def _redraw(self, hover=None):
        if hover is not None:
            self._hover = hover
        outline = C["BORDER"]
        if self._focused:
            outline = C["ACCENT"]
        elif getattr(self, "_hover", False):
            outline = C["BORDER_HI"]
        self.itemconfigure(self._shape, outline=outline)

    def _on_configure(self, event):
        w, h = event.width, event.height
        self.coords(self._shape, *self._points(1, 1, w - 1, h - 1,
                                               self._radius))
        self.coords(self._win, self._padx, h // 2)
        self.itemconfigure(self._win, width=max(10, w - 2 * self._padx),
                           height=max(10, h - 14))

    # -- 对外接口：转发给内层 Entry -------------------------------------
    def bind(self, sequence=None, func=None, add=None):
        """外部绑定（如 <Return> 触发下载）同时挂到内层 Entry 上。"""
        result = super().bind(sequence, func, add)
        entry = self.__dict__.get("_entry")
        if entry is not None and func is not None:
            entry.bind(sequence, func, add)
        return result

    def focus_set(self):
        self._entry.focus_set()

    # cget/configure/get/delete/index… 在 Canvas 上都存在同名方法，会挡住
    # __getattr__ 的转发，所以这里逐个显式转发，保证"用起来就是一个 Entry"
    def cget(self, key):
        return self._entry.cget(key)

    def configure(self, *args, **kwargs):
        return self._entry.configure(*args, **kwargs)

    config = configure

    def get(self):
        return self._entry.get()

    def insert(self, *args):
        return self._entry.insert(*args)

    def delete(self, *args):
        return self._entry.delete(*args)

    def icursor(self, *args):
        return self._entry.icursor(*args)

    def index(self, *args):
        return self._entry.index(*args)

    def select_range(self, *args):
        return self._entry.select_range(*args)

    def __getattr__(self, name):
        entry = self.__dict__.get("_entry")
        if entry is not None:
            return getattr(entry, name)
        raise AttributeError(name)


# ===========================================================================
# [新增] 圆角下拉框：Canvas 圆角外壳 + 无边框 ttk.Combobox
# ===========================================================================
class RoundedCombo(tk.Canvas):
    def __init__(self, master, textvariable=None, values=(), width=16,
                 font=None, radius=COMBO_RADIUS):
        try:
            host_bg = bg = master.cget("bg")
        except Exception:
            host_bg = C["SURFACE"]
        self._radius = radius
        self._focused = False
        f = tkfont.Font(font=font or FONTS["ui"])
        w = f.measure("0") * width + 46
        h = f.metrics("linespace") + 16

        super().__init__(master, width=w, height=h, bg=host_bg, bd=0,
                         highlightthickness=0, relief="flat", takefocus=0)
        self._combo = ttk.Combobox(self, textvariable=textvariable,
                                   values=values, state="readonly",
                                   font=font or FONTS["ui"], width=width,
                                   style="Rounded.TCombobox")
        self._shape = self.create_polygon(
            self._points(1, 1, w - 1, h - 1, radius), smooth=True, splinesteps=10,
            fill=C["INPUT_BG"], outline=C["BORDER"], width=1)
        self._win = self.create_window(8, h // 2, window=self._combo, anchor="w",
                                       width=w - 16, height=h - 12)
        self._combo.bind("<FocusIn>", lambda _e: self._set_focus(True))
        self._combo.bind("<FocusOut>", lambda _e: self._set_focus(False))
        self._combo.bind("<Enter>", lambda _e: self._redraw(hover=True))
        self._combo.bind("<Leave>", lambda _e: self._redraw(hover=False))

    def _points(self, x1, y1, x2, y2, r):
        return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
                x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
                x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]

    def _set_focus(self, focused):
        self._focused = focused
        self._redraw()

    def _redraw(self, hover=None):
        if hover is not None:
            self._hover = hover
        outline = C["BORDER"]
        if self._focused:
            outline = C["ACCENT"]
        elif getattr(self, "_hover", False):
            outline = C["BORDER_HI"]
        self.itemconfigure(self._shape, outline=outline)

    # -- 对外接口：转发给内层 ttk.Combobox -------------------------------
    # 同样要显式转发 Canvas 上已存在的同名方法
    def bind(self, sequence=None, func=None, add=None):
        return self._combo.bind(sequence, func, add)

    def cget(self, key):
        return self._combo.cget(key)

    def configure(self, *args, **kwargs):
        return self._combo.configure(*args, **kwargs)

    config = configure

    def get(self):
        return self._combo.get()

    def set(self, value):
        return self._combo.set(value)

    def current(self, *args):
        return self._combo.current(*args)

    def __getattr__(self, name):
        """未定义的属性/方法转发给内层 ttk.Combobox（values/state…）。"""
        combo = self.__dict__.get("_combo")
        if combo is not None:
            return getattr(combo, name)
        raise AttributeError(name)


# ===========================================================================
# ④ 主界面
# ===========================================================================
class YtDlpGUI:
    def __init__(self, root):
        self.root = root
        self.proc = None            # 当前 yt-dlp 子进程
        self.busy = False           # 是否有任务在跑（用于禁用下载按钮）
        self.q = queue.Queue()      # reader 线程 -> 主线程 的消息队列
        self.live_active = False    # 日志中是否有一条 \r 进度行正在原地刷新
        self._cur_item = None       # 合集中当前正在下载的 (第几个, 共几个)
        self._after_id = None       # 定时刷新日志的 after 句柄（关闭时取消）

        self.url_var = tk.StringVar()
        self.cookie_var = tk.StringVar(value=COOKIE_OFF)
        self.quality_var = tk.StringVar(value=DEFAULT_QUALITY)  # 清晰度档位
        self.playlist_var = tk.BooleanVar(value=True)   # 默认勾选：下载整个合集/列表
        self.status_var = tk.StringVar(value="就绪")

        # ---- 保存位置 ----
        # builtin_dir：内置默认（源码运行 = 脚本目录，exe 运行 = exe 目录）
        # saved_default：用户在配置文件里记住的默认保存位置（可为 None）
        # out_dir：本次下载实际使用的目录（= dir_var 的内容）
        self.builtin_dir = app_dir()
        self.saved_default = self._read_saved_default()
        self.out_dir = self.saved_default or self.builtin_dir
        self.dir_var = tk.StringVar(value=self.out_dir)

        # ---- [新增] 高级选项状态（从配置文件恢复，缺键时用默认值）----
        self.cfg = self._load_config()                     # 整份配置（含未知字段）
        self.adv_expanded = bool(self.cfg.get(CFG_ADV_EXPANDED,
                                              ADV_DEFAULTS[CFG_ADV_EXPANDED]))
        self.proxy_var = tk.StringVar(
            value=str(self.cfg.get(CFG_ADV_PROXY, ADV_DEFAULTS[CFG_ADV_PROXY])))
        self.custom_args_var = tk.StringVar(
            value=str(self.cfg.get(CFG_ADV_CUSTOM_ARGS,
                                   ADV_DEFAULTS[CFG_ADV_CUSTOM_ARGS])))
        self.subs_var = tk.BooleanVar(
            value=bool(self.cfg.get(CFG_ADV_SUBS, ADV_DEFAULTS[CFG_ADV_SUBS])))
        self.limit_rate_var = tk.StringVar(
            value=str(self.cfg.get(CFG_ADV_LIMIT_RATE,
                                   ADV_DEFAULTS[CFG_ADV_LIMIT_RATE])))
        self._save_after_id = None      # 高级选项写盘防抖句柄
        # ---- [新增] 引擎版本（后台线程探测，不阻塞启动）----
        self.engine_var = tk.StringVar(value="引擎版本：检测中…")
        # ---- [新增] 视频预览状态 ----
        self.previewing = False         # 是否正在解析
        self._preview_win = None        # 预览窗口（复用同一个）
        self._preview_img = None        # 封面 PhotoImage 引用（防止被回收）
        self._preview_info = None       # 最近一次解析结果

        self._setup_style()
        self._build_ui()
        self._bind_events()
        self.refresh_preview()
        self.check_environment()
        self._start_version_probe()     # [新增] 异步取 yt-dlp --version
        self._after_id = self.root.after(60, self._drain_queue)

    # ------------------------------------------------------------------
    # 主题样式（ttk 用 clam 主题才能完整改色）
    # ------------------------------------------------------------------
    def _setup_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", background=C["BG"], foreground=C["TEXT"],
                        fieldbackground=C["INPUT_BG"], bordercolor=C["BORDER"],
                        focuscolor=C["ACCENT"], font=FONTS["ui"])

        # 下拉框
        style.configure("TCombobox", background=C["GHOST_BG"],
                        fieldbackground=C["INPUT_BG"], foreground=C["TEXT"],
                        arrowcolor=C["TEXT_DIM"], bordercolor=C["BORDER"],
                        lightcolor=C["BORDER"], darkcolor=C["BORDER"],
                        selectbackground=C["INPUT_BG"],
                        selectforeground=C["TEXT"], padding=3)
        style.map("TCombobox",
                  fieldbackground=[("readonly", C["INPUT_BG"])],
                  foreground=[("readonly", C["TEXT"])],
                  selectbackground=[("readonly", C["INPUT_BG"])],
                  selectforeground=[("readonly", C["TEXT"])],
                  bordercolor=[("focus", C["ACCENT"]), ("active", C["BORDER"])],
                  arrowcolor=[("active", C["TEXT"])],
                  background=[("active", C["GHOST_HI"])])
        # 下拉弹出列表（Tk Listbox）的颜色
        self.root.option_add("*TCombobox*Listbox.background", C["SURFACE"])
        self.root.option_add("*TCombobox*Listbox.foreground", C["TEXT"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", C["ACCENT"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.root.option_add("*TCombobox*Listbox.borderWidth", "1")
        self.root.option_add("*TCombobox*Listbox.font", FONTS["ui"])

        # [新增] 圆角外壳内嵌的下拉框：把自身方角边框"藏起来"，
        # 只保留外层 Canvas 画的圆角描边（聚焦/悬浮由外壳负责变色）
        style.configure("Rounded.TCombobox", background=C["INPUT_BG"],
                        fieldbackground=C["INPUT_BG"], foreground=C["TEXT"],
                        arrowcolor=C["TEXT_DIM"], bordercolor=C["INPUT_BG"],
                        lightcolor=C["INPUT_BG"], darkcolor=C["INPUT_BG"],
                        focuscolor=C["INPUT_BG"], padding=2, relief="flat")
        style.map("Rounded.TCombobox",
                  fieldbackground=[("readonly", C["INPUT_BG"])],
                  foreground=[("readonly", C["TEXT"])],
                  selectbackground=[("readonly", C["INPUT_BG"])],
                  selectforeground=[("readonly", C["TEXT"])],
                  bordercolor=[("focus", C["INPUT_BG"]),
                               ("active", C["INPUT_BG"])],
                  lightcolor=[("focus", C["INPUT_BG"])],
                  darkcolor=[("focus", C["INPUT_BG"])],
                  arrowcolor=[("active", C["ACCENT"]),
                              ("pressed", C["ACCENT"])],
                  background=[("active", C["INPUT_BG"])])

        # 细滚动条（[主题] 浅色配色）
        style.configure("Dark.Vertical.TScrollbar", background=C["SCROLL_BG"],
                        troughcolor=C["TROUGH"], bordercolor=C["TROUGH"],
                        arrowcolor=C["TEXT_DIM"], relief="flat", arrowsize=12)
        style.map("Dark.Vertical.TScrollbar",
                  background=[("active", C["SCROLL_HI"])])

        # 细进度条（[主题] 浅色槽 + 主色蓝填充）
        style.configure("Flat.Horizontal.TProgressbar", troughcolor=C["TROUGH"],
                        background=C["ACCENT"], bordercolor=C["TROUGH"],
                        lightcolor=C["ACCENT"], darkcolor=C["ACCENT"],
                        thickness=4)

    # ------------------------------------------------------------------
    # 界面搭建
    # ------------------------------------------------------------------
    def _build_ui(self):
        self.root.title(f"{APP_TITLE}  v{APP_VERSION}")
        self.root.configure(bg=C["BG"])
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        main = tk.Frame(self.root, bg=C["BG"])
        main.pack(fill="both", expand=True, padx=18, pady=(14, 12))

        # ---- 页头（参考 Win10 设置页标题） ----
        tk.Label(main, text="视频下载", bg=C["BG"], fg=C["TEXT"],
                 font=FONTS["h"], anchor="w").pack(fill="x")
        tk.Label(main,
                 text="粘贴链接 → 一键调用 yt-dlp 下载；支持 yt-dlp 兼容的全部站点",
                 bg=C["BG"], fg=C["TEXT_DIM"], font=FONTS["small"],
                 anchor="w").pack(fill="x", pady=(2, 12))

        # ---- 分组 1：视频链接 ----
        body = self._card(main, "视频链接")
        row = tk.Frame(body, bg=C["SURFACE"])
        row.pack(fill="x")
        tk.Label(row, text="URL", width=10, anchor="w", bg=C["SURFACE"],
                 fg=C["TEXT"], font=FONTS["ui"]).pack(side="left")
        self.url_entry = RoundedEntry(row, textvariable=self.url_var,
                                      font=FONTS["ui"])
        self.url_entry.pack(side="left", fill="x", expand=True)
        tk.Label(body,
                 text="例如：https://www.bilibili.com/video/BVxxxx ｜ "
                      "https://www.douyin.com/video/xxxx ｜ "
                      "https://www.youtube.com/watch?v=xxxx",
                 bg=C["SURFACE"], fg=C["TEXT_MUTE"], font=FONTS["small"],
                 anchor="w").pack(fill="x", pady=(6, 0))

        # ---- 分组 2：下载选项（清晰度 + Cookie 并排，下面是合集开关） ----
        body = self._card(main, "下载选项")
        row = tk.Frame(body, bg=C["SURFACE"])
        row.pack(fill="x")
        tk.Label(row, text="清晰度", width=10, anchor="w", bg=C["SURFACE"],
                 fg=C["TEXT"], font=FONTS["ui"]).pack(side="left")
        self.quality_box = RoundedCombo(row, textvariable=self.quality_var,
                                        values=[n for n, _ in QUALITY_CHOICES],
                                        width=18)
        self.quality_box.pack(side="left")
        tk.Label(row, text="Cookie", width=8, anchor="w", bg=C["SURFACE"],
                 fg=C["TEXT"], font=FONTS["ui"]).pack(side="left", padx=(26, 0))
        self.cookie_box = RoundedCombo(row, textvariable=self.cookie_var,
                                       values=COOKIE_CHOICES, width=16)
        self.cookie_box.pack(side="left")

        # 复选框：下载整个合集 / 列表（默认勾选）
        # 勾选 = 不加额外参数，合集链接会下载全部视频；
        # 取消 = 追加 --no-playlist，只下载当前链接对应的单个视频。
        row2 = tk.Frame(body, bg=C["SURFACE"])
        row2.pack(fill="x", pady=(8, 0))
        tk.Label(row2, text="合集", width=10, anchor="w", bg=C["SURFACE"],
                 fg=C["TEXT"], font=FONTS["ui"]).pack(side="left")
        self.chk_playlist = FlatCheck(row2, text="下载整个合集 / 列表",
                                      variable=self.playlist_var,
                                      command=self.refresh_preview)
        self.chk_playlist.pack(side="left")
        self.pl_hint = tk.Label(
            body, bg=C["SURFACE"], fg=C["TEXT_MUTE"], font=FONTS["small"],
            anchor="w", justify="left", wraplength=760)
        self.pl_hint.pack(fill="x", pady=(5, 0))
        self._update_playlist_hint()

        note = (
            "说明：Cookie 只用于「需要登录才能访问的受限内容」（会员视频、私密收藏、"
            "需登录的番剧等），普通公开视频请保持「不读取 Cookie」。\n"
            "⚠ Windows 下从浏览器读取 Cookie 需要走 DPAPI 解密，会受浏览器版本、"
            "多用户配置、浏览器仍在后台运行等因素影响，存在解密失败的风险；"
            "一旦 yt-dlp 报出 Cookie / DPAPI 相关错误，把下拉框切回"
            "「不读取 Cookie」即可正常下载。"
        )
        self.note_label = tk.Label(body, text=note, bg=C["SURFACE"],
                                   fg=C["TEXT_DIM"], font=FONTS["small"],
                                   anchor="w", justify="left", wraplength=760)
        self.note_label.pack(fill="x", pady=(8, 0))
        body.bind("<Configure>",
                  lambda e: self._resize_notes(e.width))

        # ---- [新增] 分组 2.5：高级选项（可折叠，默认收起） ----
        # 复用 _card()：展开/折叠仅 pack / pack_forget，不改动 _card 自身实现
        body = self._card(main, "高级选项", action=self._adv_header_action)
        self.adv_body = body

        row = tk.Frame(body, bg=C["SURFACE"])
        row.pack(fill="x")
        tk.Label(row, text="代理地址", width=10, anchor="w", bg=C["SURFACE"],
                 fg=C["TEXT"], font=FONTS["ui"]).pack(side="left")
        self.proxy_entry = self._make_entry(row, self.proxy_var)
        self.proxy_entry.pack(side="left", fill="x", expand=True)
        self.adv_proxy_hint = tk.Label(
            body, text="留空不使用代理；填写后追加 --proxy \"地址\"，"
                       "例如 http://127.0.0.1:7890",
            bg=C["SURFACE"], fg=C["TEXT_MUTE"], font=FONTS["small"],
            anchor="w", justify="left", wraplength=760)
        self.adv_proxy_hint.pack(fill="x", pady=(4, 0))

        row = tk.Frame(body, bg=C["SURFACE"])
        row.pack(fill="x", pady=(8, 0))
        tk.Label(row, text="附加参数", width=10, anchor="w", bg=C["SURFACE"],
                 fg=C["TEXT"], font=FONTS["ui"]).pack(side="left")
        self.custom_args_entry = self._make_entry(row, self.custom_args_var)
        self.custom_args_entry.pack(side="left", fill="x", expand=True)
        self.adv_args_hint = tk.Label(
            body, text="原样拼接到命令末尾的自定义 yt-dlp 参数，"
                       "例如 --no-check-certificate；留空不添加",
            bg=C["SURFACE"], fg=C["TEXT_MUTE"], font=FONTS["small"],
            anchor="w", justify="left", wraplength=760)
        self.adv_args_hint.pack(fill="x", pady=(4, 0))

        row = tk.Frame(body, bg=C["SURFACE"])
        row.pack(fill="x", pady=(8, 0))
        tk.Label(row, text="下载字幕", width=10, anchor="w", bg=C["SURFACE"],
                 fg=C["TEXT"], font=FONTS["ui"]).pack(side="left")
        self.chk_subs = FlatCheck(row, text="同时下载字幕（含自动生成字幕）",
                                  variable=self.subs_var,
                                  command=self._on_advanced_changed)
        self.chk_subs.pack(side="left")

        row = tk.Frame(body, bg=C["SURFACE"])
        row.pack(fill="x", pady=(8, 0))
        tk.Label(row, text="限速", width=10, anchor="w", bg=C["SURFACE"],
                 fg=C["TEXT"], font=FONTS["ui"]).pack(side="left")
        self.limit_rate_entry = self._make_entry(row, self.limit_rate_var,
                                                 width=14)
        self.limit_rate_entry.pack(side="left")
        self.adv_rate_hint = tk.Label(
            row, text="", bg=C["SURFACE"], fg=C["TEXT_MUTE"],
            font=FONTS["small"], anchor="w", justify="left")
        self.adv_rate_hint.pack(side="left", padx=(10, 0))

        row = tk.Frame(body, bg=C["SURFACE"])
        row.pack(fill="x", pady=(10, 0))
        FlatButton(row, "一键重置", self.reset_advanced, kind="ghost",
                   height=26, padx=12, font=FONTS["small"]).pack(side="left")
        tk.Label(row, text="清空代理 / 附加参数 / 字幕 / 限速，恢复默认状态",
                 bg=C["SURFACE"], fg=C["TEXT_MUTE"], font=FONTS["small"],
                 anchor="w").pack(side="left", padx=(10, 0))
        body.bind("<Configure>", lambda e: self._resize_adv_notes(e.width))

        # 恢复上次的展开状态；默认折叠（需求：启动默认收起）
        self._apply_advanced_visibility()
        self._update_limit_rate_hint()

        # ---- 分组 3：命令预览（只读） ----
        body = self._card(main, "命令预览（只读 · 实时刷新）",
                          action=lambda head: self._header_action(
                              head, "复制命令", self.copy_command))
        self.cmd_text = tk.Text(body, height=3, wrap="word",
                                bg=C["CMD_BG"], fg=C["CMD_FG"],
                                font=FONTS["mono"], relief="flat", bd=0,
                                padx=8, pady=6, state="disabled",
                                cursor="arrow", highlightthickness=1,
                                highlightbackground=C["BORDER"],
                                highlightcolor=C["BORDER"])
        self.cmd_text.pack(fill="x")
        tk.Label(body,
                 text="该命令即点击「开始下载」后实际执行的参数，可复制到 CMD 中自行调试。",
                 bg=C["SURFACE"], fg=C["TEXT_MUTE"], font=FONTS["small"],
                 anchor="w").pack(fill="x", pady=(6, 0))

        # ---- 操作栏 ----
        bar = tk.Frame(main, bg=C["BG"])
        bar.pack(fill="x", pady=(2, 10))

        left = tk.Frame(bar, bg=C["BG"])
        left.pack(side="left")
        self.btn_download = FlatButton(left, "开始下载", self.start_download,
                                       kind="primary", min_width=110)
        self.btn_download.pack(side="left")
        # [新增] 预览按钮：解析视频信息（不下载）
        self.btn_preview = FlatButton(left, "预览", self.start_preview,
                                      kind="ghost", min_width=84)
        self.btn_preview.pack(side="left", padx=(8, 0))
        self.btn_stop = FlatButton(left, "停止", self.stop_download,
                                   kind="ghost", min_width=70, state="disabled")
        self.btn_stop.pack(side="left", padx=(8, 0))
        self.btn_open = FlatButton(left, "打开输出目录", self.open_out_dir,
                                   kind="ghost", min_width=110)
        self.btn_open.pack(side="left", padx=(8, 0))

        right = tk.Frame(bar, bg=C["BG"])
        right.pack(side="right")
        # [新增] 引擎版本标签：显示 yt-dlp 版本号 + 二进制来源（便携版 / 系统PATH版）
        self.engine_lbl = tk.Label(right, textvariable=self.engine_var,
                                   bg=C["BG"], fg=C["TEXT_MUTE"],
                                   font=FONTS["small"], anchor="e")
        self.engine_lbl.pack(anchor="e")
        self.status_lbl = tk.Label(right, textvariable=self.status_var,
                                   bg=C["BG"], fg=C["TEXT_DIM"],
                                   font=FONTS["small"], anchor="e")
        self.status_lbl.pack(anchor="e")
        self.pbar = ttk.Progressbar(right, style="Flat.Horizontal.TProgressbar",
                                    mode="determinate", maximum=100, value=0,
                                    length=180)
        self.pbar.pack(anchor="e", pady=(4, 0))

        # ---- 页脚：保存位置（可选择 / 设为默认 / 恢复默认） + 依赖检查 ----
        # 先以 side="bottom" 占位，保证窗口被压矮时页脚始终可见，
        # 剩下的中间空间留给下面的日志框自动伸缩。
        foot = tk.Frame(main, bg=C["BG"])
        foot.pack(fill="x", side="bottom", pady=(10, 0))

        dirrow = tk.Frame(foot, bg=C["BG"])
        dirrow.pack(fill="x")
        tk.Label(dirrow, text="保存位置", width=8, anchor="w", bg=C["BG"],
                 fg=C["TEXT"], font=FONTS["small"]).pack(side="left")
        # 既可以直接粘贴路径，也可以用右侧按钮选择；
        # 这个文本框的内容就是"本次下载保存到哪里"
        self.dir_entry = RoundedEntry(dirrow, textvariable=self.dir_var,
                                      font=FONTS["small"])
        self.dir_entry.pack(side="left", fill="x", expand=True)
        self.btn_pick = FlatButton(dirrow, "选择文件夹…", self.choose_dir,
                                   kind="ghost", height=24, padx=10,
                                   font=FONTS["small"])
        self.btn_pick.pack(side="left", padx=(8, 0))
        self.btn_setdef = FlatButton(dirrow, "设为默认", self.set_as_default,
                                     kind="ghost", height=24, padx=10,
                                     font=FONTS["small"])
        self.btn_setdef.pack(side="left", padx=(6, 0))
        self.btn_reset = FlatButton(dirrow, "恢复默认", self.reset_default,
                                    kind="ghost", height=24, padx=10,
                                    font=FONTS["small"])
        self.btn_reset.pack(side="left", padx=(6, 0))
        self._update_dir_buttons()

        self.env_label = tk.Label(foot, text="依赖检查：检测中…", bg=C["BG"],
                                  fg=C["TEXT_DIM"], font=FONTS["small"],
                                  anchor="w", justify="left")
        self.env_label.pack(fill="x", pady=(2, 0))

        # ---- 分组 4：运行日志（占据剩余空间） ----
        body = self._card(main, "运行日志", expand=True,
                          action=lambda head: self._log_actions(head))
        wrap = tk.Frame(body, bg=C["SURFACE"])
        wrap.pack(fill="both", expand=True)
        self.log = tk.Text(wrap, bg=C["LOG_BG"], fg=C["LOG_FG"],
                           font=FONTS["mono"], relief="flat", bd=0,
                           padx=8, pady=6, wrap="word", state="disabled",
                           highlightthickness=1,
                           highlightbackground=C["BORDER"],
                           highlightcolor=C["BORDER"], height=6)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.log.yview,
                           style="Dark.Vertical.TScrollbar")
        self.log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)

        self.log.tag_configure("err", foreground=C["ERR"])
        self.log.tag_configure("ok", foreground=C["OK"])
        self.log.tag_configure("warn", foreground=C["WARN"])
        self.log.tag_configure("cmd", foreground=C["CMD_FG"])
        self.log.tag_configure("dim", foreground=C["TEXT_MUTE"])
        # 合集 / 单集分隔线
        self.log.tag_configure("rule", foreground=C["ACCENT_HI"])
        self.log.tag_configure("rule_ok", foreground=C["OK"])

    def _update_playlist_hint(self):
        """勾选框下方的说明文字，同时提示当前会追加什么参数。"""
        if self.playlist_var.get():
            self.pl_hint.configure(
                text="已勾选：不加额外参数，粘贴合集/列表链接会下载其中的全部视频；"
                     "普通单视频链接不受影响。")
        else:
            self.pl_hint.configure(
                text="已取消：追加 --no-playlist，只下载当前链接对应的那一个视频，"
                     "不进入合集。")

    def _resize_notes(self, width):
        """卡片宽度变化时同步两个说明标签的换行宽度。

        UI bugfix：窗口被缩到极小时，Configure 事件给出的 width 可能非常小
        （布局中间态甚至为 0/负数），旧的 max(320, width - 20) 会算出一个与控件
        实际可用宽度不匹配的 wraplength，说明文字因此被挤成一条竖排窄条。
        现在改为"按真实可用宽度收敛 + 合理下限保护"。
        """
        try:
            width = int(width)
        except (TypeError, ValueError):
            return
        if width <= 1:                      # 布局中间态，忽略这一帧
            return
        avail = max(ADV_HINT_WRAP_MIN, min(width - 20, 1600))
        self.note_label.configure(wraplength=avail)
        self.pl_hint.configure(wraplength=avail)

    def _resize_adv_notes(self, width):
        """[新增] 高级选项卡片内说明文字的同一套换行保护。"""
        try:
            width = int(width)
        except (TypeError, ValueError):
            return
        if width <= 1:
            return
        avail = max(ADV_HINT_WRAP_MIN, min(width - 20, 1600))
        self.adv_proxy_hint.configure(wraplength=avail)
        self.adv_args_hint.configure(wraplength=avail)

    # ------------------------------------------------------------------
    # [新增] 高级选项：输入框 / 折叠 / 参数拼装 / 持久化
    # ------------------------------------------------------------------
    def _make_entry(self, parent, var, font=None, width=None):
        """生成与现有输入框同款式的圆角输入框（聚焦蓝色高亮描边）。"""
        return RoundedEntry(parent, textvariable=var, font=font or FONTS["ui"],
                            width=width)

    def _adv_header_action(self, head):
        """在高级选项卡片的标题栏右侧放展开/折叠按钮。"""
        self.btn_adv_toggle = FlatButton(head, "展开 ▼", self.toggle_advanced,
                                         kind="ghost", min_width=84, height=24,
                                         padx=10, font=FONTS["small"])
        self.btn_adv_toggle.pack(side="right")

    def _apply_advanced_visibility(self):
        """按 self.adv_expanded 显示 / 隐藏高级选项内容区。"""
        if self.adv_expanded:
            self.adv_body.pack(fill="x", padx=14, pady=(6, 8))
            self.btn_adv_toggle.set_text("收起 ▲")
        else:
            self.adv_body.pack_forget()
            self.btn_adv_toggle.set_text("展开 ▼")

    def toggle_advanced(self):
        """展开 / 折叠高级选项，并把状态记进配置文件。"""
        self.adv_expanded = not self.adv_expanded
        self._apply_advanced_visibility()
        self._save_config({CFG_ADV_EXPANDED: self.adv_expanded})
        self.refresh_preview()               # 需求：新增选项变化即刷新命令预览

    def _on_advanced_changed(self):
        """高级选项任一取值变化：刷新命令预览 + 防抖写盘。"""
        self._update_limit_rate_hint()
        self.refresh_preview()
        self._schedule_config_save()

    def _schedule_config_save(self):
        """防抖：连续输入时只在停顿后写一次配置文件。"""
        if self._save_after_id is not None:
            try:
                self.root.after_cancel(self._save_after_id)
            except Exception:                        # noqa: BLE001
                pass
        try:
            self._save_after_id = self.root.after(600, self._flush_advanced_config)
        except tk.TclError:
            self._save_after_id = None

    def _flush_advanced_config(self):
        """把高级选项的当前取值合并写回配置文件（不覆盖其它字段）。"""
        self._save_after_id = None
        # 窗口可能已被销毁（直接 destroy 的场景），此时不再写盘
        try:
            if not self.root.winfo_exists():
                return
        except tk.TclError:
            return
        self._save_config({
            CFG_ADV_PROXY: self.proxy_var.get().strip(),
            CFG_ADV_CUSTOM_ARGS: self.custom_args_var.get().strip(),
            CFG_ADV_SUBS: bool(self.subs_var.get()),
            CFG_ADV_LIMIT_RATE: self.limit_rate_var.get().strip(),
        })

    def reset_advanced(self):
        """一键重置：清空代理 / 附加参数 / 字幕 / 限速，恢复默认状态。"""
        self.proxy_var.set("")
        self.custom_args_var.set("")
        self.subs_var.set(False)
        self.limit_rate_var.set("")
        self._on_advanced_changed()
        self._flush_advanced_config()        # 立即落盘，不等待防抖
        self._append("line", "dim", "高级选项已重置为默认状态。")

    def _update_limit_rate_hint(self):
        """限速输入校验提示：非法值给橙色提示且不追加参数。"""
        rate = self.limit_rate_var.get().strip()
        if not rate:
            self.adv_rate_hint.configure(text="如 500K / 2M，留空不限速",
                                         fg=C["TEXT_MUTE"])
        elif LIMIT_RATE_RE.match(rate):
            self.adv_rate_hint.configure(text=f"将追加 --limit-rate {rate}",
                                         fg=C["OK"])
        else:
            self.adv_rate_hint.configure(
                text="格式不正确（示例：500K / 1.5M），该项将被忽略",
                fg=C["WARN"])

    def _split_extra_args(self, text):
        """拆分用户填写的附加参数，支持用引号包住带空格的值。

        用 posix=False 保留 Windows 路径里的反斜杠，避免 C:\\dir 被吃掉转义符。
        """
        try:
            parts = shlex.split(text, posix=False)
        except ValueError:
            parts = text.split()
        out = []
        for p in parts:
            if len(p) >= 2 and p[0] == p[-1] and p[0] in "\"'":
                p = p[1:-1]
            if p:
                out.append(p)
        return out

    def advanced_args(self):
        """把高级选项翻译成 yt-dlp 参数；空值 / 非法值一律不追加。"""
        args = []
        proxy = self.proxy_var.get().strip()
        if proxy:
            args += ["--proxy", proxy]
        if self.subs_var.get():
            args += ["--write-sub", "--write-auto-sub"]
        rate = self.limit_rate_var.get().strip()
        if rate and LIMIT_RATE_RE.match(rate):
            args += ["--limit-rate", rate]
        extra = self.custom_args_var.get().strip()
        if extra:
            args += self._split_extra_args(extra)
        return args

    def _start_version_probe(self):
        """[新增] 后台线程执行 yt-dlp --version，结果经队列回主线程显示。"""
        def work():
            version = query_ytdlp_version(YTDLP_RESOLVED_PATH or YTDLP_BIN)
            self.q.put(("engine", version))
        threading.Thread(target=work, daemon=True).start()

    def _apply_engine_version(self, version):
        """把引擎版本 + 二进制来源写到状态区标签上。"""
        set_ytdlp_version(version)
        src = dependency_source_text(YTDLP_SOURCE)
        if version:
            self.engine_var.set(f"引擎 yt-dlp {version} · {src}")
            self.engine_lbl.configure(fg=C["TEXT_MUTE"])
            self._append("line", "dim", f"引擎版本：yt-dlp {version} {src}")
        else:
            self.engine_var.set(f"引擎版本未知 · {src}")
            self.engine_lbl.configure(fg=C["WARN"])
            self._append("line", "warn",
                         "未能获取 yt-dlp 版本号，请确认依赖可用。")

    def _binary_available(self, binary):
        """判断解析出的二进制是否可用：绝对路径看文件，裸命令名看 PATH。"""
        if not binary:
            return False
        if os.path.isabs(binary) or os.sep in binary:
            return os.path.isfile(binary)
        return shutil.which(binary) is not None

    def _show_missing_deps_dialog(self, missing):
        """[新增] 缺失依赖引导弹窗：给出可一键复制的 winget 安装命令。

        说明：messagebox 无法承载"可复制"的交互，所以这里用 Toplevel 自绘一个
        同主题的小弹窗；若创建失败则回退到原来的 messagebox 提示。
        """
        names = "、".join(missing)
        try:
            win = tk.Toplevel(self.root)
            win.title("缺少依赖")
            win.configure(bg=C["BG"])
            win.transient(self.root)
            win.resizable(False, False)

            box = tk.Frame(win, bg=C["SURFACE"], highlightthickness=1,
                           highlightbackground=C["BORDER"])
            box.pack(fill="both", expand=True, padx=16, pady=16)

            tk.Label(box, text=f"未检测到：{names}", bg=C["SURFACE"],
                     fg=C["ERR"], font=FONTS["card"], anchor="w").pack(
                fill="x", padx=16, pady=(14, 4))
            tk.Label(box,
                     text="请在 PowerShell 中执行下面的命令安装（点击「复制命令」"
                          "后粘贴即可），安装完成后重启本程序：",
                     bg=C["SURFACE"], fg=C["TEXT_DIM"], font=FONTS["small"],
                     anchor="w", justify="left",
                     wraplength=460).pack(fill="x", padx=16)

            cmd_text = tk.Text(box, height=len(WINGET_COMMANDS) + 1, width=52,
                               bg=C["CMD_BG"], fg=C["CMD_FG"],
                               font=FONTS["mono"], relief="flat", bd=0,
                               padx=10, pady=8, wrap="none")
            cmd_text.insert("1.0", "\n".join(WINGET_COMMANDS))
            cmd_text.configure(state="disabled")
            cmd_text.pack(fill="x", padx=16, pady=(8, 4))

            btns = tk.Frame(box, bg=C["SURFACE"])
            btns.pack(fill="x", padx=16, pady=(4, 14))

            def copy_cmds():
                self.root.clipboard_clear()
                self.root.clipboard_append("\n".join(WINGET_COMMANDS))
                self._append("line", "dim", "winget 安装命令已复制到剪贴板。")

            FlatButton(btns, "复制命令", copy_cmds, kind="primary",
                       min_width=100, height=28,
                       font=FONTS["small"]).pack(side="left")
            FlatButton(btns, "关闭", win.destroy, kind="ghost",
                       min_width=80, height=28,
                       font=FONTS["small"]).pack(side="left", padx=(8, 0))

            win.update_idletasks()
            x = self.root.winfo_rootx() + max(
                0, (self.root.winfo_width() - win.winfo_width()) // 2)
            y = self.root.winfo_rooty() + 120
            win.geometry(f"+{x}+{y}")
            try:
                win.grab_set()               # 模态，避免误操作
            except tk.TclError:
                pass
            self._append("line", "err",
                         f"缺少依赖：{names}。请按弹窗中的 winget 命令安装后重启。")
        except tk.TclError:
            # 回退：任何异常情况下仍然给出带命令的 messagebox 提示
            messagebox.showerror(
                "缺少依赖",
                f"未检测到：{names}\n\n请在 PowerShell 中执行：\n"
                + "\n".join(WINGET_COMMANDS)
                + "\n\n安装完成后重启本程序。", parent=self.root)

    def _card(self, parent, title, action=None, expand=False):
        """创建一个 Win10 设置风格的分组卡片，返回可放置内容的内层 Frame。"""
        card = tk.Frame(parent, bg=C["SURFACE"], bd=0,
                        highlightthickness=1, highlightbackground=C["BORDER"])
        # [主题] 按钮/控件加高后纵向空间紧张，卡片内外边距适当收紧，
        # 把省下来的高度让给下方的运行日志区
        card.pack(fill="both" if expand else "x", expand=expand,
                  pady=(0, 7))
        head = tk.Frame(card, bg=C["SURFACE"])
        head.pack(fill="x", padx=14, pady=(7, 0))
        tk.Label(head, text=title, bg=C["SURFACE"], fg=C["TEXT"],
                 font=FONTS["card"], anchor="w").pack(side="left")
        if action:
            action(head)
        body = tk.Frame(card, bg=C["SURFACE"])
        body.pack(fill="both" if expand else "x", expand=expand,
                  padx=14, pady=(6, 8))
        return body

    def _header_action(self, head, text, command):
        FlatButton(head, text, command, kind="ghost", min_width=84,
                   height=24, padx=10,
                   font=FONTS["small"]).pack(side="right")

    def _log_actions(self, head):
        FlatButton(head, "复制日志", self.copy_log, kind="ghost",
                   min_width=84, height=24, padx=10,
                   font=FONTS["small"]).pack(side="right")
        FlatButton(head, "清空日志", self.clear_log, kind="ghost",
                   min_width=84, height=24, padx=10,
                   font=FONTS["small"]).pack(side="right", padx=(0, 8))

    def _bind_events(self):
        # URL / 清晰度 / Cookie / 合集勾选 变化 → 实时刷新命令预览
        self.url_var.trace_add("write", lambda *_: self.refresh_preview())
        self.quality_var.trace_add("write", lambda *_: self.refresh_preview())
        self.cookie_var.trace_add("write", lambda *_: self.refresh_preview())
        self.playlist_var.trace_add("write", lambda *_: self._on_playlist_toggle())
        # 保存位置变化 → 刷新 -P 参数与按钮可用状态
        self.dir_var.trace_add("write", lambda *_: self._on_dir_changed())
        # [新增] 高级选项任一取值变化 → 刷新命令预览 + 记忆到配置文件
        self.proxy_var.trace_add("write", lambda *_: self._on_advanced_changed())
        self.custom_args_var.trace_add("write",
                                       lambda *_: self._on_advanced_changed())
        self.subs_var.trace_add("write", lambda *_: self._on_advanced_changed())
        self.limit_rate_var.trace_add("write",
                                      lambda *_: self._on_advanced_changed())
        # 回车即开始下载
        self.url_entry.bind("<Return>", lambda _e: self.start_download())

    def _on_playlist_toggle(self):
        self._update_playlist_hint()
        self.refresh_preview()

    # ------------------------------------------------------------------
    # 命令行拼装
    # ------------------------------------------------------------------
    def selected_format(self):
        """把「清晰度」下拉选项翻译成 yt-dlp 的 -f 格式选择器。"""
        return QUALITY_MAP.get(self.quality_var.get(), DEFAULT_FORMAT)

    def build_command(self):
        """拼装实际要执行的 yt-dlp 命令（列表形式，直接喂给 subprocess）。"""
        # 清晰度：默认档位就是原始基础参数 -f "bv*+ba"
        cmd = [YTDLP_BIN, "-f", self.selected_format()] + BASE_ARGS
        # 合集开关：勾选时不加任何参数（合集链接自动下载全部视频）；
        # 取消勾选时追加 --no-playlist，只下载当前链接对应的单个视频。
        if not self.playlist_var.get():
            cmd.append("--no-playlist")
        # Cookie：选择「不读取 Cookie」时不追加任何参数，命令保持纯净
        browser = BROWSER_MAP.get(self.cookie_var.get())
        if browser:
            cmd += ["--cookies-from-browser", browser]
        # [新增] 高级选项：代理 / 字幕 / 限速 / 自定义附加参数（空值不追加）
        cmd += self.advanced_args()
        # 输出目录 + 文件名模板
        cmd += ["-P", self.out_dir, "-o", OUTPUT_TEMPLATE]
        url = self.url_var.get().strip()
        if url:
            cmd.append(url)
        return cmd

    def refresh_preview(self):
        """把当前命令写入只读预览区。"""
        text = format_command(self.build_command())
        self.cmd_text.configure(state="normal")
        self.cmd_text.delete("1.0", "end")
        self.cmd_text.insert("1.0", text)
        self.cmd_text.configure(state="disabled")

    # ------------------------------------------------------------------
    # 环境自检
    # ------------------------------------------------------------------
    def check_environment(self):
        # [新增] 依赖路径以 runtime 解析结果为准（便携版优先 / PATH 回退）
        ytdlp_path = YTDLP_RESOLVED_PATH
        ffmpeg_path = FFMPEG_RESOLVED_PATH
        parts, bad = [], []
        # [新增] 标注来源：【本地便携版】/【系统PATH版本】，并用颜色区分状态
        if ytdlp_path:
            parts.append(f"yt-dlp ✓{dependency_source_text(YTDLP_SOURCE)}  "
                         f"{ytdlp_path}")
        else:
            parts.append("yt-dlp ✗  未找到（本地目录与系统 PATH 都没有）")
            bad.append("yt-dlp")
        if ffmpeg_path:
            parts.append(f"ffmpeg ✓{dependency_source_text(FFMPEG_SOURCE)}  "
                         f"{ffmpeg_path}")
        else:
            parts.append("ffmpeg ✗  未找到（本地目录与系统 PATH 都没有）")
            bad.append("ffmpeg")
        self.env_label.configure(text="依赖检查：" + "    ".join(parts),
                                 fg=C["ERR"] if bad else C["OK"])
        self._append("line", "dim",
                     f"依赖检查：yt-dlp={ytdlp_path or '未找到'}"
                     f"{dependency_source_text(YTDLP_SOURCE)} | "
                     f"ffmpeg={ffmpeg_path or '未找到'}"
                     f"{dependency_source_text(FFMPEG_SOURCE)}")
        self._append("line", "dim", f"程序目录：{self.builtin_dir}"
                                   "（便携版 yt-dlp.exe / ffmpeg.exe 放这里即被优先使用）")
        # 保存位置自检：配置里记住的目录没了（换机器 / 拔了移动盘）就回退
        if self.saved_default and not self._ensure_dir(self.saved_default,
                                                       quiet=True):
            self._append("line", "warn",
                         f"配置的默认保存位置不可用：{self.saved_default}，"
                         f"已回退到内置默认目录。")
            self.saved_default = None
            self.dir_var.set(self.builtin_dir)
        src = ("用户设置的默认值" if self.saved_default
               else "内置默认（源码运行=脚本目录，exe 运行=exe 所在目录）")
        self._append("line", "dim", f"保存位置：{self.out_dir}    [{src}]")
        if bad:
            self._append("line", "warn",
                         "缺少依赖：" + "、".join(bad) +
                         "。点「开始下载」会给出 winget 安装命令。")

    # ------------------------------------------------------------------
    # 下载流程
    # ------------------------------------------------------------------
    def start_download(self):
        if self.busy:
            return
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("缺少链接", "请先粘贴视频链接。", parent=self.root)
            self.url_entry.focus_set()
            return
        if not url.lower().startswith(("http://", "https://")):
            messagebox.showwarning("链接格式有误",
                                   "请粘贴以 http:// 或 https:// 开头的视频网页链接。",
                                   parent=self.root)
            self.url_entry.focus_set()
            return
        if not self._binary_available(YTDLP_BIN) or \
                not self._binary_available(FFMPEG_BIN):
            # [新增] 依赖缺失：弹窗给出可复制的 winget 安装命令
            missing = []
            if not self._binary_available(YTDLP_BIN):
                missing.append("yt-dlp")
            if not self._binary_available(FFMPEG_BIN):
                missing.append("ffmpeg")
            self._show_missing_deps_dialog(missing)
            return
        # 保存位置：不存在就创建，创建不了就别启动子进程了
        if not self._ensure_dir(self.out_dir):
            return

        cmd = self.build_command()
        self._set_busy(True)
        self._cur_item = None            # 重置合集进度状态
        self._append("line", "dim",
                     f"{'=' * 12} {time.strftime('%H:%M:%S')} 开始任务 {'=' * 12}")
        self._append("line", "cmd", format_command(cmd))
        self.pbar.configure(value=0)

        threading.Thread(target=self._worker, args=(cmd,),
                         daemon=True).start()

    def _worker(self, cmd):
        """后台线程：拉起 yt-dlp 并把 stdout / stderr 流式送进队列。"""
        env = os.environ.copy()
        # 让 Python 版 yt-dlp（含 PyInstaller 打包出来的 yt-dlp.exe）强制输出 UTF-8
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["PYTHONUNBUFFERED"] = "1"
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,                      # 无缓冲，保证实时性
                env=env,
                creationflags=CREATE_NO_WINDOW,  # 不弹出黑色控制台窗口
            )
        except FileNotFoundError:
            self.q.put(("fatal", f"未找到可执行文件：{cmd[0]}（请检查系统 PATH）"))
            return
        except OSError as exc:
            self.q.put(("fatal", f"启动子进程失败：{exc}"))
            return

        self.proc = proc
        t_out = threading.Thread(target=self._pump, args=(proc.stdout, "stdout"),
                                 daemon=True)
        t_err = threading.Thread(target=self._pump, args=(proc.stderr, "stderr"),
                                 daemon=True)
        t_out.start()
        t_err.start()
        t_out.join()
        t_err.join()
        rc = proc.wait()
        self.proc = None
        self.q.put(("done", rc))

    def _pump(self, stream, name):
        """读取管道原始字节，按 \\r / \\n 切块后入队（\\r 视为原地刷新的进度行）。"""
        buf = b""
        while True:
            try:
                chunk = stream.read(512)
            except (OSError, ValueError):
                break
            if not chunk:
                break
            buf += chunk
            while True:
                m = _SPLIT_RE.search(buf)
                if not m:
                    break
                seg, term = buf[:m.start()], buf[m.start():m.end()]
                buf = buf[m.end():]
                text = _ANSI_RE.sub("", decode_output(seg).strip("\r\n"))
                if term == b"\r":
                    if text:
                        self.q.put(("live", name, text))
                else:
                    self.q.put(("line", name, text))
        if buf.strip():
            self.q.put(("line", name, _ANSI_RE.sub("", decode_output(buf).strip())))

    def stop_download(self):
        """终止当前任务（Windows 下连同 ffmpeg 子进程一起结束）。"""
        proc = self.proc
        if proc is None or proc.poll() is not None:
            return
        self._append("line", "warn", "正在停止下载…")
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL,
                               creationflags=CREATE_NO_WINDOW)
            else:
                proc.terminate()
        except Exception as exc:                      # noqa: BLE001
            self._append("line", "err", f"停止失败：{exc}")

    # ------------------------------------------------------------------
    # 日志渲染（仅主线程操作 Tk 控件）
    # ------------------------------------------------------------------
    def _drain_queue(self):
        # 窗口可能已被销毁（关窗 / 测试脚本直接 destroy），此时直接退出，
        # 避免 Tk 报 "invalid command name ..._drain_queue"
        try:
            if not self.root.winfo_exists():
                return
        except tk.TclError:
            return
        try:
            while True:
                item = self.q.get_nowait()
                kind = item[0]
                if kind in ("line", "live"):
                    _, stream, text = item
                    self._render(stream, text, live=(kind == "live"))
                elif kind == "done":
                    self._on_finished(item[1])
                elif kind == "fatal":
                    self._append("line", "err", item[1])
                    self._on_finished(-1)
                elif kind == "engine":            # [新增] yt-dlp 版本探测回填
                    self._apply_engine_version(item[1])
                elif kind == "preview":           # [新增] 视频预览解析结果
                    self._on_preview_result(item[1], item[2])
        except queue.Empty:
            pass
        finally:
            try:
                self._after_id = self.root.after(60, self._drain_queue)
            except tk.TclError:          # 窗口已销毁
                self._after_id = None

    def _render(self, stream, text, live=False):
        """把一行输出写进日志框；\\r 进度行原地覆盖上一条。"""
        # 进度条解析
        if not live:
            m = _PCT_RE.search(text)
            if m:
                try:
                    self.pbar.configure(value=min(100.0, float(m.group(1))))
                except ValueError:
                    pass
        if not live:
            # 合集/列表：插入清晰分隔，让用户一眼看出正在下第几个；
            # 分隔线只是额外补在前面，yt-dlp 的原始输出照常原样打印。
            self._mark_playlist(text)
        tag = "err" if stream == "stderr" else None
        if stream == "stderr":
            text = "[stderr] " + text
        if not text.strip():
            # 空行：仅用于结束当前的原地刷新行
            if self.live_active:
                self._delete_live()
            return
        self._append("live" if live else "line", tag, text)

    # -- 合集分隔线 ------------------------------------------------------
    def _rule(self, text, tag="rule"):
        """打印一条左右带横线的分隔行。"""
        self._append("line", tag, f"{'─' * RULE_WIDTH}  {text}  {'─' * RULE_WIDTH}")

    def _mark_playlist(self, text):
        """识别合集的开始/单集切换/结束，插入分隔线。返回是否为合集相关行。

        yt-dlp 的典型输出：
            [download] Downloading playlist: 某某合集
            [download] Downloading item 3 of 12
            ...
            [download] Finished downloading playlist: 某某合集
        原始的 item 行不做任何改写，分隔线只是额外补在它前面。
        """
        m = _PL_ITEM_RE.search(text)
        if m:
            index, total = int(m.group(1)), int(m.group(2))
            if self._cur_item:                 # 上一集到此结束
                self._rule(f"✓ 第 {self._cur_item[0]} / {self._cur_item[1]} 个 已完成",
                           "rule_ok")
            self._rule(f"第 {index} / {total} 个")
            self._cur_item = (index, total)
            return True
        if _PL_END_RE.search(text):
            if self._cur_item:
                self._rule(f"✓ 第 {self._cur_item[0]} / {self._cur_item[1]} 个 已完成",
                           "rule_ok")
                self._cur_item = None
            self._rule("合集下载结束", "rule_ok")
            return True
        m = _PL_START_RE.search(text)
        if m:
            self._cur_item = None
            self._rule(f"合集开始：{m.group(1)}")
            return True
        return False

    def _append(self, kind, tag, text):
        self.log.configure(state="normal")
        try:
            if kind == "live":
                if self.live_active:
                    self.log.delete("live_start", "end-1c")
                else:
                    self.log.mark_set("live_start", "end-1c")
                    self.log.mark_gravity("live_start", tk.LEFT)
                    self.live_active = True
                self.log.insert("end", text, (tag,) if tag else ())
            else:
                if self.live_active:
                    self._delete_live()
                self.log.insert("end", text + "\n", (tag,) if tag else ())
            self._trim_log()
            # 仅当视图本来就在底部时才自动滚动，避免打扰向上翻阅
            if self.log.yview()[1] > 0.999:
                self.log.see("end")
        finally:
            self.log.configure(state="disabled")

    def _delete_live(self):
        """清除正在原地刷新的进度行（Tk 的 Text 在 disabled 状态下会忽略删除操作，
        所以这里必须先临时切回 normal）。"""
        if not self.live_active:
            return
        self.log.configure(state="normal")
        try:
            self.log.delete("live_start", "end-1c")
        except tk.TclError:
            pass
        self.live_active = False

    def _trim_log(self):
        """日志过长时从头部裁剪，避免长时间下载内存膨胀。"""
        if self.live_active:
            return
        last_line = int(self.log.index("end-1c").split(".")[0])
        if last_line > LOG_MAX_LINES:
            self.log.delete("1.0", f"{last_line - LOG_KEEP_LINES}.0")

    def _on_finished(self, rc):
        self._set_busy(False)
        if rc == 0:
            self._append("line", "ok", f"✓ 任务完成，文件已保存到：{self.out_dir}")
            self.pbar.configure(value=100)
            self._set_status("已完成", C["OK"])
        else:
            self.pbar.configure(value=0)
            self._append("line", "err",
                         f"✗ yt-dlp 退出码 {rc}，请查看上方日志定位原因。"
                         f"若为 Cookie / DPAPI 报错，请把 Cookie 切回"
                         f"「{COOKIE_OFF}」。")
            self._set_status(f"失败（退出码 {rc}）", C["ERR"])

    def _set_busy(self, busy):
        """下载中禁用「开始下载」，结束/出错后自动恢复可用。"""
        self.busy = busy
        self.btn_download.set_state("disabled" if busy else "normal")
        self.btn_stop.set_state("normal" if busy else "disabled")
        self.btn_download.set_text("下载中…" if busy else "开始下载")
        # [新增] 下载期间也把「预览」一并禁用，避免同时跑两个 yt-dlp 进程
        self._update_preview_button()
        if busy:
            self._set_status("下载中…", C["ACCENT_HI"])

    def _set_status(self, text, color):
        self.status_var.set(text)
        self.status_lbl.configure(fg=color)

    # ------------------------------------------------------------------
    # [新增] 视频预览：解析链接信息 + 封面，不产生下载
    # ------------------------------------------------------------------
    def _update_preview_button(self):
        """预览按钮的可用状态与文案（下载中或解析中均禁用）。"""
        busy = self.busy or self.previewing
        self.btn_preview.set_state("disabled" if busy else "normal")
        self.btn_preview.set_text("解析中…" if self.previewing else "预览")

    def start_preview(self):
        """点击「预览」：后台解析当前链接的视频信息。"""
        if self.previewing:
            return
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("缺少链接", "请先粘贴视频链接。",
                                   parent=self.root)
            self.url_entry.focus_set()
            return
        if not url.lower().startswith(("http://", "https://")):
            messagebox.showwarning("链接格式有误",
                                   "请粘贴以 http:// 或 https:// 开头的视频网页链接。",
                                   parent=self.root)
            self.url_entry.focus_set()
            return
        if not self._binary_available(YTDLP_BIN):
            self._show_missing_deps_dialog(["yt-dlp"])
            return
        self.previewing = True
        self._update_preview_button()
        self._set_status("解析中…", C["ACCENT_HI"])
        self._append("line", "dim", f"正在解析视频信息：{url}")
        # 注意：Tk 变量不是线程安全的，必须在主线程先把界面状态取成普通 Python 值，
        # 再交给后台线程（否则后台线程调用 xxx_var.get() 会报
        # "main thread is not in main loop"）
        options = {
            "browser": BROWSER_MAP.get(self.cookie_var.get()),
            "proxy": self.proxy_var.get().strip(),
            "extra": self.custom_args_var.get().strip(),
        }
        threading.Thread(target=self._preview_worker, args=(url, options),
                         daemon=True).start()

    def _preview_worker(self, url, options):
        """后台线程：yt-dlp --dump-json 取信息，再抓封面转 PNG。

        options 是主线程预先取好的界面设置（Cookie / 代理 / 附加参数），
        本线程内不再触碰任何 Tk 控件。
        """
        cmd = [YTDLP_BIN, "--dump-json", "--no-warnings", "--playlist-items", "1"]
        # 复用界面上的 Cookie / 代理 / 附加参数设置，受限内容也能解析
        if options.get("browser"):
            cmd += ["--cookies-from-browser", options["browser"]]
        if options.get("proxy"):
            cmd += ["--proxy", options["proxy"]]
        if options.get("extra"):
            cmd += self._split_extra_args(options["extra"])
        cmd.append(url)

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        try:
            out = subprocess.run(
                cmd, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=PREVIEW_TIMEOUT, env=env,
                creationflags=CREATE_NO_WINDOW)
        except FileNotFoundError:
            self.q.put(("preview", None, f"未找到可执行文件：{cmd[0]}"))
            return
        except subprocess.TimeoutExpired:
            self.q.put(("preview", None,
                        f"解析超时（{PREVIEW_TIMEOUT} 秒），请检查网络或代理设置。"))
            return
        except OSError as exc:
            self.q.put(("preview", None, f"启动解析进程失败：{exc}"))
            return

        info = None
        for line in decode_output(out.stdout or b"").splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    info = json.loads(line)
                    break
                except ValueError:
                    continue
        if not isinstance(info, dict):
            errs = [ln for ln in decode_output(out.stderr or b"").splitlines()
                    if ln.strip()]
            reason = errs[-1].strip() if errs else "未获取到视频信息"
            self.q.put(("preview", None, reason))
            return

        png, thumb_err = self._load_thumbnail(info)
        self.q.put(("preview", {"info": info, "png": png, "thumb_err": thumb_err},
                    ""))
        return

    def _load_thumbnail(self, info):
        """取封面地址并转成 PNG 字节。"""
        url = info.get("thumbnail")
        if not url:
            thumbs = info.get("thumbnails") or []
            if thumbs and isinstance(thumbs[-1], dict):
                url = thumbs[-1].get("url")
        if not url:
            return None, ""
        headers = {"User-Agent": PREVIEW_UA}
        for key, value in (info.get("http_headers") or {}).items():
            if value:
                headers[key] = value
        return fetch_thumbnail_png(url, headers)

    def _on_preview_result(self, payload, error):
        """主线程：解析结束，刷新按钮状态并弹出/刷新预览窗口。"""
        self.previewing = False
        self._update_preview_button()
        self._set_status("就绪", C["TEXT_DIM"])
        if not payload:
            self._append("line", "err", f"✗ 解析失败：{error}")
            messagebox.showerror("解析失败", error or "未知错误", parent=self.root)
            return
        info = payload.get("info") or {}
        self._preview_info = info
        title = first_field(info, ("title", "fulltitle"), "(无标题)")
        self._append("line", "ok", f"✓ 解析成功：{title}")
        if payload.get("thumb_err"):
            self._append("line", "warn", payload["thumb_err"])
        self._show_preview_window(info, payload.get("png"))

    def _show_preview_window(self, info, png):
        """[新增] 同主题的预览窗口：左边封面，右边信息，可复制。"""
        win = getattr(self, "_preview_win", None)
        try:
            alive = win is not None and win.winfo_exists()
        except tk.TclError:
            alive = False
        if alive:
            for child in win.winfo_children():     # 复用窗口，原地刷新
                child.destroy()
        else:
            win = tk.Toplevel(self.root)
            self._preview_win = win
            win.title("视频预览")
            win.configure(bg=C["BG"])
            win.transient(self.root)

        card = tk.Frame(win, bg=C["SURFACE"], highlightthickness=1,
                        highlightbackground=C["BORDER"])
        card.pack(fill="both", expand=True, padx=14, pady=14)

        head = tk.Frame(card, bg=C["SURFACE"])
        head.pack(fill="x", padx=14, pady=(10, 0))
        tk.Label(head, text="视频预览", bg=C["SURFACE"], fg=C["TEXT"],
                 font=FONTS["card"], anchor="w").pack(side="left")

        body = tk.Frame(card, bg=C["SURFACE"])
        body.pack(fill="both", expand=True, padx=14, pady=(8, 10))

        # ---- 左：封面 ----
        cover = tk.Frame(body, bg=C["SURFACE"])
        cover.pack(side="left", anchor="n")
        image = None
        if png:
            image = self._make_photo(png)
        self._preview_img = image       # 保持引用，避免被 GC 掉
        if image is not None:
            holder = tk.Label(cover, image=image, bg=C["SURFACE"],
                              highlightthickness=1,
                              highlightbackground=C["BORDER"], bd=0)
        else:
            holder = tk.Label(cover, text="（无封面）", bg=C["LOG_BG"],
                              fg=C["TEXT_MUTE"], font=FONTS["small"],
                              width=30, height=10,
                              highlightthickness=1,
                              highlightbackground=C["BORDER"])
        holder.pack()

        # ---- 右：信息 ----
        panel = tk.Frame(body, bg=C["SURFACE"])
        panel.pack(side="left", fill="both", expand=True, padx=(16, 0))

        rows = []
        for label, keys in PREVIEW_FIELDS:
            value = first_field(info, keys)
            if label == "时长":
                value = format_duration(value) or value
            elif label == "上传日期":
                value = format_upload_date(value)
            elif label in ("播放量", "点赞数"):
                value = format_count(value)
            elif label == "简介":
                value = str(value).strip().replace("\n", " ")
                if len(value) > 120:
                    value = value[:120] + "…"
            if value in (None, ""):
                continue
            rows.append((label, str(value)))
        qualities = format_quality_list(info)
        if qualities:
            rows.append(("可选清晰度", qualities))
        webpage = first_field(info, ("webpage_url", "original_url"))
        if webpage:
            rows.append(("网页链接", str(webpage)))

        for label, value in rows:
            row = tk.Frame(panel, bg=C["SURFACE"])
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"{label}", bg=C["SURFACE"], fg=C["TEXT_DIM"],
                     font=FONTS["small"], width=9, anchor="nw").pack(side="left")
            tk.Label(row, text=value, bg=C["SURFACE"], fg=C["TEXT"],
                     font=FONTS["small"], anchor="w", justify="left",
                     wraplength=430).pack(side="left", fill="x", expand=True)

        btns = tk.Frame(card, bg=C["SURFACE"])
        btns.pack(fill="x", padx=14, pady=(0, 12))
        FlatButton(btns, "复制信息", lambda: self._copy_preview_info(info),
                   kind="primary", min_width=100, height=30,
                   font=FONTS["small"]).pack(side="left")
        FlatButton(btns, "用浏览器打开",
                   lambda: self._open_preview_url(info),
                   kind="ghost", min_width=110, height=30,
                   font=FONTS["small"]).pack(side="left", padx=(8, 0))
        FlatButton(btns, "关闭", self._close_preview_window, kind="ghost",
                   min_width=80, height=30,
                   font=FONTS["small"]).pack(side="right")

        win.update_idletasks()
        w = max(620, win.winfo_reqwidth())
        h = max(320, win.winfo_reqheight())
        x = self.root.winfo_rootx() + max(
            0, (self.root.winfo_width() - w) // 2)
        y = self.root.winfo_rooty() + 60
        win.geometry(f"{w}x{h}+{x}+{y}")

    def _make_photo(self, png):
        """[新增] PNG 字节 -> PhotoImage；data= 失败时退回临时文件加载。"""
        try:
            return tk.PhotoImage(data=base64.b64encode(png).decode("ascii"))
        except tk.TclError:
            pass
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as fh:
                fh.write(png)
                path = fh.name
            image = tk.PhotoImage(file=path)
            try:
                os.remove(path)
            except OSError:
                pass
            return image
        except Exception:                                 # noqa: BLE001
            return None

    def _preview_text(self, info):
        """把解析结果整理成可复制的文本。"""
        lines = []
        for label, keys in PREVIEW_FIELDS:
            value = first_field(info, keys)
            if label == "时长":
                value = format_duration(value) or value
            elif label == "上传日期":
                value = format_upload_date(value)
            elif label in ("播放量", "点赞数"):
                value = format_count(value)
            if value in (None, ""):
                continue
            lines.append(f"{label}：{value}")
        qualities = format_quality_list(info)
        if qualities:
            lines.append(f"可选清晰度：{qualities}")
        webpage = first_field(info, ("webpage_url", "original_url"))
        if webpage:
            lines.append(f"网页链接：{webpage}")
        return "\n".join(lines)

    def _copy_preview_info(self, info):
        self.root.clipboard_clear()
        self.root.clipboard_append(self._preview_text(info))
        self._append("line", "dim", "视频信息已复制到剪贴板。")

    def _open_preview_url(self, info):
        url = first_field(info, ("webpage_url", "original_url"))
        if not url:
            return
        try:
            if os.name == "nt":
                os.startfile(url)                        # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", url])
            else:
                subprocess.Popen(["xdg-open", url])
        except Exception as exc:                          # noqa: BLE001
            messagebox.showerror("无法打开链接", str(exc), parent=self.root)

    def _close_preview_window(self):
        win = getattr(self, "_preview_win", None)
        self._preview_win = None
        self._preview_img = None
        if win is not None:
            try:
                win.destroy()
            except tk.TclError:
                pass

    # ------------------------------------------------------------------
    # 小工具按钮
    # ------------------------------------------------------------------
    def copy_command(self):
        text = self.cmd_text.get("1.0", "end-1c").strip()
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._append("line", "dim", "命令已复制到剪贴板。")

    def copy_log(self):
        text = self.log.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._append("line", "dim", "日志已复制到剪贴板。")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.live_active = False

    # ------------------------------------------------------------------
    # 保存位置：选择目录 / 设为默认 / 恢复默认
    # ------------------------------------------------------------------
    def _config_path(self):
        """配置文件与脚本（或 exe）放在同一目录。"""
        return os.path.join(self.builtin_dir, CONFIG_NAME)

    def _read_saved_default(self):
        """读取记住的默认保存位置；文件不存在或损坏时返回 None。

        用 utf-8-sig 读取：手工编辑过的配置文件常带 UTF-8 BOM（Windows 记事本、
        PowerShell 5.1 的 Set-Content -Encoding UTF8 都会写 BOM），
        而 json 模块不接受开头的 BOM，会导致设置被静默忽略。
        """
        try:
            with open(self._config_path(), "r", encoding="utf-8-sig") as fh:
                data = json.load(fh)
            path = normalize_dir(data.get("default_output_dir", ""))
            return path or None
        except (OSError, ValueError, AttributeError):
            return None

    def _load_config(self):
        """[新增] 读取整份配置（容错：文件缺失 / 损坏 / 非对象一律返回空 dict）。

        读取用 utf-8-sig，容忍老配置或被记事本加过 BOM 的文件。
        """
        try:
            with open(self._config_path(), "r", encoding="utf-8-sig") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save_config(self, updates=None, remove=()):
        """[新增] 合并写回配置：先读旧内容，只覆盖 updates 里的键、按 remove 删键，
        其余字段（包括本程序不认识的字段）原样保留，绝不整体覆盖。

        需求：新增配置项追加写入，不破坏旧版 ytdlp-gui.config.json 的读取。
        """
        data = self._load_config()
        for key in remove:
            data.pop(key, None)
        if updates:
            data.update(updates)
        try:
            with open(self._config_path(), "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            self.cfg = data
            return True
        except OSError as exc:
            self._append("line", "warn",
                         f"配置文件写入失败（设置仅在本次运行内有效）：{exc}")
            return False

    def _write_default(self, path):
        """把默认保存位置写入配置文件（合并写，保留高级选项等其它字段）。"""
        return self._save_config({CFG_DEFAULT_DIR: path})

    def _ensure_dir(self, path, quiet=False):
        """确保目录存在（不存在就创建）。quiet=True 时不弹错误框。"""
        path = normalize_dir(path)
        if not path:
            if not quiet:
                messagebox.showwarning("保存位置为空",
                                       "请先选择一个保存文件夹。", parent=self.root)
            return False
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except OSError as exc:
            if not quiet:
                messagebox.showerror(
                    "保存位置不可用",
                    f"无法创建或访问保存目录：\n{path}\n\n{exc}", parent=self.root)
            return False

    def _effective_default_dir(self):
        """当前生效的默认保存位置（用户设置过就用它，否则用内置默认）。"""
        return self.saved_default or self.builtin_dir

    def _update_dir_buttons(self):
        """按当前状态决定两个按钮是否可用，省去额外的状态说明文字。"""
        cur = os.path.normcase(normalize_dir(self.out_dir))
        eff = os.path.normcase(normalize_dir(self._effective_default_dir()))
        builtin = os.path.normcase(normalize_dir(self.builtin_dir))
        # 当前目录已经是默认值 → 没什么可"设为默认"的
        self.btn_setdef.set_state("normal" if cur != eff else "disabled")
        # 已经是内置默认、且没有配置文件 → 没什么可"恢复"的
        self.btn_reset.set_state(
            "normal" if (self.saved_default is not None or cur != builtin)
            else "disabled")

    def _on_dir_changed(self):
        self.out_dir = normalize_dir(self.dir_var.get())
        self.refresh_preview()
        self._update_dir_buttons()

    def choose_dir(self):
        """打开系统文件夹选择框，把结果作为本次下载的保存位置。"""
        initial = self.out_dir if os.path.isdir(self.out_dir) else self.builtin_dir
        path = filedialog.askdirectory(parent=self.root, title="选择保存位置",
                                       initialdir=initial, mustexist=False)
        if not path:
            return
        self.dir_var.set(normalize_dir(path))
        self._append("line", "dim", f"保存位置已改为：{self.out_dir}")

    def set_as_default(self):
        """把当前保存位置记住，下次启动自动使用。"""
        path = normalize_dir(self.out_dir)
        if not self._ensure_dir(path):
            return
        self.saved_default = path
        ok = self._write_default(path)
        self._update_dir_buttons()
        self._append("line", "ok",
                     f"✓ 已设为默认保存位置：{path}"
                     + ("" if ok else "（配置文件未能写入，重启后不生效）"))

    def reset_default(self):
        """清除记住的默认位置，回到内置默认（脚本 / exe 所在目录）。

        [新增] 只删除 default_output_dir 这一个键，保留高级选项等其它配置。
        """
        self.saved_default = None
        remaining = self._load_config()
        remaining.pop(CFG_DEFAULT_DIR, None)
        if remaining:
            self._save_config(remove=[CFG_DEFAULT_DIR])
        else:
            # 配置里没有别的字段了，直接删文件，保持目录干净
            try:
                os.remove(self._config_path())
            except OSError:
                pass
        self.dir_var.set(self.builtin_dir)
        self._append("line", "dim",
                     f"已恢复内置默认保存位置：{self.builtin_dir}")

    def open_out_dir(self):
        if not self._ensure_dir(self.out_dir, quiet=True):
            messagebox.showwarning("目录不存在",
                                   f"保存位置不存在或无法访问：\n{self.out_dir}",
                                   parent=self.root)
            return
        try:
            if os.name == "nt":
                os.startfile(self.out_dir)          # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.out_dir])
            else:
                subprocess.Popen(["xdg-open", self.out_dir])
        except Exception as exc:                     # noqa: BLE001
            messagebox.showerror("无法打开目录", str(exc), parent=self.root)

    def on_close(self):
        proc = self.proc
        if proc is not None and proc.poll() is None:
            if not messagebox.askyesno("正在下载",
                                       "当前还有下载任务在运行，确定要退出并终止它吗？",
                                       parent=self.root):
                return
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL,
                                   creationflags=CREATE_NO_WINDOW)
                else:
                    proc.terminate()
            except Exception:                        # noqa: BLE001
                pass
        # 取消定时刷新回调，避免销毁窗口后 Tk 抛出 invalid command name
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:                        # noqa: BLE001
                pass
            self._after_id = None
        # [新增] 高级选项写盘防抖定时器同样要取消，否则关窗后 Tk 会报错
        if self._save_after_id is not None:
            try:
                self.root.after_cancel(self._save_after_id)
            except Exception:                        # noqa: BLE001
                pass
            self._save_after_id = None
        self.root.destroy()


# ===========================================================================
# ⑤ 启动
# ===========================================================================
def pick_fonts(root):
    """挑选系统中存在的字体，保证在非中文 Windows 上也能正常显示。"""
    families = set(tkfont.families(root))
    ui = next((f for f in ("Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI",
                           "PingFang SC", "Noto Sans CJK SC") if f in families),
              "TkDefaultFont")
    mono = next((f for f in ("Consolas", "Cascadia Mono", "DejaVu Sans Mono",
                             "Courier New") if f in families), "TkFixedFont")
    FONTS.update({
        "h":    (ui, 15, "bold"),
        "card": (ui, 10, "bold"),
        "ui":   (ui, 10),
        "small": (ui, 9),
        "mono": (mono, 9),
    })


def enable_dpi_awareness():
    """开启 Windows DPI 感知（必须在创建 Tk 根窗口之前调用）。

    注意顺序：如果先 tk.Tk() 再设置 DPI 感知，Tk 会缓存按虚拟化坐标算出的
    屏幕尺寸（例如 1920x1080@125% 会被缓存成 1536x864），导致窗口尺寸算错、
    内容被挤扁。因此这里拆成两步，本函数在 tk.Tk() 之前执行。
    """
    if os.name != "nt":
        return
    try:
        from ctypes import windll
        try:
            windll.shcore.SetProcessDpiAwareness(1)       # System DPI aware
        except Exception:                                 # noqa: BLE001
            windll.user32.SetProcessDPIAware()
    except Exception:                                     # noqa: BLE001
        pass


def apply_window_geometry(root):
    """按系统缩放比设置 Tk 字体缩放 + 窗口尺寸并居中。"""
    scale = 1.0
    if os.name == "nt":
        try:
            from ctypes import windll
            dpi = windll.user32.GetDpiForSystem()
            scale = max(1.0, dpi / 96.0)
            root.tk.call("tk", "scaling", dpi / 72.0)
        except Exception:                                 # noqa: BLE001
            scale = 1.0
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    w = min(int(1000 * scale), int(screen_w * 0.95))
    # [主题] 按钮加高后占用更多纵向空间，窗口基准高度与上限都适当放宽，
    # 保证日志区仍然有足够的可视高度
    h = min(int(800 * scale), int(screen_h * 0.92))
    x = max(0, (screen_w - w) // 2)
    y = max(0, (screen_h - h) // 3)
    root.geometry(f"{w}x{h}+{x}+{y}")
    # minsize 不能超过实际窗口尺寸，否则小屏上窗口会溢出屏幕
    root.minsize(min(int(720 * scale), w), min(int(600 * scale), h))
    return scale


def main():
    enable_dpi_awareness()          # 必须先于 tk.Tk()，否则屏幕尺寸会被虚拟化
    resolve_binaries()              # [新增] 解析便携版优先 / PATH 回退的二进制
    root = tk.Tk()
    root.withdraw()                 # 先隐藏，等尺寸算好再显示，避免闪烁
    pick_fonts(root)
    apply_window_geometry(root)
    gui = YtDlpGUI(root)
    # 可选：支持把链接作为启动参数传入（也可以直接把链接拖到 exe 图标上）
    if len(sys.argv) > 1 and sys.argv[1].strip():
        gui.url_var.set(sys.argv[1].strip())
    root.deiconify()
    gui.url_entry.focus_set()       # 打开即可 Ctrl+V 粘贴
    root.mainloop()


if __name__ == "__main__":
    main()
