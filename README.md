# FormatKae

基于 FFmpeg 的 Windows x64 中文音视频格式转换器。所有媒体处理在本机离线进行。

## 直接使用

打开 `dist\FormatKae\FormatKae.exe`。发布目录含 Python、Qt、FFmpeg 和 ffprobe，无需单独安装这些环境。
复制软件时请复制整个 `FormatKae` 文件夹，不能仅复制 EXE。压缩包版本解压后双击同名 EXE 即可。
适用于 Windows 10/11 x64；本次构建在当前 Windows x64 主机验证。

1. 添加文件、文件夹（递归搜索常见媒体）或将文件拖入窗口。
2. 选择预设或自行调整输出参数。
3. 指定输出目录；留空表示分别保存到各个源文件旁。
4. 开始转换。完成后点击「打开输出目录」。

## 功能

- 输出预设：MP4、MKV、MOV、WebM、AVI、M4V、TS、FLV、MPG、WMV、GIF、MP3、WAV、FLAC、AAC、M4A、OGG、Opus、AIFF、WMA、AC3，另提供自定义封装扩展名。
- 输入范围由 FFmpeg 引擎决定；「所有文件」可直接选择其他输入扩展名。
- 支持 H.264 / H.265 / AV1 / VP9、常用音频编码、直接复制轨道，以及 NVENC / QSV / AMF 编码器选项。
- 可调质量、码率、编码速度、宽高、帧率、音频码率、采样率、声道、音量、时间裁剪、线程和元数据。
- 自定义 FFmpeg 输出参数、命令预览、JSON 预设导入导出、设置记忆。
- 顺序批量处理、实时进度和速度、取消任务、错误日志和重试。
- 中文路径支持、同名输出自动编号、临时文件提交、取消和失败清理。

## 参数说明与限制

CRF / CQ 越低通常质量越高、体积越大。视频码率填写后优先于质量值。
质量设置用于 x264、x265、SVT-AV1、VP8/9 和 NVENC；编码速度用于 x264、x265 和 SVT-AV1。
其他编码器的专有选项可在高级输出参数填写。

一个批次共用一组参数。已完成任务不会重复转换；右键可重新加入待转换。
默认处理首个视频轨道（排除封面）与首个音频轨道，不保留字幕、附件及其他轨道。
不同容器支持不同编码器，手动选择不兼容的组合会失败，并在日志显示 FFmpeg 原因。
硬件编码依赖支持的显卡与驱动，本机未逐一验证硬件编码器。
音频文件导出到视频容器只保留音频，不会自动生成画面。

`copy` 表示不重新编码，不支持同时更改对应轨道的分辨率、帧率、采样率或音量。
裁剪的开始与结束时间均指源文件中的位置。复制模式的定位受关键帧限制；精确剪辑请重新编码。
尺寸两项自动表示保留原始；仅填写一项时按比例缩放。部分编码器要求宽高为偶数。
GIF 默认 640 像素宽、15 FPS，使用调色板优化，不包含音频。
FLAC / PCM / ALAC 不能恢复输入音频已损失的细节。

额外输出参数示例：`-vf "hflip"`、`-metadata title="我的视频"`、`-c:a pcm_s24le`。
同名选项以最后出现的为准；自定义 `-vf` / `-af` 替换界面生成的对应滤镜。
参数字符串值含空格时使用引号。不要填写额外输入、输出路径、覆盖选项或进度选项。
自定义封装填写扩展名后，需要自行设置兼容编码器。

## 文件和引擎

输出为 `源文件名_converted.扩展名`，同名自动增加数字。不会覆盖原文件或现有输出。
先写同一输出目录下的隐藏式 `.partial` 临时文件，成功后重命名；失败和取消自动清理。
意外断电时遗留的 `.partial` 文件可手动删除。
队列仅保存在当前会话，参数和目录保存在 `%APPDATA%\FormatKae\settings.json`。
异常信息写入 `%APPDATA%\FormatKae\error.log`。

自动检测顺序：软件旁 `ffmpeg\bin`、软件旁 `ffmpeg`、本机提供的 FFmpeg 路径、系统 PATH。
可在「引擎设置」指定其他包含 `ffmpeg.exe` 和 `ffprobe.exe` 的目录。指定目录无效时会提示重新配置。

## 从源码运行与构建

需要 Windows x64、Python 3.12 x64。依赖固定在 `requirements.txt`。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py

# 构建可直接运行的目录和 ZIP；也可只运行 build.ps1 不生成 ZIP
.\build.ps1 -CreateZip
# 指定其他 FFmpeg 引擎
.\build.ps1 -FFmpegDirectory 'D:\Tools\ffmpeg\bin' -CreateZip
```

构建输出在 `dist\FormatKae`，ZIP 在 `release`。`SHA256SUMS.txt` 提供主程序和引擎校验值。
第三方库、引擎许可证和原始发行信息在 `licenses`，应用源码副本在 `source`。

## 验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\integration_test.py
.\.venv\Scripts\python.exe scripts\gui_test.py
.\.venv\Scripts\python.exe scripts\packaged_test.py
.\dist\FormatKae\FormatKae.exe --smoke-test test-artifacts\packaged-smoke.json
```

实转测试覆盖全部 21 种预设格式与 NUT 自定义封装，以及中文路径、裁剪、缩放、采样率和声道设置。
GUI 测试覆盖队列转换、取消、失败继续处理、原文件保留和临时文件清理。
具体报告位于 `test-artifacts`。不保证任意损坏文件、加密媒体或所有编码器组合均能转换。

参考：[FFmpeg 官方参数文档](https://ffmpeg.org/ffmpeg.html)、[Qt for Python](https://doc.qt.io/qtforpython-6/)、[PyInstaller](https://pyinstaller.org/en/stable/usage.html)。
