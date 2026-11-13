"""Full-screen calibration: 12 dots (each of the 6 card positions twice),
then shows the measured accuracy for a few seconds."""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont
from core.eye_tracker import CALIB_GRID

DOT_MS = 1600        # time per dot
RESULT_MS = 3500     # how long the accuracy result stays on screen


class CalibrationOverlay(QWidget):
    finished = pyqtSignal(object)   # accuracy 0..1, or None if failed

    def __init__(self, tracker, sw, sh):
        super().__init__()
        self.tracker, self.sw, self.sh = tracker, sw, sh
        self.idx = -1
        self.result_text = ""
        self.result_color = "#94a3b8"
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("background:#0b1220;")
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._next)

    def start(self):
        self.tracker.recalibrate()
        self.idx = -1
        self.result_text = ""
        self.showFullScreen()
        self.update()
        QTimer.singleShot(1800, self._next)   # time to get ready

    def _next(self):
        self.tracker.hide_dot()
        self.idx += 1
        if self.idx >= len(CALIB_GRID):
            acc = self.tracker.finish_calibration(self.sw, self.sh)
            if acc is None:
                self.result_text = self.tracker.report_text + "\nPress C to try again."
                self.result_color = "#f87171"
            else:
                hint = ""
                if acc < 0.6:
                    hint = "\nLow accuracy: face a light, sit 50-60 cm away, keep your head still,\nthen press C to calibrate again."
                    self.result_color = "#fbbf24"
                else:
                    self.result_color = "#4ade80"
                self.result_text = self.tracker.report_text + hint
            self._acc = acc
            self.update()
            QTimer.singleShot(RESULT_MS, self._close_and_emit)
            return
        self.tracker.show_dot(self.idx, self.sw, self.sh)
        self.update()
        self.timer.start(DOT_MS)

    def _close_and_emit(self):
        self.close()
        self.finished.emit(getattr(self, "_acc", None))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setFont(QFont("Arial", 18))
        p.setPen(QColor("#94a3b8"))
        if self.idx < 0:
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Sit comfortably, facing the light. Keep your head still.\n"
                       "Follow each dot with your EYES only - look at its centre.")
            return
        if self.idx >= len(CALIB_GRID):
            p.setPen(QColor(self.result_color))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.result_text)
            return
        fx, fy = CALIB_GRID[self.idx]
        cx, cy = int(fx * self.width()), int(fy * self.height())
        p.setBrush(QColor("#22d3ee"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(cx - 18, cy - 18, 36, 36)
        p.setBrush(QColor("#0b1220"))
        p.drawEllipse(cx - 5, cy - 5, 10, 10)