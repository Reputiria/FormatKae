"""Windows GUI entry point and packaged application smoke-test entry."""
import json
import os
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from formatkae.core import APP_NAME, VERSION, CREATE_NO_WINDOW, Options, build_command, config_path, find_tools, probe
from formatkae.theme import STYLE
from formatkae.window import MainWindow


def main():
    QApplication.setApplicationName(APP_NAME)
    QApplication.setOrganizationName(APP_NAME)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)

    def exception_hook(exc_type, value, tb):
        message = "".join(traceback.format_exception(exc_type, value, tb))
        if "--smoke-test" in sys.argv:
            report = Path(sys.argv[sys.argv.index("--smoke-test") + 1])
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps({"success": False, "error": message}, ensure_ascii=False, indent=2), encoding="utf-8")
            app.exit(1)
            return
        try:
            path = config_path().parent / "error.log"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(message, encoding="utf-8")
        except OSError:
            pass
        QMessageBox.critical(None, "FormatKae 错误", f"操作遇到错误：{value}\n详情已记录到 %APPDATA%\\FormatKae\\error.log。")

    sys.excepthook = exception_hook
    window = MainWindow()
    window.show()
    if "--smoke-test" in sys.argv:
        index = sys.argv.index("--smoke-test")
        report = Path(sys.argv[index + 1])

        def finish():
            ffmpeg, ffprobe = find_tools()
            report.parent.mkdir(parents=True, exist_ok=True)
            result = {"success": True, "app": APP_NAME, "version": VERSION, "platform": sys.platform, "bits": 64 if sys.maxsize > 2**32 else 32, "ffmpeg": str(ffmpeg), "ffprobe": str(ffprobe), "window_visible": window.isVisible(), "formats": window.format_combo.count()}
            result["theme"] = window.theme_mode
            if "--probe" in sys.argv:
                sample = sys.argv[sys.argv.index("--probe") + 1]
                media = probe(ffprobe, sample)
                result["probe"] = {"video": media.video, "audio": media.audio, "duration": media.duration}
                with tempfile.TemporaryDirectory(prefix="packaged-conversion-", dir=report.parent) as temp:
                    output = Path(temp) / "converted.mp3"
                    conversion = subprocess.run(build_command(ffmpeg, media, Options(format="mp3", audio_codec="libmp3lame"), output), capture_output=True, encoding="utf-8", errors="replace", creationflags=CREATE_NO_WINDOW, timeout=60)
                    if conversion.returncode:
                        raise RuntimeError(conversion.stderr)
                    converted = probe(ffprobe, str(output))
                    result["conversion"] = {"audio": converted.audio, "video": converted.video, "bytes": converted.size, "duration": converted.duration}
            result["screenshot"] = str(report.with_suffix(".png"))
            window.grab().save(str(report.with_suffix(".png")))
            report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            app.quit()

        QTimer.singleShot(1300, finish)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
