"""Real FFmpeg conversion tests against all shipped format defaults."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from formatkae.core import CREATE_NO_WINDOW, FORMATS, Options, build_command, find_tools, probe


def run():
    root = Path(__file__).resolve().parents[1] / "test-artifacts"
    root.mkdir(exist_ok=True)
    ffmpeg, ffprobe = find_tools()
    sample = root / "中文 测试素材.mp4"
    result = subprocess.run([str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=24:duration=2", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(sample)], capture_output=True, creationflags=CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    media = probe(ffprobe, str(sample))
    reports = []
    for fmt in FORMATS:
        target = root / f"output-{fmt.ext}.{fmt.ext}"
        target.unlink(missing_ok=True)
        opt = Options(format=fmt.ext, video_codec=fmt.video or "libx264", audio_codec=fmt.audio or "aac")
        if fmt.ext == "opus":
            opt.sample_rate = "48000"
        result = subprocess.run(build_command(ffmpeg, media, opt, target), capture_output=True, encoding="utf-8", errors="replace", creationflags=CREATE_NO_WINDOW, timeout=90)
        if result.returncode:
            reports.append({"format": fmt.ext, "success": False, "error": result.stderr[-4000:]})
            print(f"FAIL {fmt.ext}: {result.stderr[-700:]}")
        else:
            inspected = probe(ffprobe, str(target))
            success = target.stat().st_size > 0 and (bool(inspected.video) if fmt.kind in {"video", "gif", "custom"} else bool(inspected.audio) and not inspected.video)
            reports.append({"format": fmt.ext, "success": success, "video": inspected.video, "audio": inspected.audio, "duration": inspected.duration})
            print(f"{'PASS' if success else 'FAIL'} {fmt.ext}: {inspected.video} / {inspected.audio}")
    target = root / "裁剪 缩放.mp4"
    target.unlink(missing_ok=True)
    result = subprocess.run(build_command(ffmpeg, media, Options(width=160, fps="15", start="0.5", end="1.5", volume=50, sample_rate="48000", channels="1"), target), capture_output=True, creationflags=CREATE_NO_WINDOW)
    cropped = probe(ffprobe, str(target)) if not result.returncode else None
    success = bool(cropped and cropped.width == 160 and cropped.height == 90 and cropped.channels == 1 and cropped.sample_rate == "48000" and abs(cropped.duration - 1) < 0.2)
    reports.append({"format": "crop-scale-audio", "success": success})
    print(f"{'PASS' if success else 'FAIL'} crop-scale-audio")
    (root / "integration-report.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if all(r["success"] for r in reports) else 1


if __name__ == "__main__":
    sys.exit(run())
