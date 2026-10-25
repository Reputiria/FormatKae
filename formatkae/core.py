"""FFmpeg discovery, media inspection and validated conversion commands."""
from __future__ import annotations

import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

APP_NAME = "FormatKae"
VERSION = "1.0.0"
DEFAULT_FFMPEG = Path(r"D:\4Application\ffmpeg-2026-08-30-git-818cecc6e1-full_build\ffmpeg-2026-08-30-git-818cecc6e1-full_build\bin")
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@dataclass(frozen=True)
class Format:
    label: str
    ext: str
    video: str | None
    audio: str | None
    kind: str


FORMATS = [
    Format("MP4 · 通用视频", "mp4", "libx264", "aac", "video"),
    Format("MKV · 高清封装", "mkv", "libx264", "aac", "video"),
    Format("MOV · QuickTime", "mov", "libx264", "aac", "video"),
    Format("WebM · 网页视频", "webm", "libvpx-vp9", "libopus", "video"),
    Format("AVI · 传统视频", "avi", "mpeg4", "libmp3lame", "video"),
    Format("M4V · MPEG-4 视频", "m4v", "libx264", "aac", "video"),
    Format("TS · MPEG 传输流", "ts", "libx264", "aac", "video"),
    Format("FLV · Flash 视频", "flv", "flv", "libmp3lame", "video"),
    Format("MPG · MPEG-2 视频", "mpg", "mpeg2video", "mp2", "video"),
    Format("WMV · Windows 视频", "wmv", "wmv2", "wmav2", "video"),
    Format("GIF · 动态图片", "gif", "gif", None, "gif"),
    Format("MP3 · 通用音频", "mp3", None, "libmp3lame", "audio"),
    Format("WAV · 无损音频", "wav", None, "pcm_s16le", "audio"),
    Format("FLAC · 无损压缩", "flac", None, "flac", "audio"),
    Format("AAC · 高效音频", "aac", None, "aac", "audio"),
    Format("M4A · MPEG-4 音频", "m4a", None, "aac", "audio"),
    Format("OGG · Vorbis 音频", "ogg", None, "libvorbis", "audio"),
    Format("Opus · 低延迟音频", "opus", None, "libopus", "audio"),
    Format("AIFF · 无损音频", "aiff", None, "pcm_s16be", "audio"),
    Format("WMA · Windows 音频", "wma", None, "wmav2", "audio"),
    Format("AC3 · 杜比音频", "ac3", None, "ac3", "audio"),
    Format("自定义封装格式", "nut", "libx264", "aac", "custom"),
]
FORMAT_MAP = {f.ext: f for f in FORMATS}
VIDEO_CODECS = ["libx264", "libx265", "libsvtav1", "libvpx-vp9", "libvpx", "mpeg4", "mpeg2video", "prores_ks", "ffv1", "wmv2", "flv", "h264_nvenc", "hevc_nvenc", "av1_nvenc", "h264_qsv", "hevc_qsv", "h264_amf", "hevc_amf", "copy"]
AUDIO_CODECS = ["aac", "libmp3lame", "flac", "alac", "libopus", "libvorbis", "pcm_s16le", "pcm_s24le", "pcm_s32le", "pcm_f32le", "pcm_s16be", "ac3", "eac3", "mp2", "wmav2", "copy", "禁用音频"]


def app_root() -> Path:
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent


def config_path() -> Path:
    return Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME / "settings.json"


def load_settings() -> dict:
    try:
        data = json.loads(config_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(data: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


def find_tools(custom: str = "") -> tuple[Path, Path]:
    candidates = []
    if custom:
        path = Path(custom)
        candidates.append(path.parent if path.is_file() else path)
    else:
        candidates.extend([app_root() / "ffmpeg" / "bin", app_root() / "ffmpeg", DEFAULT_FFMPEG])
        found = shutil.which("ffmpeg")
        if found:
            candidates.append(Path(found).parent)
    for folder in candidates:
        ffmpeg, ffprobe = folder / "ffmpeg.exe", folder / "ffprobe.exe"
        if ffmpeg.is_file() and ffprobe.is_file():
            return ffmpeg.resolve(), ffprobe.resolve()
    raise ValueError("未找到 ffmpeg.exe 和 ffprobe.exe，请在「引擎设置」中选择包含这两个文件的目录。")


@dataclass
class Media:
    path: str
    duration: float = 0
    size: int = 0
    video: str = ""
    audio: str = ""
    width: int = 0
    height: int = 0
    fps: str = ""
    sample_rate: str = ""
    channels: int = 0
    audio_streams: int = 0
    video_streams: int = 0
    raw: str = ""


def probe(ffprobe: Path, path: str, cancelled=None) -> Media:
    with subprocess.Popen([str(ffprobe), "-v", "error", "-show_format", "-show_streams", "-of", "json", str(Path(path).resolve())], stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", errors="replace", creationflags=CREATE_NO_WINDOW) as process:
        deadline = time.monotonic() + 60
        while True:
            try:
                stdout, stderr = process.communicate(timeout=0.2)
                break
            except subprocess.TimeoutExpired:
                if (cancelled and cancelled()) or time.monotonic() > deadline:
                    process.kill()
                    process.communicate()
                    raise ValueError("媒体检测已取消或超时。") from None
        if process.returncode:
            raise ValueError(stderr.strip()[-1500:] or "文件无法读取或不是支持的媒体文件。")
    data = json.loads(stdout)
    streams = data.get("streams", [])
    videos = [s for s in streams if s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    if not videos and not audios:
        raise ValueError("此文件不包含可转换的音频或视频轨道。")
    video, audio = (videos or [{}])[0], (audios or [{}])[0]
    fmt = data.get("format", {})
    try:
        duration = float(fmt.get("duration", video.get("duration", audio.get("duration", 0))))
    except (ValueError, TypeError):
        duration = 0
    if not math.isfinite(duration) or duration < 0:
        duration = 0
    return Media(str(Path(path).resolve()), duration, Path(path).stat().st_size, video.get("codec_name", ""), audio.get("codec_name", ""), video.get("width", 0), video.get("height", 0), video.get("avg_frame_rate", ""), audio.get("sample_rate", ""), audio.get("channels", 0), len(audios), len(videos), json.dumps(data, ensure_ascii=False, indent=2))


def time_seconds(value: str) -> float:
    if not value.strip():
        return 0
    parts = value.strip().split(":")
    if len(parts) > 3:
        raise ValueError("时间格式应为秒数或 HH:MM:SS，例如 00:01:30。")
    try:
        values = [float(p) for p in parts]
        if any(not math.isfinite(v) or v < 0 for v in values):
            raise ValueError()
        if len(values) > 1 and any(v >= 60 for v in values[1:]):
            raise ValueError()
        return sum(v * 60**i for i, v in enumerate(reversed(values)))
    except ValueError:
        raise ValueError("时间必须是非负秒数或有效的 HH:MM:SS。") from None


@dataclass
class Options:
    format: str = "mp4"
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    quality: int = 23
    preset: str = "medium"
    video_bitrate: str = ""
    width: int = 0
    height: int = 0
    fps: str = ""
    audio_bitrate: str = "192k"
    sample_rate: str = ""
    channels: str = ""
    volume: float = 100
    start: str = ""
    end: str = ""
    threads: int = 0
    metadata: bool = True
    extra: str = ""
    custom_ext: str = "nut"

    @classmethod
    def from_dict(cls, data: dict) -> "Options":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def as_dict(self) -> dict:
        return asdict(self)

    @property
    def profile(self) -> Format:
        return FORMAT_MAP[self.format]

    @property
    def extension(self) -> str:
        return self.custom_ext.strip().lstrip(".").lower() if self.profile.kind == "custom" else self.format

    def validate(self, media: Media | None = None) -> None:
        if self.format not in FORMAT_MAP:
            raise ValueError("请选择有效的输出格式。")
        if not re.fullmatch(r"[a-zA-Z0-9]{1,12}", self.extension):
            raise ValueError("自定义扩展名只能包含 1–12 个英文字母或数字。")
        for name, value in [("视频码率", self.video_bitrate), ("音频码率", self.audio_bitrate)]:
            if value and (not re.fullmatch(r"[1-9]\d*(?:\.\d+)?[kKmM]?", value) or float(value.rstrip("kKmM")) <= 0):
                raise ValueError(f"{name}格式不正确，例如 192k、5M。")
        if self.fps:
            try:
                parts = self.fps.split("/")
                rate = float(parts[0]) / float(parts[1]) if len(parts) == 2 else float(self.fps)
                if not math.isfinite(rate) or not 0 < rate <= 1000:
                    raise ValueError()
            except (ValueError, ZeroDivisionError):
                raise ValueError("帧率必须是 0–1000 之间的正数或分数，例如 30、30000/1001。") from None
        start, end = time_seconds(self.start), time_seconds(self.end)
        if self.end.strip() and end <= start:
            raise ValueError("结束时间必须大于开始时间。")
        if media and media.duration and start >= media.duration:
            raise ValueError("开始时间已超出媒体时长。")
        if self.width < 0 or self.height < 0 or self.width > 16384 or self.height > 16384:
            raise ValueError("分辨率需在 0–16384 之间，0 表示自动。")
        if not 0 <= self.quality <= 63 or not 0 <= self.volume <= 400:
            raise ValueError("质量或音量超出有效范围。")
        if self.sample_rate and (not self.sample_rate.isdigit() or not 8000 <= int(self.sample_rate) <= 384000):
            raise ValueError("音频采样率需在 8000–384000 Hz 之间。")
        if self.channels and (not self.channels.isdigit() or not 1 <= int(self.channels) <= 8):
            raise ValueError("声道数需在 1–8 之间。")
        for codec in (self.video_codec, self.audio_codec):
            if codec != "禁用音频" and not re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9_-]*", codec):
                raise ValueError("编码器名称只能使用字母、数字、下划线和连字符。")
        if self.preset not in {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"}:
            raise ValueError("请选择有效的编码速度预设。")
        if self.video_codec == "copy" and (self.width or self.height or self.fps or self.video_bitrate):
            raise ValueError("视频直接复制时不能改变分辨率、帧率或码率；请先选择视频编码器。")
        if self.audio_codec == "copy" and (self.sample_rate or self.channels or self.volume != 100):
            raise ValueError("音频直接复制时不能改变采样率、声道数或音量。")
        if media:
            if self.profile.kind == "audio" and not media.audio:
                raise ValueError("源文件没有音轨，无法导出音频。")
            if self.profile.kind == "audio" and self.audio_codec == "禁用音频":
                raise ValueError("导出音频格式时不能禁用音频。")
            if self.profile.kind == "gif" and not media.video:
                raise ValueError("生成 GIF 需要源文件包含视频。")
            if not media.video and self.audio_codec == "禁用音频":
                raise ValueError("源文件只有音频，不能禁用音频轨道。")
        parse_extra(self.extra)


def parse_extra(value: str) -> list[str]:
    try:
        args = shlex.split(value, posix=True)
    except ValueError as exc:
        raise ValueError(f"自定义参数的引号不完整：{exc}") from None
    forbidden = {"-i", "-y", "-n", "-progress", "-stdin", "-nostdin", "-report", "-passlogfile", "-filter_script", "-filter_complex_script", "-attach", "-dump_attachment", "-h", "-help", "-version", "-encoders", "-formats"}
    no_value = {"-shortest", "-an", "-vn", "-sn", "-dn", "-bitexact", "-copyts", "-start_at_zero", "-copyinkf"}
    i = 0
    while i < len(args):
        arg = args[i]
        if not arg.startswith("-") or arg.split(":")[0] in forbidden or arg.startswith("-/"):
            raise ValueError(f"自定义参数仅支持输出选项，不能添加输入/输出文件、覆盖或进度控制：{arg}")
        if arg in no_value:
            i += 1
        else:
            if i + 1 >= len(args) or (args[i + 1].startswith("-") and not re.fullmatch(r"-\d+(?:\.\d+)?", args[i + 1]) and not (arg == "-map" and re.fullmatch(r"-\d+(?::[a-zA-Z0-9?]+)*", args[i + 1]))):
                raise ValueError(f"自定义选项 {arg} 缺少参数值。")
            i += 2
    return args


def output_path(media: Media, folder: Path, extension: str, reserved: set[str] | None = None) -> Path:
    reserved = reserved if reserved is not None else set()
    base = Path(media.path).stem + "_converted"
    for index in range(100000):
        suffix = "" if index == 0 else f"_{index}"
        path = folder / f"{base}{suffix}.{extension}"
        key = str(path.resolve()).casefold()
        if key != str(Path(media.path).resolve()).casefold() and key not in reserved and not path.exists():
            reserved.add(key)
            return path
    raise ValueError("输出目录内同名文件过多，请选择其他目录。")


def effective_duration(media: Media, options: Options) -> float:
    start = time_seconds(options.start)
    end = time_seconds(options.end) if options.end.strip() else media.duration
    if media.duration:
        end = min(end, media.duration)
    return max(0, end - start)


def build_command(ffmpeg: Path, media: Media, opt: Options, output: Path) -> list[str]:
    opt.validate(media)
    profile = opt.profile
    args = [str(ffmpeg), "-hide_banner", "-nostdin", "-n", "-loglevel", "info", "-progress", "pipe:1", "-nostats"]
    start = time_seconds(opt.start)
    if start:
        args += ["-ss", f"{start:g}"]
    args += ["-i", media.path]
    if opt.end.strip():
        args += ["-t", f"{time_seconds(opt.end) - start:g}"]
    args += ["-map_metadata", "0" if opt.metadata else "-1"]
    has_video = bool(media.video) and profile.kind != "audio"
    if has_video:
        if profile.kind == "gif":
            width = opt.width or min(media.width or 640, 640)
            height = opt.height or -1
            fps = opt.fps or "15"
            args += ["-filter_complex", f"[0:V:0]fps={fps},scale={width}:{height}:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse[gifout]", "-map", "[gifout]", "-loop", "0", "-an"]
        else:
            args += ["-map", "0:V:0"]
            codec = opt.video_codec
            args += ["-c:v", codec]
            if codec != "copy":
                if opt.width or opt.height:
                    args += ["-vf", f"scale={opt.width or -2}:{opt.height or -2}"]
                if opt.fps:
                    args += ["-r", opt.fps]
                if opt.video_bitrate:
                    args += ["-b:v", opt.video_bitrate]
                elif codec in {"libx264", "libx265", "libsvtav1", "libvpx-vp9", "libvpx"}:
                    max_quality = 51 if codec in {"libx264", "libx265"} else 63
                    args += ["-crf", str(min(opt.quality, max_quality))]
                    if codec.startswith("libvpx"):
                        args += ["-b:v", "0"]
                elif codec.endswith("_nvenc"):
                    args += ["-rc", "vbr", "-cq", str(min(opt.quality, 51)), "-b:v", "0"]
                if codec in {"libx264", "libx265"}:
                    args += ["-preset", opt.preset, "-pix_fmt", "yuv420p"]
                elif codec == "libsvtav1":
                    args += ["-preset", {"ultrafast": "12", "superfast": "11", "veryfast": "10", "faster": "9", "fast": "8", "medium": "7", "slow": "6", "slower": "5", "veryslow": "4"}[opt.preset], "-pix_fmt", "yuv420p"]
                elif codec == "mpeg2video":
                    args += ["-pix_fmt", "yuv420p"]
                if codec in {"libx265", "hevc_nvenc", "hevc_qsv", "hevc_amf"} and opt.extension in {"mp4", "mov", "m4v"}:
                    args += ["-tag:v", "hvc1"]
    else:
        args += ["-vn"]
    if profile.kind != "gif" and media.audio and opt.audio_codec != "禁用音频":
        args += ["-map", "0:a:0", "-c:a", opt.audio_codec]
        if opt.audio_codec != "copy":
            if opt.audio_bitrate and opt.audio_codec not in {"flac", "alac"} and not opt.audio_codec.startswith("pcm_"):
                args += ["-b:a", opt.audio_bitrate]
            if opt.sample_rate:
                args += ["-ar", opt.sample_rate]
            if opt.channels:
                args += ["-ac", opt.channels]
            if opt.volume != 100:
                args += ["-af", f"volume={opt.volume / 100:g}"]
    else:
        args += ["-an"]
    if opt.threads:
        args += ["-threads", str(opt.threads)]
    if opt.extension in {"mp4", "m4a", "mov", "m4v"}:
        args += ["-movflags", "+faststart"]
    if opt.extension == "m4v":
        args += ["-f", "mp4"]
    args += parse_extra(opt.extra)
    args.append(str(output))
    return args


def display_command(args: list[str]) -> str:
    return subprocess.list2cmdline(args)


def format_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 3600:02}:{seconds // 60 % 60:02}:{seconds % 60:02}"


def format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return ""
