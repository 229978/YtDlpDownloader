# YtDlpDownloader
tkinter 编写的 yt‑dlp 图形界面前端。

> 本程序仅仅是GUI外壳，**下载解析能力完全依赖外部 yt‑dlp 与 ffmpeg**，程序不会内置这两个程序。

## ⚠️重要提示与免责
1. 本项目仅供个人学习研究，请遵守各网站用户协议以及当地法律法规，禁止用于侵权下载。
2. 抖音有严格反爬，公开视频也经常需要浏览器Cookie；Windows环境下`--cookies‑from‑browser edge`容易因为浏览器锁文件报错，优先使用导出`cookies.txt`导入。
3. 仓库内提供的`YtDlpDownloader.spec`打包脚本由 DeepSeek AI 生成，未做修改。
   - ✅本项目默认用法：GUI调用系统外部yt‑dlp/ffmpeg，不会触发spec缺陷；
   - ⚠️不要尝试把yt‑dlp打包进exe内部，会出现提取器缺失，如需内置请自行查阅yt‑dlp官方hook文档。
4. 软件按现状提供，使用者自行测试，自行承担使用风险。

## 依赖安装
需要提前在系统安装两个程序，推荐使用winget：
```powershell
winget install yt‑dlp
winget install ffmpeg
也可以手动下载 exe，在软件界面手动指定程序路径。

## 直接运行源码
pip install tk
python app.py
打包 exe
pyinstaller --clean YtDlpDownloader.spec
输出文件在 `dist` 文件夹。

## 已知问题

1. 部分网站下载失败，优先更新系统 yt‑dlp：`yt‑dlp -U`
2. 抖音无 Cookie 直接报错，需要导入 cookies.txt
3. 打包脚本不支持内置 yt‑dlp 进 exe