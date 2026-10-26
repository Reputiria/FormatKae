"""Launch the frozen x64 app outside the project with a minimal system PATH."""
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", default="dist")
    parser.add_argument("--report", default="test-artifacts/packaged-smoke.json")
    args = parser.parse_args()
    report = (root / args.report).resolve()
    dist = (root / args.dist_dir).resolve()
    env = os.environ.copy()
    windows = os.environ.get("SYSTEMROOT", r"C:\Windows")
    env["PATH"] = str(Path(windows) / "System32") + ";" + windows
    for name in ["PYTHONPATH", "PYTHONHOME", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"]:
        env.pop(name, None)
    exe = dist / "FormatKae" / "FormatKae.exe"
    sample = root / "test-artifacts" / "中文 测试素材.mp4"
    report.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="packaged-settings-", dir=report.parent) as settings:
        env["APPDATA"] = settings
        config = Path(settings) / "FormatKae" / "settings.json"
        config.parent.mkdir()
        for theme in ("light", "dark"):
            config.write_text(json.dumps({"theme": theme}), encoding="utf-8")
            target = report if theme == "light" else report.with_stem(report.stem + "-dark")
            result = subprocess.run([str(exe), "--smoke-test", str(target), "--probe", str(sample)], cwd=tempfile.gettempdir(), env=env, timeout=45)
            assert result.returncode == 0, result.returncode
            data = json.loads(target.read_text(encoding="utf-8"))
            assert data["success"] and data["window_visible"] and data["bits"] == 64
            assert data["theme"] == theme
            assert str(dist / "FormatKae" / "ffmpeg") in data["ffmpeg"]
            assert data["conversion"]["audio"] == "mp3" and data["conversion"]["bytes"] > 0
            print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
