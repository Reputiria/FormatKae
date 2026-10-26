"""Exercise theme persistence, card interactions and the real conversion feedback."""
import json
import os
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "test-artifacts"
ARTIFACTS.mkdir(exist_ok=True)
SETTINGS = tempfile.TemporaryDirectory(prefix="m3-settings-", dir=ARTIFACTS)
os.environ["APPDATA"] = SETTINGS.name
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QMimeData, QPoint, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QFontDatabase, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from formatkae.core import Media, Options, config_path, probe
from formatkae.theme import SCHEMES
from formatkae.window import MainWindow
from formatkae.workers import Job


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    # Qt's offscreen backend does not discover Windows system fonts automatically.
    for name in ("msyh.ttc", "segoeui.ttf", "seguisym.ttf"):
        path = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / name
        if path.exists():
            QFontDatabase.addApplicationFont(str(path))
    reports = []

    def check(name, condition):
        reports.append({"test": name, "success": bool(condition)})
        print(f"{'PASS' if condition else 'FAIL'} {name}", flush=True)
        if not condition:
            raise AssertionError(name)

    def wait_for(predicate, timeout=30):
        deadline = time.monotonic() + timeout
        while not predicate():
            app.processEvents()
            if time.monotonic() > deadline:
                raise TimeoutError("Timed out waiting for Qt")
            time.sleep(0.01)
        app.processEvents()

    window = MainWindow()
    notifications = []
    window.notify = lambda *args: notifications.append(args)
    window.show()
    app.processEvents()
    check("fresh settings start in light mode", window.theme_mode == "light")
    before = window.current_options()
    window.theme_button.click()
    check("theme switches without changing conversion options",
          window.theme_mode == "dark" and window.current_options() == before
          and app.palette().color(QPalette.ColorRole.Window).name().upper() == SCHEMES["dark"]["surface"].upper())
    check("theme is persisted immediately", json.loads(config_path().read_text(encoding="utf-8"))["theme"] == "dark")
    restored = MainWindow()
    check("new window restores saved theme", restored.theme_mode == "dark")
    restored.close()
    window.toggle_theme()
    window.grab().save(str(ARTIFACTS / "m3-light-empty.png"))

    for preset in window.preset_buttons:
        preset.click()
        check(f"preset chip {preset.property('presetKey')} selects exclusively",
              preset.isChecked() and sum(p.isChecked() for p in window.preset_buttons) == 1)
    window.quick_preset("balanced")
    window.quality.setValue(25)
    check("custom parameters clear preset selection", not any(p.isChecked() for p in window.preset_buttons))
    window.quick_preset("balanced")

    sample = ARTIFACTS / "中文 测试素材.mp4"
    if not sample.exists():
        raise RuntimeError("Run scripts/integration_test.py first")
    media = probe(window.ffprobe, str(sample))
    missing = Media(str(ARTIFACTS / "missing-ui.mp4"), duration=2, video="h264", audio="aac")
    window.jobs = [Job(media), Job(replace(media, path=str(ARTIFACTS / ("很长的文件名_" * 15 + ".mov"))), state="转换中", progress=42),
                   Job(missing, state="失败", error="无法读取源文件：文件已被移动或删除。请检查路径后重试。")]
    window._job_eta[window.jobs[1].id] = "预计剩余 00:18"
    window.refresh_table()
    app.processEvents()
    item, card = window._cards[window.jobs[0].id]
    QTest.mouseClick(card.filename, Qt.MouseButton.LeftButton)
    app.processEvents()
    check("clicking card text selects its queue item", item.isSelected() and card.property("selected"))
    failed_card = window._cards[window.jobs[2].id][1]
    check("failure reason and retry are visible inline",
          failed_card.error.isVisible() and "文件已被移动" in failed_card.error.text()
          and failed_card.action.isEnabled() and failed_card.action.accessibleName() == "重试转换")
    check("each running job shows progress and estimated time",
          window._cards[window.jobs[1].id][1].progress.value() == 42
          and "预计剩余" in window._cards[window.jobs[1].id][1].status.text())

    for mode in ("light", "dark"):
        window.set_theme(mode)
        app.processEvents()
        window.grab().save(str(ARTIFACTS / f"m3-{mode}-queue.png"))
        window.resize(1040, 800)
        app.processEvents()
        check(f"{mode} controls fit minimum window width",
              window.start_button.isVisible() and window.theme_button.isVisible()
              and window.centralWidget().rect().contains(window.start_button.mapTo(window.centralWidget(), window.start_button.rect().bottomRight()))
              and window.centralWidget().rect().contains(window.add_button.mapTo(window.centralWidget(), window.add_button.rect().bottomRight())))
        check(f"{mode} long filename card fits queue width",
              window._cards[window.jobs[1].id][1].width() <= window.table.viewport().width())
        window.grab().save(str(ARTIFACTS / f"m3-{mode}-compact.png"))
        window.open_advanced()
        QTest.qWait(280)
        check(f"{mode} advanced settings open as a bottom sheet", window.advanced_sheet.isVisible() and window.advanced_sheet.isModal())
        window.quality_slider.setValue(26)
        check(f"{mode} quality slider updates conversion settings", window.current_options().quality == 26)
        window.advanced_sheet.grab().save(str(ARTIFACTS / f"m3-{mode}-advanced.png"))
        window.advanced_sheet.reject()
        check(f"{mode} closing sheet retains edits", window.current_options().quality == 26)
        window.resize(1380, 960)

    local = QMimeData()
    local.setUrls([QUrl.fromLocalFile(str(sample))])
    enter = QDragEnterEvent(QPoint(100, 100), Qt.DropAction.CopyAction, local, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(window, enter)
    check("local drag highlights upload area", enter.isAccepted() and window.drop_area.property("dragging") and window.drop_title.text() == "松开以添加")
    window.grab().save(str(ARTIFACTS / "m3-dark-drag.png"))
    QApplication.sendEvent(window, QDragLeaveEvent())
    check("drag exit restores upload area", not window.drop_area.property("dragging"))
    remote = QMimeData()
    remote.setUrls([QUrl("https://example.com/video.mp4")])
    rejected = QDragEnterEvent(QPoint(100, 100), Qt.DropAction.CopyAction, remote, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(window, rejected)
    check("remote URLs are not accepted as local media", not rejected.isAccepted())

    window.jobs = [Job(missing), Job(media)]
    window.refresh_table()
    window.quick_preset("balanced")
    window.output_edit.setText(str(ARTIFACTS / "m3-output"))
    window.start_conversion()
    window.theme_button.click()
    check("theme can switch while converting", window.theme_mode == "light" and window._busy)
    wait_for(lambda: window.converter is None)
    check("failed file does not stop subsequent real conversion", window.jobs[0].state == "失败" and window.jobs[1].state == "已完成")
    check("completion uses a nonmodal snackbar and count", window.snackbar.isVisible() and window.completed_count.text() == "已完成 1 / 2" and not notifications)
    check("FFmpeg error is shown in failed card", bool(window._cards[window.jobs[0].id][1].error.text()))

    # Retry only the failed item; a separate pending job must remain untouched.
    window.jobs[0].media = media
    window.jobs.append(Job(media))
    window.refresh_table()
    window._cards[window.jobs[0].id][1].action.click()
    wait_for(lambda: window.converter is None)
    check("inline retry converts only the failed item", window.jobs[0].state == "已完成" and window.jobs[2].state == "等待转换")
    window.grab().save(str(ARTIFACTS / "m3-light-completed.png"))
    window.close()
    (ARTIFACTS / "m3-ui-report.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
