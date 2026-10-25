from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QScrollArea, QSpinBox, QSplitter, QStackedWidget,
    QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .core import (
    APP_NAME, AUDIO_CODECS, FORMATS, VIDEO_CODECS, VERSION, Options, app_root,
    build_command, display_command, find_tools, format_size, format_time,
    load_settings, output_path, save_settings,
)
from .workers import ConversionWorker, Job, ProbeWorker


def label(text, name="", wrap=False):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def button(text, callback, name=""):
    widget = QPushButton(text)
    if name:
        widget.setObjectName(name)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.clicked.connect(callback)
    return widget


def combo(values, editable=False):
    widget = QComboBox()
    widget.addItems(values)
    widget.setEditable(editable)
    widget.setMinimumWidth(90)
    return widget


def app_icon():
    resource_root = Path(getattr(sys, "_MEIPASS", str(app_root())))
    return QIcon(str(resource_root / "assets" / "app.ico"))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} · 音视频格式转换器")
        icon = app_icon()
        self.setWindowIcon(icon)
        QApplication.instance().setWindowIcon(icon)
        self.resize(1380, 900)
        self.setMinimumSize(1040, 720)
        self.setAcceptDrops(True)
        self.settings = load_settings()
        self.jobs: list[Job] = []
        self.prober = None
        self.converter = None
        self._batch_ids = []
        self._probe_errors = []
        self._busy = False
        self.ffmpeg = None
        self.ffprobe = None
        self.build_ui()
        self.apply_options(Options())
        try:
            saved = Options.from_dict(self.settings.get("options", {}))
            saved.validate()
            self.apply_options(saved)
        except (ValueError, TypeError, KeyError):
            pass
        self.detect_engine()
        self.refresh_table()

    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(205)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(20, 29, 20, 22)
        logo = QLabel()
        logo.setPixmap(app_icon().pixmap(45, 45))
        side.addWidget(logo)
        side.addSpacing(9)
        side.addWidget(label("FormatKae", "brand"))
        side.addWidget(label("音视频格式转换器", "muted"))
        side.addSpacing(32)
        side.addWidget(label("快速预设  /  PRESETS", "eyebrow"))
        self.preset_buttons = []
        for title, key in [("通用视频\nMP4 · H.264", "balanced"), ("更小体积\nMP4 · HEVC", "small"), ("网页视频\nWebM · VP9", "web"), ("提取音频\nMP3 · 192 kbps", "mp3"), ("无损音频\nFLAC · 原始采样率", "flac"), ("动态图片\nGIF · 15 FPS", "gif")]:
            item = button(title, lambda checked=False, k=key: self.quick_preset(k), "preset")
            side.addWidget(item)
            self.preset_buttons.append(item)
        side.addStretch()
        self.engine_status = label("● 正在检测引擎", "accent", True)
        side.addWidget(self.engine_status)
        side.addWidget(button("引擎设置", self.engine_dialog))
        side.addWidget(button("使用说明 / 关于", self.help_dialog))
        side.addWidget(label(f"v{VERSION}  ·  Windows x64", "muted"))
        outer.addWidget(sidebar)

        workspace = QWidget()
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.addWidget(label("把格式，交给你。", "title"))
        titles.addWidget(label("添加媒体 → 调整参数 → 开始转换", "muted"))
        header.addLayout(titles)
        header.addStretch()
        self.add_button = button("＋ 添加文件", self.choose_files, "primary")
        self.add_folder_button = button("添加文件夹", self.choose_folder)
        header.addWidget(self.add_folder_button)
        header.addWidget(self.add_button)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        queue_head = QHBoxLayout()
        self.queue_count = label("转换队列  ·  0 个文件", "heading")
        queue_head.addWidget(self.queue_count)
        queue_head.addStretch()
        self.remove_button = button("移除选中", self.remove_selected)
        self.clear_button = button("清空", self.clear_jobs)
        queue_head.addWidget(self.remove_button)
        queue_head.addWidget(self.clear_button)
        left_layout.addLayout(queue_head)
        self.tabs = QTabWidget()
        self.queue_page = QStackedWidget()
        empty = QFrame()
        empty.setObjectName("drop")
        empty_layout = QVBoxLayout(empty)
        empty_layout.addStretch()
        drop_icon = label("⇄", "accent")
        drop_icon.setStyleSheet("font-size: 68px; font-weight: 600;")
        drop_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(drop_icon)
        for text, name in [("拖放音频或视频到这里", "heading"), ("或点击右上角「添加文件」", "muted"), ("支持批量添加 · 支持中文路径 · 本地离线转换", "muted")]:
            item = label(text, name, True)
            item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(item)
        empty_layout.addStretch()
        self.queue_page.addWidget(empty)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["文件 / 媒体信息", "时长", "大小", "状态"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(64)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 3):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.table.cellDoubleClicked.connect(self.media_details)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.queue_menu)
        self.queue_page.addWidget(self.table)
        self.tabs.addTab(self.queue_page, "任务队列")
        self.log_edit = QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumBlockCount(6000)
        self.log_edit.setFont(QFont("Consolas", 10))
        self.tabs.addTab(self.log_edit, "转换日志")
        left_layout.addWidget(self.tabs, 1)

        destination = QFrame()
        destination.setObjectName("card")
        dest_layout = QVBoxLayout(destination)
        dest_layout.setContentsMargins(16, 13, 16, 13)
        dest_layout.addWidget(label("输出位置", "heading"))
        dest_row = QHBoxLayout()
        self.output_edit = QLineEdit(str(self.settings.get("output", "")))
        self.output_edit.setPlaceholderText("留空：保存到每个源文件所在目录")
        self.output_edit.setToolTip("输出自动添加 _converted 后缀；重名时自动编号，不会覆盖原文件。")
        self.browse_output_button = button("浏览…", self.choose_output)
        dest_row.addWidget(self.output_edit, 1)
        dest_row.addWidget(self.browse_output_button)
        dest_layout.addLayout(dest_row)
        dest_layout.addWidget(label("自动避让同名文件，原始素材始终保留。", "muted", True))
        left_layout.addWidget(destination)
        splitter.addWidget(left)

        self.params_container = QFrame()
        self.params_container.setObjectName("card")
        self.params_container.setMinimumWidth(335)
        params_outer = QVBoxLayout(self.params_container)
        params_outer.setContentsMargins(14, 14, 14, 12)
        settings_header = QHBoxLayout()
        settings_header.addWidget(label("转换参数", "heading"))
        settings_header.addStretch()
        settings_header.addWidget(button("预设…", self.presets_menu))
        params_outer.addLayout(settings_header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        params = QWidget()
        params_layout = QVBoxLayout(params)
        params_layout.setContentsMargins(0, 0, 8, 4)
        self.format_combo = QComboBox()
        for fmt in FORMATS:
            self.format_combo.addItem(fmt.label, fmt.ext)
        params_layout.addWidget(label("目标格式", "muted"))
        params_layout.addWidget(self.format_combo)
        self.custom_ext = QLineEdit("nut")
        self.custom_ext.setPlaceholderText("自定义扩展名，例如 mxf / nut")
        self.custom_ext.setToolTip("请自行选择与封装兼容的编码器；具体支持范围取决于 FFmpeg。")
        params_layout.addWidget(self.custom_ext)

        self.video_group = QGroupBox("视频设置")
        form = QFormLayout(self.video_group)
        form.setSpacing(10)
        self.video_codec = combo(VIDEO_CODECS, True)
        self.video_codec.setToolTip("copy = 不重新编码；硬件编码需要相应显卡与驱动。可输入其他 FFmpeg 编码器名称。")
        form.addRow("编码器", self.video_codec)
        self.quality = QSpinBox()
        self.quality.setRange(0, 63)
        self.quality.setToolTip("CRF / CQ 越低画质越高、体积越大；H.264 / H.265 上限 51。仅适用于支持的编码器，码率优先。")
        form.addRow("质量 CRF / CQ", self.quality)
        self.speed = combo(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"])
        self.speed.setToolTip("用于 x264 / x265 / SVT-AV1。越慢通常压缩率越高。")
        form.addRow("编码速度", self.speed)
        self.video_bitrate = QLineEdit()
        self.video_bitrate.setPlaceholderText("自动质量；或输入 5M / 2500k")
        form.addRow("视频码率", self.video_bitrate)
        resolution = QWidget()
        res_layout = QHBoxLayout(resolution)
        res_layout.setContentsMargins(0, 0, 0, 0)
        self.width = QSpinBox()
        self.height = QSpinBox()
        for spin in (self.width, self.height):
            spin.setRange(0, 16384)
            spin.setSpecialValueText("自动")
            spin.setToolTip("两项为自动时保留原分辨率；只填一项时按比例缩放。")
        res_layout.addWidget(self.width)
        res_layout.addWidget(label("×"))
        res_layout.addWidget(self.height)
        form.addRow("宽 × 高", resolution)
        self.fps = combo(["原始帧率", "15", "24", "25", "30", "50", "60", "120", "30000/1001"], True)
        form.addRow("帧率 FPS", self.fps)
        params_layout.addWidget(self.video_group)

        self.audio_group = QGroupBox("音频设置")
        form = QFormLayout(self.audio_group)
        form.setSpacing(10)
        self.audio_codec = combo(AUDIO_CODECS, True)
        form.addRow("编码器", self.audio_codec)
        self.audio_bitrate = combo(["64k", "96k", "128k", "160k", "192k", "256k", "320k", "自动"], True)
        self.audio_bitrate.setToolTip("无损编码器忽略码率；可输入自定义值。")
        form.addRow("音频码率", self.audio_bitrate)
        self.sample_rate = combo(["保留原始", "8000", "16000", "22050", "24000", "44100", "48000", "96000", "192000"], True)
        form.addRow("采样率 Hz", self.sample_rate)
        self.channels = combo(["保留原始", "1", "2", "6", "8"], True)
        form.addRow("声道数", self.channels)
        self.volume = QDoubleSpinBox()
        self.volume.setRange(0, 400)
        self.volume.setSuffix(" %")
        self.volume.setDecimals(0)
        self.volume.setSingleStep(10)
        form.addRow("音量", self.volume)
        params_layout.addWidget(self.audio_group)

        advanced = QGroupBox("裁剪与高级参数")
        form = QFormLayout(advanced)
        form.setSpacing(10)
        self.start_edit = QLineEdit()
        self.end_edit = QLineEdit()
        self.start_edit.setPlaceholderText("00:00:00 或秒数")
        self.end_edit.setPlaceholderText("留空：直到结束")
        self.start_edit.setToolTip("指定源文件中的开始位置。copy 模式按关键帧定位，可能不精确。")
        self.end_edit.setToolTip("指定源文件中的结束位置，而非片段时长。")
        form.addRow("开始时间", self.start_edit)
        form.addRow("结束时间", self.end_edit)
        self.threads = QSpinBox()
        self.threads.setRange(0, 128)
        self.threads.setSpecialValueText("自动")
        form.addRow("编码线程", self.threads)
        self.metadata = QCheckBox("保留媒体元数据")
        form.addRow(self.metadata)
        self.extra = QPlainTextEdit()
        self.extra.setFixedHeight(88)
        self.extra.setPlaceholderText('例如：-vf "hflip"\n或 -metadata title="我的视频"')
        self.extra.setToolTip("追加输出选项，优先于上方设置。每个参数后跟一个值；不支持额外输入、输出路径和覆盖控制。")
        form.addRow("额外输出参数", self.extra)
        self.preview_button = button("查看 FFmpeg 命令", self.command_dialog)
        form.addRow(self.preview_button)
        params_layout.addWidget(advanced)
        params_layout.addWidget(label("默认处理首个视频与音频轨道，不保留字幕或附件。硬件编码可用性取决于设备与驱动。", "muted", True))
        params_layout.addStretch()
        scroll.setWidget(params)
        params_outer.addWidget(scroll)
        splitter.addWidget(self.params_container)
        splitter.setSizes([740, 365])
        splitter.setStretchFactor(0, 1)
        layout.addWidget(splitter, 1)

        footer = QFrame()
        footer.setObjectName("footer")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(17, 14, 17, 14)
        status_layout = QVBoxLayout()
        self.status_label = label("准备就绪", "heading")
        self.detail_label = label("先添加文件，再选择适合你的转换参数。", "muted", True)
        self.overall_progress = QProgressBar()
        self.overall_progress.setValue(0)
        self.overall_progress.setTextVisible(False)
        self.overall_progress.setFixedHeight(6)
        self.overall_progress.setStyleSheet("QProgressBar { min-height: 4px; border: none; }")
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.detail_label)
        status_layout.addWidget(self.overall_progress)
        footer_layout.addLayout(status_layout, 1)
        self.open_button = button("打开输出目录", self.open_output)
        self.cancel_button = button("取消转换", self.cancel_conversion, "danger")
        self.cancel_button.setEnabled(False)
        self.start_button = button("▶ 开始转换", self.start_conversion, "primary")
        self.start_button.setMinimumSize(145, 46)
        footer_layout.addWidget(self.open_button)
        footer_layout.addWidget(self.cancel_button)
        footer_layout.addWidget(self.start_button)
        layout.addWidget(footer)
        outer.addWidget(workspace, 1)
        self.format_combo.currentIndexChanged.connect(self.format_changed)
        self.video_codec.currentTextChanged.connect(self.codec_changed)
        self.audio_codec.currentTextChanged.connect(self.codec_changed)
        action = QAction("添加文件", self)
        action.setShortcut("Ctrl+O")
        action.triggered.connect(self.choose_files)
        self.addAction(action)

    def current_options(self):
        def text(widget, placeholder):
            value = widget.currentText().strip()
            return "" if value == placeholder else value
        return Options(
            format=self.format_combo.currentData(), video_codec=self.video_codec.currentText().strip(),
            audio_codec=self.audio_codec.currentText().strip(), quality=self.quality.value(), preset=self.speed.currentText(),
            video_bitrate=self.video_bitrate.text().strip(), width=self.width.value(), height=self.height.value(),
            fps=text(self.fps, "原始帧率"), audio_bitrate=text(self.audio_bitrate, "自动"), sample_rate=text(self.sample_rate, "保留原始"),
            channels=text(self.channels, "保留原始"), volume=self.volume.value(), start=self.start_edit.text().strip(),
            end=self.end_edit.text().strip(), threads=self.threads.value(), metadata=self.metadata.isChecked(),
            extra=self.extra.toPlainText().strip(), custom_ext=self.custom_ext.text().strip(),
        )

    def apply_options(self, opt):
        index = self.format_combo.findData(opt.format)
        self.format_combo.setCurrentIndex(max(0, index))
        for widget, value in [(self.video_codec, opt.video_codec), (self.audio_codec, opt.audio_codec), (self.speed, opt.preset),
                              (self.fps, opt.fps or "原始帧率"), (self.audio_bitrate, opt.audio_bitrate or "自动"),
                              (self.sample_rate, opt.sample_rate or "保留原始"), (self.channels, opt.channels or "保留原始")]:
            widget.setCurrentText(value)
        for widget, value in [(self.quality, opt.quality), (self.width, opt.width), (self.height, opt.height), (self.volume, opt.volume), (self.threads, opt.threads)]:
            widget.setValue(value)
        for widget, value in [(self.video_bitrate, opt.video_bitrate), (self.start_edit, opt.start), (self.end_edit, opt.end), (self.custom_ext, opt.custom_ext)]:
            widget.setText(value)
        self.metadata.setChecked(opt.metadata)
        self.extra.setPlainText(opt.extra)
        self.update_parameter_availability()

    def format_changed(self):
        fmt = FORMATS[self.format_combo.currentIndex()]
        self.video_codec.setCurrentText(fmt.video or "libx264")
        self.audio_codec.setCurrentText(fmt.audio or "aac")
        # Container-specific defaults avoid carrying incompatible settings across profiles.
        self.sample_rate.setCurrentText("48000" if fmt.ext == "opus" else "保留原始")
        self.channels.setCurrentText("保留原始")
        self.video_bitrate.clear()
        self.fps.setCurrentText("15" if fmt.kind == "gif" else "原始帧率")
        self.width.setValue(640 if fmt.kind == "gif" else 0)
        self.height.setValue(0)
        self.update_parameter_availability()

    def codec_changed(self):
        if hasattr(self, "width") and self.video_codec.currentText() == "copy":
            self.width.setValue(0)
            self.height.setValue(0)
            self.fps.setCurrentText("原始帧率")
            self.video_bitrate.clear()
        if hasattr(self, "volume") and self.audio_codec.currentText() == "copy":
            self.sample_rate.setCurrentText("保留原始")
            self.channels.setCurrentText("保留原始")
            self.volume.setValue(100)
        self.update_parameter_availability()

    def update_parameter_availability(self):
        if not hasattr(self, "audio_group"):
            return
        fmt = FORMATS[self.format_combo.currentIndex()]
        self.custom_ext.setVisible(fmt.kind == "custom")
        self.video_group.setEnabled(fmt.kind != "audio")
        self.audio_group.setEnabled(fmt.kind != "gif")
        vcodec = self.video_codec.currentText()
        acodec = self.audio_codec.currentText()
        self.video_codec.setEnabled(fmt.kind != "gif")
        self.quality.setEnabled(fmt.kind != "gif" and (vcodec in {"libx264", "libx265", "libsvtav1", "libvpx-vp9", "libvpx"} or vcodec.endswith("_nvenc")))
        self.speed.setEnabled(fmt.kind != "gif" and vcodec in {"libx264", "libx265", "libsvtav1"})
        self.video_bitrate.setEnabled(fmt.kind != "gif" and vcodec != "copy")
        for item in (self.width, self.height, self.fps):
            item.setEnabled(vcodec != "copy" or fmt.kind == "gif")
        for item in (self.sample_rate, self.channels, self.volume):
            item.setEnabled(acodec not in {"copy", "禁用音频"})
        self.audio_bitrate.setEnabled(acodec not in {"copy", "禁用音频", "alac", "flac"} and not acodec.startswith("pcm_"))

    def quick_preset(self, key):
        if self._busy:
            return
        opt = Options()
        if key == "small":
            opt.video_codec, opt.quality = "libx265", 28
        elif key == "web":
            opt.format, opt.video_codec, opt.audio_codec, opt.quality = "webm", "libvpx-vp9", "libopus", 32
        elif key == "mp3":
            opt.format, opt.audio_codec = "mp3", "libmp3lame"
        elif key == "flac":
            opt.format, opt.audio_codec = "flac", "flac"
        elif key == "gif":
            opt.format, opt.width, opt.fps = "gif", 640, "15"
        self.apply_options(opt)
        self.status_label.setText("预设已应用")
        self.detail_label.setText("可继续调整右侧参数；开始转换时应用于所有待处理文件。")

    def detect_engine(self):
        try:
            self.ffmpeg, self.ffprobe = find_tools(str(self.settings.get("engine", "")))
            self.engine_status.setText("● FFmpeg 已就绪")
            self.engine_status.setToolTip(str(self.ffmpeg))
        except ValueError as exc:
            self.ffmpeg = self.ffprobe = None
            self.engine_status.setText("● 请配置 FFmpeg")
            self.engine_status.setToolTip(str(exc))
        self.update_buttons()

    def engine_dialog(self):
        if self._busy:
            self.notify("转换进行中", "请等待任务完成或取消转换后再切换引擎。")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("FFmpeg 引擎设置")
        dialog.resize(650, 250)
        layout = QVBoxLayout(dialog)
        layout.addWidget(label("选择包含 ffmpeg.exe 和 ffprobe.exe 的 bin 目录。", "heading", True))
        edit = QLineEdit(str(self.ffmpeg.parent) if self.ffmpeg else str(self.settings.get("engine", "")))
        layout.addWidget(edit)
        def browse():
            path = QFileDialog.getExistingDirectory(dialog, "选择 FFmpeg 目录", edit.text())
            if path:
                edit.setText(path)
        layout.addWidget(button("浏览目录…", browse))
        layout.addWidget(label("打包版本附带引擎；留空可恢复自动检测。", "muted", True))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        def save():
            try:
                find_tools(edit.text().strip())
                self.settings["engine"] = edit.text().strip()
                self.persist_settings()
                self.detect_engine()
                dialog.accept()
            except (ValueError, OSError) as exc:
                self.notify("引擎配置失败", str(exc))
        buttons.accepted.connect(save)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def choose_files(self):
        if self._busy:
            return
        files, _ = QFileDialog.getOpenFileNames(self, "选择音频或视频", str(self.settings.get("last_input", "")), "媒体文件 (*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.ts *.mts *.m2ts *.mpg *.mpeg *.wmv *.flv *.vob *.3gp *.mp3 *.wav *.flac *.m4a *.aac *.ogg *.opus *.aiff *.aif *.wma *.ac3 *.ape *.amr *.mka *.gif *.mxf *.rm *.rmvb);;所有文件 (*)")
        if files:
            self.settings["last_input"] = str(Path(files[0]).parent)
            self.add_paths(files)

    def choose_folder(self):
        if self._busy:
            return
        folder = QFileDialog.getExistingDirectory(self, "选择媒体目录（包含子目录）", str(self.settings.get("last_input", "")))
        if folder:
            self.settings["last_input"] = folder
            self.add_paths([folder])

    def add_paths(self, paths):
        if self._busy:
            return
        if not self.ffprobe:
            self.engine_dialog()
            if not self.ffprobe:
                return
        known = {j.media.path.casefold() for j in self.jobs}
        supported = {"mp4", "mkv", "mov", "avi", "webm", "m4v", "ts", "mts", "m2ts", "mpg", "mpeg", "wmv", "flv", "vob", "3gp", "mp3", "wav", "flac", "m4a", "aac", "ogg", "opus", "aiff", "aif", "wma", "ac3", "eac3", "ape", "amr", "mka", "gif", "mxf", "rm", "rmvb", "nut", "asf", "mp2", "caf", "aifc", "m2v", "m4b", "m4p", "m4r", "alac", "weba"}
        expanded = []
        try:
            for value in paths:
                path = Path(value)
                if path.is_dir():
                    expanded.extend(p for p in path.rglob("*") if p.is_file() and p.suffix.lower().lstrip(".") in supported and ".partial" not in p.name)
                elif path.is_file():
                    expanded.append(path)
        except OSError as exc:
            self.notify("无法读取目录", str(exc))
        unique = []
        for path in expanded:
            value = str(path.resolve())
            if value.casefold() not in known:
                known.add(value.casefold())
                unique.append(value)
        if not unique:
            self.notify("没有新文件", "所选文件已在队列中，或文件夹中没有常见媒体文件。其他扩展名可以通过「添加文件 → 所有文件」直接选择。")
            return
        self._probe_errors = []
        self.set_busy(True)
        self.status_label.setText("正在读取媒体信息…")
        self.detail_label.setText(f"正在检查 {len(unique)} 个文件，界面仍可正常响应。")
        self.prober = ProbeWorker(self.ffprobe, unique, self)
        self.prober.found.connect(self.media_found)
        self.prober.failed.connect(self.probe_failed)
        self.prober.finished.connect(self.probe_finished)
        self.prober.start()

    def media_found(self, media):
        self.jobs.append(Job(media))
        self.refresh_table()

    def probe_failed(self, path, error):
        self._probe_errors.append(f"{Path(path).name}：{error}")
        self.log_edit.appendPlainText(f"无法读取 {path}\n{error}\n")

    def probe_finished(self):
        self.prober.deleteLater()
        self.prober = None
        self.set_busy(False)
        self.status_label.setText("媒体信息已读取")
        self.detail_label.setText(f"队列共有 {len(self.jobs)} 个文件。双击可查看详细信息。")
        if self._probe_errors:
            self.notify("部分文件无法添加", "\n\n".join(self._probe_errors[:5]) + ("\n更多详情见转换日志。" if len(self._probe_errors) > 5 else ""))

    def refresh_table(self):
        self.queue_count.setText(f"转换队列  ·  {len(self.jobs)} 个文件")
        self.queue_page.setCurrentIndex(1 if self.jobs else 0)
        selected = {i.row() for i in self.table.selectionModel().selectedRows()}
        self.table.setRowCount(len(self.jobs))
        for row, job in enumerate(self.jobs):
            media = job.media
            info = f"{media.width}×{media.height} · {media.video.upper()}" if media.video else "音频"
            if media.audio:
                info += f" · {media.audio.upper()}"
            first = QTableWidgetItem(f"{Path(media.path).name}\n{info}")
            first.setToolTip(f"{media.path}\n双击查看媒体信息或错误详情")
            self.table.setItem(row, 0, first)
            self.table.setItem(row, 1, QTableWidgetItem(format_time(media.duration) if media.duration else "未知"))
            self.table.setItem(row, 2, QTableWidgetItem(format_size(media.size)))
            self.table.setItem(row, 3, self.status_item(job))
        for row in selected:
            if row < len(self.jobs):
                self.table.selectRow(row)
        self.update_buttons()

    def status_item(self, job):
        item = QTableWidgetItem(f"{job.progress}%" if job.state == "转换中" else job.state)
        colors = {"已完成": "#73d8b2", "失败": "#ff9da6", "已取消": "#d7b986", "转换中": "#89b0ff"}
        item.setForeground(QColor(colors.get(job.state, "#a1b1cd")))
        if job.error:
            item.setToolTip(job.error[-3000:])
        return item

    def update_job_row(self, job):
        row = self.jobs.index(job)
        self.table.setItem(row, 3, self.status_item(job))

    def set_busy(self, busy):
        self._busy = busy
        for widget in [self.add_button, self.add_folder_button, self.remove_button, self.clear_button, self.params_container, self.output_edit, self.browse_output_button, *self.preset_buttons]:
            widget.setEnabled(not busy)
        self.update_buttons()

    def update_buttons(self):
        if not hasattr(self, "start_button"):
            return
        self.start_button.setEnabled(not self._busy and bool(self.ffmpeg) and any(j.state != "已完成" for j in self.jobs))
        self.cancel_button.setEnabled(self.converter is not None and not self.converter.cancelled.is_set())

    def choose_output(self):
        folder = QFileDialog.getExistingDirectory(self, "选择输出目录", self.output_edit.text())
        if folder:
            self.output_edit.setText(folder)

    def start_conversion(self):
        if self._busy or not self.ffmpeg:
            return
        pending = [j for j in self.jobs if j.state != "已完成"]
        if not pending:
            return
        options = self.current_options()
        reserved = set()
        tasks = []
        try:
            options.validate()
            for job in pending:
                try:
                    options.validate(job.media)
                except ValueError as exc:
                    raise ValueError(f"{Path(job.media.path).name}\n{exc}") from None
                folder = Path(self.output_edit.text().strip()).expanduser() if self.output_edit.text().strip() else Path(job.media.path).parent
                folder = folder.resolve()
                folder.mkdir(parents=True, exist_ok=True)
                tasks.append((job, output_path(job.media, folder, options.extension, reserved)))
        except (ValueError, OSError) as exc:
            self.notify("请检查转换设置", str(exc))
            return
        self.persist_settings()
        self._batch_ids = [job.id for job in pending]
        for job in pending:
            job.progress, job.state, job.error, job.output = 0, "等待转换", "", ""
        self.converter = ConversionWorker(self.ffmpeg, tasks, options, self)
        self.converter.status.connect(self.conversion_status)
        self.converter.progress.connect(self.conversion_progress)
        self.converter.log.connect(self.log_edit.appendPlainText)
        self.converter.finished.connect(self.conversion_finished)
        self.set_busy(True)
        self.refresh_table()
        self.overall_progress.setValue(0)
        self.status_label.setText(f"正在转换  ·  {len(tasks)} 个任务")
        self.detail_label.setText("所有任务使用当前参数，按顺序处理。")
        self.converter.start()

    def conversion_status(self, job_id, state, detail):
        job = next((j for j in self.jobs if j.id == job_id), None)
        if not job:
            return
        job.state = state
        if state in {"转换中", "已完成"}:
            job.output = detail
        if state == "失败":
            job.error = detail
        self.update_job_row(job)
        self.update_overall()

    def conversion_progress(self, job_id, value, speed):
        job = next((j for j in self.jobs if j.id == job_id), None)
        if job:
            job.progress = value
            self.update_job_row(job)
            self.detail_label.setText(f"{Path(job.media.path).name}  ·  {value}%" + (f"  ·  速度 {speed}" if speed and speed != "N/A" else ""))
            self.update_overall()

    def update_overall(self):
        batch = [j for j in self.jobs if j.id in self._batch_ids]
        if batch:
            value = sum(100 if j.state in {"已完成", "失败", "已取消"} else j.progress for j in batch) // len(batch)
            self.overall_progress.setValue(value)

    def cancel_conversion(self):
        if self.converter:
            self.converter.cancel()
            self.cancel_button.setEnabled(False)
            self.status_label.setText("正在取消并清理临时文件…")

    def conversion_finished(self):
        self.converter.deleteLater()
        self.converter = None
        self.set_busy(False)
        batch = [j for j in self.jobs if j.id in self._batch_ids]
        done = sum(j.state == "已完成" for j in batch)
        failed = sum(j.state == "失败" for j in batch)
        cancelled = sum(j.state == "已取消" for j in batch)
        self.status_label.setText("转换结束" if failed or cancelled else "全部转换完成")
        self.detail_label.setText(f"成功 {done}  ·  失败 {failed}  ·  取消 {cancelled}" + ("。双击失败任务查看原因，调整参数后可重试。" if failed else "。可打开输出目录查看文件。"))
        self.refresh_table()
        QApplication.alert(self, 2000)

    def selected_jobs(self):
        return [self.jobs[i.row()] for i in self.table.selectionModel().selectedRows() if i.row() < len(self.jobs)]

    def remove_selected(self):
        if self._busy:
            return
        selected = {j.id for j in self.selected_jobs()}
        self.jobs = [j for j in self.jobs if j.id not in selected]
        self.refresh_table()

    def clear_jobs(self):
        if not self._busy:
            self.jobs.clear()
            self.refresh_table()
            self.overall_progress.setValue(0)
            self.status_label.setText("准备就绪")
            self.detail_label.setText("添加媒体文件以开始新的转换。")

    def open_output(self):
        selected = self.selected_jobs()
        completed = [j for j in self.jobs if j.state == "已完成" and j.output]
        if selected and selected[0].state == "已完成" and selected[0].output:
            folder = Path(selected[0].output).parent
        elif completed:
            folder = Path(completed[-1].output).parent
        elif self.output_edit.text().strip():
            folder = Path(self.output_edit.text().strip()).expanduser()
        elif self.jobs:
            folder = Path(self.jobs[0].media.path).parent
        else:
            self.notify("尚未设置输出目录", "添加文件或选择输出目录后，即可在这里打开目录。")
            return
        if not folder.is_dir():
            self.notify("目录不存在", str(folder))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder.resolve())))

    def media_details(self, row, _column=0):
        if row >= len(self.jobs):
            return
        job = self.jobs[row]
        text = f"源文件：{job.media.path}\n时长：{format_time(job.media.duration)}\n大小：{format_size(job.media.size)}\n状态：{job.state}\n"
        if job.output:
            text += f"输出：{job.output}\n"
        if job.error:
            text += f"\n转换错误：\n{job.error}\n\n建议：检查封装与编码器是否兼容。硬件编码失败可切换到 libx264 / libx265。\n"
        text += f"\n完整媒体信息：\n{job.media.raw}"
        self.text_dialog("媒体信息", text)

    def queue_menu(self, point):
        row = self.table.rowAt(point.y())
        if row < 0:
            return
        menu = QMenu(self)
        menu.addAction("查看媒体信息 / 错误详情", lambda: self.media_details(row))
        menu.addAction("打开源文件所在目录", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.jobs[row].media.path).parent))))
        if self.jobs[row].state == "已完成":
            menu.addAction("打开转换后的文件", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.jobs[row].output)))
            if not self._busy:
                menu.addAction("重新加入待转换", lambda: self.requeue(row))
        if not self._busy:
            menu.addAction("移除选中任务", self.remove_selected)
        menu.exec(self.table.viewport().mapToGlobal(point))

    def requeue(self, row):
        self.jobs[row].state, self.jobs[row].progress = "等待转换", 0
        self.refresh_table()

    def command_dialog(self):
        jobs = self.selected_jobs() or self.jobs
        if not jobs:
            self.notify("请先添加文件", "读取媒体后即可查看针对该文件生成的 FFmpeg 命令。")
            return
        try:
            opt = self.current_options()
            opt.validate(jobs[0].media)
            folder = Path(self.output_edit.text().strip()) if self.output_edit.text().strip() else Path(jobs[0].media.path).parent
            target = output_path(jobs[0].media, folder.resolve(), opt.extension)
            args = build_command(self.ffmpeg, jobs[0].media, opt, target)
            self.text_dialog("FFmpeg 命令预览", "以下命令可复制；实际转换使用临时文件，成功后再保存为最终文件。\n\n" + display_command(args))
        except (ValueError, OSError) as exc:
            self.notify("参数无效", str(exc))

    def presets_menu(self):
        menu = QMenu(self)
        menu.addAction("导出当前参数…", self.export_preset)
        menu.addAction("导入参数预设…", self.import_preset)
        menu.addSeparator()
        menu.addAction("恢复默认参数", lambda: self.apply_options(Options()))
        menu.exec(self.params_container.mapToGlobal(self.params_container.rect().topRight()))

    def export_preset(self):
        try:
            options = self.current_options()
            options.validate()
            path, _ = QFileDialog.getSaveFileName(self, "导出预设", "FormatKae-preset.json", "JSON 预设 (*.json)")
            if path:
                Path(path).write_text(json.dumps({"app": APP_NAME, "version": VERSION, "options": options.as_dict()}, ensure_ascii=False, indent=2), encoding="utf-8")
        except (OSError, ValueError) as exc:
            self.notify("无法导出预设", str(exc))

    def import_preset(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入预设", "", "JSON 预设 (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("options"), dict):
                raise ValueError("不是有效的 FormatKae 预设文件。")
            options = Options.from_dict(data["options"])
            options.validate()
            self.apply_options(options)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self.notify("无法导入预设", str(exc))

    def persist_settings(self):
        self.settings["options"] = self.current_options().as_dict()
        self.settings["output"] = self.output_edit.text().strip()
        try:
            save_settings(self.settings)
        except OSError as exc:
            self.log_edit.appendPlainText(f"无法保存个人设置：{exc}")

    def text_dialog(self, title, text):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(820, 590)
        layout = QVBoxLayout(dialog)
        edit = QPlainTextEdit(text)
        edit.setReadOnly(True)
        edit.setFont(QFont("Consolas", 10))
        layout.addWidget(edit)
        controls = QHBoxLayout()
        controls.addWidget(button("复制全部", lambda: QApplication.clipboard().setText(text)))
        controls.addStretch()
        controls.addWidget(button("关闭", dialog.accept))
        layout.addLayout(controls)
        dialog.exec()

    def help_dialog(self):
        self.text_dialog("使用说明 / 关于 FormatKae", f"""FormatKae {VERSION} · Windows x64 音视频格式转换器

1. 添加文件、文件夹或将文件拖入窗口。Ctrl+O 可快速添加文件。
2. 选择左侧快速预设，或在右侧选择目标格式与编码参数。
3. 指定输出目录；留空则分别保存到每个源文件旁。
4. 点击开始转换。双击任务可查看媒体信息或错误详情。

批量队列：本次所有待处理文件使用同一组参数，顺序执行。
已完成的文件不会重复转换；右键「重新加入待转换」可再次处理。
失败或取消的文件可调整参数后重试；单个转换失败会继续后续任务。
文件夹添加会搜索子目录中的常见媒体文件；其他扩展名可直接添加。

画质与体积：CRF / CQ 越低通常画质越高、文件越大。视频码率有值时优先。
编码速度：用于 x264 / x265 / SVT-AV1，越慢通常压缩率越高。
copy：直接复制轨道，不改变编码；不能同时缩放、变速或调整对应音频参数。
时间裁剪：开始和结束均为源文件中的位置，可填写秒数或 HH:MM:SS。
copy 模式可能按关键帧定位，精确裁剪请重新编码。
GIF：默认 640 像素宽、15 FPS；包含调色板优化，不带声音。
无损音频：FLAC / PCM / ALAC 无损保存解码后的音频，不能恢复源文件已经损失的细节。
音频输入转换为视频封装时仅输出音频轨道，不会自动生成画面。

高级参数：可追加 FFmpeg 输出选项，例如 -vf "hflip" 或 -metadata title="示例"。
同名选项以最后出现的为准；自定义 -vf / -af 会替换界面生成的对应滤镜。
选项的字符串值请用引号包围，不要添加输入或输出文件路径。
自定义封装：填扩展名并选择兼容编码器，例如 nut / mxf。
并非任意编码器都适用于任意封装；FFmpeg 错误会保留在日志中。
NVENC / QSV / AMF 需要支持的硬件及驱动，失败时可改用软件编码器。
默认只处理首个视频轨道和首个音轨，不保留字幕、附件或其他轨道。
额外 -map 等选项需要自行理解 FFmpeg 的流映射规则。

文件安全：不会覆盖原文件或已存在的输出，输出名添加 _converted 和自动编号。
取消或失败会删除本次临时文件；异常断电留下的 .partial 文件可手动删除。
转换完全在本机执行，不上传素材。设置保存在 %APPDATA%\\FormatKae\\settings.json。
可通过预设菜单导入/导出 JSON 参数文件。

引擎：{self.ffmpeg or '尚未配置'}
官方文档：https://ffmpeg.org/ffmpeg.html
界面：Qt for Python / PySide6（https://doc.qt.io/qtforpython-6/）
打包：PyInstaller（https://pyinstaller.org/）
第三方许可及 FFmpeg 源码信息见随附 THIRD_PARTY_NOTICES.md 和 licenses 目录。
""")

    def notify(self, title, message):
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setIcon(QMessageBox.Icon.Information)
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText(message[:6000])
        box.exec()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and not self._busy:
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not self._busy:
            self.add_paths([url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()])
            event.acceptProposedAction()

    def closeEvent(self, event):
        if self.converter:
            answer = QMessageBox.question(self, "退出 FormatKae", "转换仍在进行，退出将取消本次未完成任务。是否退出？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.converter.cancel()
            if not self.converter.wait(5000):
                event.ignore()
                self.status_label.setText("正在清理任务，完成后可关闭窗口。")
                return
        if self.prober and self.prober.isRunning():
            self.prober.requestInterruption()
            if not self.prober.wait(2000):
                event.ignore()
                self.status_label.setText("正在结束媒体检测，稍后可关闭窗口。")
                return
        self.persist_settings()
        event.accept()
