#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全平台视频下载器 · yt-dlp GUI
=============================================================================

一个基于 tkinter / ttk 的深色主题图形外壳：通过系统 PATH 调用外部已安装的
yt-dlp 与 ffmpeg 完成下载。凡是 yt-dlp 支持的站点（B 站、抖音、小红书、
YouTube、Twitter/X、Vimeo、Twitch、微博……）本工具都可以直接使用。

设计定位
--------
本程序是「命令行拼装 + 子进程托管 + 日志回显」的薄外壳，不内嵌下载引擎：

    * 下载引擎：系统 PATH 中的 yt-dlp
    * 音视频合并：系统 PATH 中的 ffmpeg（yt-dlp 自动调用）

界面与交互
----------
    * 深色主题：炭黑/深灰底 + 浅灰白文字 + 低饱和蓝强调色
    * 小圆角（3px，偏向直角）、扁平纯色填充、1px 细边框
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

关键实现
--------
    * 默认基础参数：-f "bv*+ba" --add-header Referer:https://www.bilibili.com
      （「清晰度」选最高画质时输出与原始需求完全一致）
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
"""

import json
import locale
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

# ===========================================================================
# ① 常量与全局配置
# ===========================================================================

APP_TITLE = "全平台视频下载器 · yt-dlp GUI"
APP_VERSION = "1.2.0"

# 外部依赖的可执行文件名（均由用户在系统层面安装并配置进 PATH）
YTDLP_BIN = "yt-dlp"
FFMPEG_BIN = "ffmpeg"

# ---- 深色主题配色：炭黑 / 深灰底 + 浅灰白文字 + 低饱和蓝强调 ----
C = {
    "BG":          "#1f1f1f",   # 窗口底色（炭黑）
    "SURFACE":     "#2a2a2a",   # 分组卡片底色（深灰）
    "INPUT_BG":    "#1b1b1b",   # 输入框 / 终端底色
    "BORDER":      "#3a3a3a",   # 1px 细边框
    "TEXT":        "#e6e6e6",   # 主文字（浅灰白）
    "TEXT_DIM":    "#9a9a9a",   # 次要文字
    "TEXT_MUTE":   "#7d7d7d",   # 更弱的提示文字
    "ACCENT":      "#3f6f9f",   # 强调色（低饱和蓝）
    "ACCENT_HI":   "#4c83b8",   # 悬浮高亮
    "ACCENT_LO":   "#33587d",   # 按下
    "GHOST_BG":    "#333333",   # 次级按钮填充
    "GHOST_HI":    "#3f3f3f",
    "DISABLED_BG": "#2e3236",
    "DISABLED_FG": "#6b7075",
    "OK":          "#7fae7f",
    "ERR":         "#d07b7b",
    "WARN":        "#d0b070",
    "CMD_FG":      "#cfe3f5",
    "LOG_FG":      "#d6d6d6",
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

        f = tkfont.Font(font=self._font)
        w = max(min_width, f.measure(text) + 2 * padx)
        h = height or (f.metrics("linespace") + 12)

        super().__init__(master, width=w, height=h, bg=bg, bd=0,
                         highlightthickness=0, relief="flat", takefocus=0,
                         cursor="hand2" if state == "normal" else "arrow")
        # 注意：不要用 self._w / self._h，那是 tkinter 内部保存控件路径名的属性
        self._bw, self._bh = w, h
        self._shape = self._rounded(0, 0, w, h, 3, fill=self._fill())
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
        return self.create_polygon(pts, smooth=True, splinesteps=8,
                                   outline="", **kw)

    def _palette(self):
        if self._kind == "primary":
            return {"normal": C["ACCENT"], "hover": C["ACCENT_HI"],
                    "active": C["ACCENT_LO"], "fg": "#ffffff"}
        return {"normal": C["GHOST_BG"], "hover": C["GHOST_HI"],
                "active": "#474747", "fg": C["TEXT"]}

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
        return self._palette()["fg"]

    def _redraw(self):
        self.itemconfigure(self._shape, fill=self._fill())
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
    """深色扁平复选框：纯色方框 + 1px 细边框，选中时填充强调蓝并画白色对勾。

    原生 tk.Checkbutton 在 Windows 下的勾选框由系统绘制，深色主题下容易出现
    「框是黑的、对勾也是黑的」问题，所以这里和 FlatButton 一样自绘，保证风格统一。
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
        self._box = self.create_rectangle(1, top + 1, box, top + box,
                                          outline=C["BORDER"],
                                          fill=C["INPUT_BG"], width=1)
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

        self._setup_style()
        self._build_ui()
        self._bind_events()
        self.refresh_preview()
        self.check_environment()
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

        # 细滚动条
        style.configure("Dark.Vertical.TScrollbar", background="#3a3a3a",
                        troughcolor=C["BG"], bordercolor=C["BG"],
                        arrowcolor=C["TEXT_DIM"], relief="flat", arrowsize=12)
        style.map("Dark.Vertical.TScrollbar",
                  background=[("active", "#4a4a4a")])

        # 细进度条
        style.configure("Flat.Horizontal.TProgressbar", troughcolor="#2b2b2b",
                        background=C["ACCENT"], bordercolor="#2b2b2b",
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
        self.url_entry = tk.Entry(row, textvariable=self.url_var,
                                  bg=C["INPUT_BG"], fg=C["TEXT"],
                                  insertbackground=C["TEXT"], relief="flat",
                                  bd=0, font=FONTS["ui"],
                                  highlightthickness=1,
                                  highlightbackground=C["BORDER"],
                                  highlightcolor=C["ACCENT"])
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=5)
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
        self.quality_box = ttk.Combobox(row, textvariable=self.quality_var,
                                        values=[name for name, _ in QUALITY_CHOICES],
                                        state="readonly", width=18)
        self.quality_box.pack(side="left")
        tk.Label(row, text="Cookie", width=8, anchor="w", bg=C["SURFACE"],
                 fg=C["TEXT"], font=FONTS["ui"]).pack(side="left", padx=(26, 0))
        self.cookie_box = ttk.Combobox(row, textvariable=self.cookie_var,
                                       values=COOKIE_CHOICES, state="readonly",
                                       width=16)
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

        # ---- 分组 3：命令预览（只读） ----
        body = self._card(main, "命令预览（只读 · 实时刷新）",
                          action=lambda head: self._header_action(
                              head, "复制命令", self.copy_command))
        self.cmd_text = tk.Text(body, height=3, wrap="word",
                                bg=C["INPUT_BG"], fg=C["CMD_FG"],
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
        self.btn_stop = FlatButton(left, "停止", self.stop_download,
                                   kind="ghost", min_width=70, state="disabled")
        self.btn_stop.pack(side="left", padx=(8, 0))
        self.btn_open = FlatButton(left, "打开输出目录", self.open_out_dir,
                                   kind="ghost", min_width=110)
        self.btn_open.pack(side="left", padx=(8, 0))

        right = tk.Frame(bar, bg=C["BG"])
        right.pack(side="right")
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
        self.dir_entry = tk.Entry(dirrow, textvariable=self.dir_var,
                                  bg=C["INPUT_BG"], fg=C["TEXT"],
                                  insertbackground=C["TEXT"], relief="flat",
                                  bd=0, font=FONTS["small"],
                                  highlightthickness=1,
                                  highlightbackground=C["BORDER"],
                                  highlightcolor=C["ACCENT"])
        self.dir_entry.pack(side="left", fill="x", expand=True, ipady=3)
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
        self.log = tk.Text(wrap, bg=C["INPUT_BG"], fg=C["LOG_FG"],
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
        """卡片宽度变化时同步两个说明标签的换行宽度。"""
        wrap = max(320, width - 20)
        self.note_label.configure(wraplength=wrap)
        self.pl_hint.configure(wraplength=wrap)

    def _card(self, parent, title, action=None, expand=False):
        """创建一个 Win10 设置风格的分组卡片，返回可放置内容的内层 Frame。"""
        card = tk.Frame(parent, bg=C["SURFACE"], bd=0,
                        highlightthickness=1, highlightbackground=C["BORDER"])
        card.pack(fill="both" if expand else "x", expand=expand,
                  pady=(0, 9))
        head = tk.Frame(card, bg=C["SURFACE"])
        head.pack(fill="x", padx=14, pady=(9, 0))
        tk.Label(head, text=title, bg=C["SURFACE"], fg=C["TEXT"],
                 font=FONTS["card"], anchor="w").pack(side="left")
        if action:
            action(head)
        body = tk.Frame(card, bg=C["SURFACE"])
        body.pack(fill="both" if expand else "x", expand=expand,
                  padx=14, pady=(7, 10))
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
        ytdlp_path = shutil.which(YTDLP_BIN)
        ffmpeg_path = shutil.which(FFMPEG_BIN)
        parts, bad = [], []
        if ytdlp_path:
            parts.append(f"yt-dlp ✓  {ytdlp_path}")
        else:
            parts.append("yt-dlp ✗  未在 PATH 中找到")
            bad.append("yt-dlp")
        if ffmpeg_path:
            parts.append(f"ffmpeg ✓  {ffmpeg_path}")
        else:
            parts.append("ffmpeg ✗  未在 PATH 中找到")
            bad.append("ffmpeg")
        self.env_label.configure(text="依赖检查：" + "    ".join(parts),
                                 fg=C["ERR"] if bad else C["OK"])
        self._append("line", "dim",
                     f"依赖检查：yt-dlp={ytdlp_path or '未找到'} | "
                     f"ffmpeg={ffmpeg_path or '未找到'}")
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
            self._append("line", "err",
                         "缺少依赖：" + "、".join(bad) +
                         "。请先安装并确保已加入系统 PATH，再重新打开本程序。")

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
        if shutil.which(YTDLP_BIN) is None:
            messagebox.showerror(
                "未找到 yt-dlp",
                "系统 PATH 中找不到 yt-dlp。\n\n"
                "请先安装 yt-dlp 并确保可以从命令行直接运行 yt-dlp --version，"
                "然后重新打开本程序。", parent=self.root)
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
        if busy:
            self._set_status("下载中…", C["ACCENT_HI"])

    def _set_status(self, text, color):
        self.status_var.set(text)
        self.status_lbl.configure(fg=color)

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

    def _write_default(self, path):
        """把默认保存位置写入配置文件，返回是否写成功。"""
        try:
            with open(self._config_path(), "w", encoding="utf-8") as fh:
                json.dump({"default_output_dir": path}, fh,
                          ensure_ascii=False, indent=2)
            return True
        except OSError as exc:
            self._append("line", "warn",
                         f"配置文件写入失败（设置仅在本次运行内有效）：{exc}")
            return False

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
        """清除记住的默认位置，回到内置默认（脚本 / exe 所在目录）。"""
        self.saved_default = None
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
    h = min(int(770 * scale), int(screen_h * 0.90))
    x = max(0, (screen_w - w) // 2)
    y = max(0, (screen_h - h) // 3)
    root.geometry(f"{w}x{h}+{x}+{y}")
    # minsize 不能超过实际窗口尺寸，否则小屏上窗口会溢出屏幕
    root.minsize(min(int(720 * scale), w), min(int(600 * scale), h))
    return scale


def main():
    enable_dpi_awareness()          # 必须先于 tk.Tk()，否则屏幕尺寸会被虚拟化
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
