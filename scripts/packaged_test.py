"""Launch the frozen x64 app outside the project with a minimal system PATH."""
import json
import os
import subprocess
import tempfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    report = root / "test-artifacts" / "packaged-smoke.json"
    env = os.environ.copy()
    windows = os.environ.get("SYSTEMROOT", r"C:\Windows")
    env["PATH"] = str(Path(windows) / "System32") + ";" + windows
    for name in ["PYTHONPATH", "PYTHONHOME", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"]:
        env.pop(name, None)
    exe = root / "dist" / "FormatKae" / "FormatKae.exe"
    sample = root / "test-artifacts" / "中文 测试素材.mp4"
    result = subprocess.run([str(exe), "--smoke-test", str(report), "--probe", str(sample)], cwd=tempfile.gettempdir(), env=env, timeout=45)
    assert result.returncode == 0, result.returncode
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["success"] and data["window_visible"] and data["bits"] == 64
    assert str(root / "dist" / "FormatKae" / "ffmpeg") in data["ffmpeg"]
    assert data["conversion"]["audio"] == "mp3" and data["conversion"]["bytes"] > 0
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
