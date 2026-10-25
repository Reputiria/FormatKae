"""Background workers. UI widgets are only touched through Qt signals."""
from __future__ import annotations

import os
import subprocess
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .core import CREATE_NO_WINDOW, Media, Options, build_command, display_command, effective_duration, probe


@dataclass
class Job:
    media: Media
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    state: str = "等待转换"
    progress: int = 0
    output: str = ""
    error: str = ""


class ProbeWorker(QThread):
    found = Signal(object)
    failed = Signal(str, str)

    def __init__(self, ffprobe: Path, paths: list[str], parent=None):
        super().__init__(parent)
        self.ffprobe = ffprobe
        self.paths = paths

    def run(self):
        for path in self.paths:
            if self.isInterruptionRequested():
                break
            try:
                self.found.emit(probe(self.ffprobe, path, self.isInterruptionRequested))
            except Exception as exc:
                self.failed.emit(path, str(exc))


class ConversionWorker(QThread):
    status = Signal(str, str, str)
    progress = Signal(str, int, str)
    log = Signal(str)

    def __init__(self, ffmpeg: Path, jobs: list[tuple[Job, Path]], options: Options, parent=None):
        super().__init__(parent)
        self.ffmpeg = ffmpeg
        self.jobs = jobs
        self.options = options
        self.cancelled = threading.Event()
        self._lock = threading.Lock()
        self._process = None

    def cancel(self):
        self.cancelled.set()
        with self._lock:
            if self._process and self._process.poll() is None:
                try:
                    self._process.kill()
                except OSError:
                    pass

    def run(self):
        for job, target in self.jobs:
            if self.cancelled.is_set():
                self.status.emit(job.id, "已取消", "")
                continue
            temp = target.with_name(f".{target.stem}.{uuid.uuid4().hex[:12]}.partial{target.suffix}")
            errors = deque(maxlen=100)
            reader = None
            process = None
            try:
                args = build_command(self.ffmpeg, job.media, self.options, temp)
                self.log.emit(f"\n{'─' * 56}\n{Path(job.media.path).name}\n{display_command(args)}\n")
                self.status.emit(job.id, "转换中", str(target))
                with self._lock:
                    if self.cancelled.is_set():
                        self.status.emit(job.id, "已取消", "")
                        continue
                    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace", creationflags=CREATE_NO_WINDOW)
                    self._process = process

                def read_errors():
                    for line in process.stderr:
                        errors.append(line.rstrip())
                        self.log.emit(line.rstrip())

                reader = threading.Thread(target=read_errors, daemon=True)
                reader.start()
                duration = effective_duration(job.media, self.options)
                speed = ""
                last_emit = 0.0
                for line in process.stdout:
                    key, _, value = line.strip().partition("=")
                    if key == "speed":
                        speed = value
                    if key == "out_time_us":
                        try:
                            seconds = max(0, int(value) / 1_000_000)
                        except ValueError:
                            continue
                        percent = min(99, int(seconds / duration * 100)) if duration > 0 else 0
                        now = time.monotonic()
                        if now - last_emit > 0.15:
                            self.progress.emit(job.id, percent, speed)
                            last_emit = now
                code = process.wait()
                reader.join(timeout=3)
                if self.cancelled.is_set():
                    self.status.emit(job.id, "已取消", "")
                elif code:
                    raise RuntimeError("\n".join(errors)[-7000:] or f"FFmpeg 退出码：{code}")
                elif not temp.is_file() or not temp.stat().st_size:
                    raise RuntimeError("FFmpeg 没有生成有效的输出文件。")
                else:
                    # Windows rename refuses to replace a file created by another application.
                    if target.exists():
                        raise RuntimeError("输出文件在转换期间被其他程序创建，已保留现有文件。请重试。")
                    os.rename(temp, target)
                    self.progress.emit(job.id, 100, speed)
                    self.status.emit(job.id, "已完成", str(target))
                    self.log.emit(f"✓ 已保存：{target}")
            except Exception as exc:
                if process and process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
                if self.cancelled.is_set():
                    self.status.emit(job.id, "已取消", "")
                else:
                    message = str(exc)
                    self.log.emit(f"✕ 转换失败：{message}")
                    self.status.emit(job.id, "失败", message)
            finally:
                if reader:
                    reader.join(timeout=3)
                if process:
                    if process.stdout:
                        process.stdout.close()
                    if process.stderr:
                        process.stderr.close()
                with self._lock:
                    self._process = None
                try:
                    temp.unlink(missing_ok=True)
                except OSError as exc:
                    self.log.emit(f"临时文件无法清理：{temp} ({exc})")
