"""Exercise the real Qt window and QThread/subprocess lifecycle."""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "test-artifacts"
ARTIFACTS.mkdir(exist_ok=True)
os.environ["APPDATA"] = str(ARTIFACTS / "test-settings")
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from formatkae.core import Media, Options, find_tools, probe
from formatkae.theme import STYLE
from formatkae.window import MainWindow
from formatkae.workers import ConversionWorker, Job


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    reports = []

    def check(name, success):
        reports.append({"test": name, "success": bool(success)})
        print(f"{'PASS' if success else 'FAIL'} {name}", flush=True)
        if not success:
            raise AssertionError(name)

    def wait_for(predicate, timeout=25):
        deadline = time.monotonic() + timeout
        while not predicate():
            app.processEvents()
            if time.monotonic() > deadline:
                raise TimeoutError("Timed out waiting for Qt worker")
            time.sleep(0.01)
        app.processEvents()

    sample = ARTIFACTS / "中文 测试素材.mp4"
    if not sample.exists():
        raise RuntimeError("Run integration_test.py first")
    ffmpeg, ffprobe = find_tools()
    original = hashlib.sha256(sample.read_bytes()).hexdigest()
    window = MainWindow()
    notifications = []
    window.notify = lambda title, message: notifications.append((title, message))
    window.show()
    app.processEvents()
    check("window starts with engine and correct default settings", window.ffmpeg and window.current_options() == Options())
    for name in ["balanced", "small", "web", "mp3", "flac", "gif"]:
        window.quick_preset(name)
        window.current_options().validate()
    check("all quick presets produce valid options", True)
    window.quick_preset("balanced")
    window.add_paths([str(sample), str(sample)])
    wait_for(lambda: window.prober is None)
    check("background inspection and duplicate input prevention", len(window.jobs) == 1 and not notifications)
    window.width.setValue(160)
    window.video_codec.setCurrentText("copy")
    check("copy codec clears incompatible transforms", window.width.value() == 0 and window.current_options().video_codec == "copy")
    window.quick_preset("balanced")
    out = ARTIFACTS / "gui-output"
    out.mkdir(exist_ok=True)
    window.output_edit.setText(str(out))
    window.width.setValue(160)
    window.start_edit.setText("0.25")
    window.end_edit.setText("1.25")
    window.start_conversion()
    wait_for(lambda: window.converter is None)
    check("GUI queue converts successfully", window.jobs[0].state == "已完成" and window.jobs[0].progress == 100)
    output = Path(window.jobs[0].output)
    converted = probe(ffprobe, str(output))
    check("GUI parameters reach FFmpeg", converted.width == 160 and abs(converted.duration - 1) < 0.2)
    check("original input unchanged", hashlib.sha256(sample.read_bytes()).hexdigest() == original)
    window.requeue(0)
    window.start_conversion()
    wait_for(lambda: window.converter is None)
    check("repeat output gets unique filename", Path(window.jobs[0].output) != output and output.exists())
    window.grab().save(str(ARTIFACTS / "gui-converted.png"))

    # A corrupt/missing input must not prevent the next independent queue job.
    media = probe(ffprobe, str(sample))
    missing = Media(str(ARTIFACTS / "missing.mp4"), duration=2, video="h264", audio="aac")
    fail_target = out / "should-not-exist.mp4"
    good_target = out / "after-error.mp4"
    fail_target.unlink(missing_ok=True)
    good_target.unlink(missing_ok=True)
    states = {}
    worker = ConversionWorker(ffmpeg, [(Job(missing, id="bad"), fail_target), (Job(media, id="good"), good_target)], Options())
    worker.status.connect(lambda identity, state, detail: states.__setitem__(identity, state))
    worker.start()
    wait_for(lambda: worker.isFinished())
    worker.wait()
    check("failed task continues to next file", states == {"bad": "失败", "good": "已完成"} and good_target.exists() and not fail_target.exists())

    # An output created externally must be preserved even after transcoding succeeds.
    occupied = out / "occupied.mp4"
    occupied.write_bytes(b"keep existing file")
    states = {}
    worker = ConversionWorker(ffmpeg, [(Job(media, id="occupied"), occupied)], Options())
    worker.status.connect(lambda identity, state, detail: states.__setitem__(identity, state))
    worker.start()
    wait_for(lambda: worker.isFinished())
    worker.wait()
    check("existing output is preserved", states.get("occupied") == "失败" and occupied.read_bytes() == b"keep existing file")

    cancelled_target = out / "cancelled.mp4"
    cancelled_target.unlink(missing_ok=True)
    states = {}
    worker = ConversionWorker(ffmpeg, [(Job(media, id="cancel"), cancelled_target), (Job(media, id="pending"), out / "cancel-pending.mp4")], Options(width=3840, height=2160, video_codec="libx265", preset="veryslow", threads=1))
    worker.status.connect(lambda identity, state, detail: states.__setitem__(identity, state))
    worker.start()
    QTimer.singleShot(120, worker.cancel)
    wait_for(lambda: worker.isFinished())
    worker.wait()
    check("cancel terminates process and pending queue", states == {"cancel": "已取消", "pending": "已取消"} and not cancelled_target.exists())
    check("temporary files are cleaned", not list(out.glob("*.partial*")))
    check("no GUI error notifications", not notifications)
    window.close()
    (ARTIFACTS / "gui-report.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
