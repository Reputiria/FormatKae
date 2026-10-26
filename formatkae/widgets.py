"""Small desktop components using the shared Material 3 theme."""
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, QRectF, QPointF, Qt
from PySide6.QtGui import QIcon, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout,
)

from .core import format_size, format_time


def material_icon(name, color):
    """Draw small vector icons so their availability does not depend on fonts."""
    pixmap = QPixmap(40, 40)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(2, 2)
    painter.setPen(QPen(color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))

    def line(x1, y1, x2, y2):
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    if name == "play":
        path = QPainterPath(QPointF(6, 3))
        path.lineTo(16, 10)
        path.lineTo(6, 17)
        path.closeSubpath()
        painter.drawPath(path)
    elif name == "sun":
        painter.drawEllipse(QRectF(6, 6, 8, 8))
        for points in [(10, 1, 10, 3), (10, 17, 10, 19), (1, 10, 3, 10), (17, 10, 19, 10),
                       (3.5, 3.5, 5, 5), (15, 15, 16.5, 16.5), (3.5, 16.5, 5, 15), (15, 5, 16.5, 3.5)]:
            line(*points)
    elif name == "moon":
        path = QPainterPath(QPointF(17, 12))
        path.cubicTo(10, 15, 5, 9, 8, 3)
        path.cubicTo(-1, 5, 2, 20, 12, 17)
        path.cubicTo(14, 16, 16, 14, 17, 12)
        painter.drawPath(path)
    elif name == "tune":
        for y, x in [(5, 7), (10, 13), (15, 9)]:
            line(2, y, x - 2, y)
            line(x + 2, y, 18, y)
            painter.drawEllipse(QRectF(x - 2, y - 2, 4, 4))
    elif name == "queue":
        for y in (5, 10, 15):
            line(3, y, 5, y)
            line(9, y, 17, y)
    elif name == "log":
        painter.drawRoundedRect(QRectF(3, 2, 14, 16), 2, 2)
        for y in (6, 10, 14):
            line(7, y, 13, y)
    painter.end()
    return QIcon(pixmap)


def restyle(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class MaterialComboBox(QComboBox):
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self.palette().color(QPalette.ColorRole.Text), 1.5,
                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        x, y = self.width() - 16, self.height() / 2
        painter.drawLine(QPointF(x - 4, y - 2), QPointF(x, y + 2))
        painter.drawLine(QPointF(x, y + 2), QPointF(x + 4, y - 2))
        painter.end()


class ElidedLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.full_text = text
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setToolTip(text)

    def set_full_text(self, text):
        self.full_text = text
        self.setToolTip(text)
        self.update_text()

    def setText(self, text):
        self.set_full_text(text)

    def update_text(self):
        super().setText(self.fontMetrics().elidedText(self.full_text, Qt.TextElideMode.ElideMiddle, self.width()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_text()


class JobCard(QFrame):
    def __init__(self, job, action, parent=None):
        super().__init__(parent)
        self.setObjectName("jobCard")
        self.setProperty("selected", False)
        self.setProperty("failed", False)
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 12, 12, 12)
        row.setSpacing(16)
        self.icon = QLabel("▷" if job.media.video else "♪")
        self.icon.setObjectName("mediaIcon")
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setFixedSize(44, 44)
        row.addWidget(self.icon)
        content = QVBoxLayout()
        content.setSpacing(5)
        self.filename = ElidedLabel()
        self.filename.setTextFormat(Qt.TextFormat.PlainText)
        content.addWidget(self.filename)
        self.info = ElidedLabel()
        self.info.setObjectName("caption")
        content.addWidget(self.info)
        self.status = QLabel()
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setObjectName("caption")
        content.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        content.addWidget(self.progress)
        self.error = QLabel()
        self.error.setTextFormat(Qt.TextFormat.PlainText)
        self.error.setObjectName("muted")
        self.error.setWordWrap(True)
        self.error.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.error.setMaximumHeight(54)
        content.addWidget(self.error)
        row.addLayout(content, 1)
        self.action = QPushButton("×")
        self.action.setObjectName("remove")
        self.action.setFixedSize(40, 40)
        self.action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action.clicked.connect(action)
        row.addWidget(self.action, 0, Qt.AlignmentFlag.AlignVCenter)

    def update_job(self, job, target, busy, remaining=""):
        from pathlib import Path
        self.filename.set_full_text(Path(job.media.path).name)
        self.filename.setToolTip(job.media.path)
        source = Path(job.media.path).suffix.lstrip(".").upper() or "媒体"
        self.info.set_full_text(f"{source} → {target.upper()}   ·   {format_time(job.media.duration)}   ·   {format_size(job.media.size)}")
        self.progress.setValue(job.progress)
        self.progress.setVisible(job.state == "转换中")
        self.status.setText(f"转换中  {job.progress}%  ·  {remaining or '正在估算剩余时间…'}" if job.state == "转换中" else job.state)
        failed = job.state == "失败"
        if self.property("failed") != failed:
            self.setProperty("failed", failed)
            restyle(self)
        # Show the final diagnostic lines directly; the full message stays accessible.
        lines = [line for line in job.error.splitlines() if line.strip()]
        self.error.setText("\n".join(lines[-2:])[-360:])
        self.error.setToolTip(job.error)
        self.error.setVisible(failed)
        self.action.setText("↻" if failed else "×")
        self.action.setObjectName("icon" if failed else "remove")
        self.action.setToolTip("重新转换此文件" if failed else ("转换期间请使用下方「取消转换」" if busy else "移除此文件"))
        self.action.setAccessibleName("重试转换" if failed else "移除文件")
        self.action.setEnabled(not busy)
        restyle(self.action)


class BottomSheet(QDialog):
    """Window-modal sheet with a short spring response on entry."""
    def __init__(self, parent):
        super().__init__(parent, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("高级转换设置")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        frame = QFrame()
        frame.setObjectName("sheet")
        layout.addWidget(frame)
        self.content = QVBoxLayout(frame)
        self.content.setContentsMargins(24, 16, 24, 20)
        heading = QHBoxLayout()
        title = QLabel("高级转换设置")
        title.setObjectName("heading")
        heading.addWidget(title)
        heading.addStretch()
        close = QPushButton("完成")
        close.setToolTip("设置实时应用，关闭后保留当前参数")
        close.clicked.connect(self.accept)
        heading.addWidget(close)
        self.content.addLayout(heading)
        note = QLabel("参数对本批次所有文件生效；关闭面板即可保留设置。")
        note.setObjectName("muted")
        self.content.addWidget(note)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content.addWidget(self.scroll)
        self.motion = QPropertyAnimation(self, b"geometry", self)
        self.motion.setDuration(240)
        curve = QEasingCurve(QEasingCurve.Type.OutBack)
        curve.setOvershoot(0.35)
        self.motion.setEasingCurve(curve)

    def open_at_bottom(self):
        owner = self.parentWidget()
        area = owner.centralWidget()
        origin = area.mapToGlobal(area.rect().topLeft())
        width = min(960, area.width() - 40)
        height = min(650, area.height() - 32)
        target = QRect(origin.x() + (area.width() - width) // 2,
                       origin.y() + area.height() - height, width, height)
        self.setGeometry(target)
        self.show()
        self.motion.stop()
        self.motion.setStartValue(target.translated(0, 48))
        self.motion.setEndValue(target)
        self.motion.start()
        self.raise_()
        self.activateWindow()

    def done(self, result):
        self.motion.stop()
        super().done(result)
