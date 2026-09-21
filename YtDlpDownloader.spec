# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec打包脚本由 DeepSeek AI 生成，原样复用未修改。
已知局限：未做yt‑dlp模块适配，如果选择把yt‑dlp打包进exe内部，存在提取器缺失风险。
本项目默认架构：GUI调用系统外部 yt‑dlp.exe / ffmpeg.exe，不将yt‑dlp打进exe。
打包产物请充分测试，使用者自行承担使用风险。
"""
from PyInstaller.utils.hooks import collect_data_files

datas = []
datas += collect_data_files('tkinter')


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['tkinter.ttk', 'tkinter.font', 'tkinter.messagebox'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='YtDlpDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
