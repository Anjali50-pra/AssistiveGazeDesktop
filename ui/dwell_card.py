import threading
from PyQt6.QtWidgets import QPushButton, QSizePolicy
from PyQt6.QtCore import QTimer, pyqtSignal, QRectF, QPointF, Qt
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QFont, QFontMetrics
from ui import icons

try:
    import winsound
except ImportError:
    winsound = None

CONFIRM_MS = 450          # how long the "selected" flash is shown before the page changes
TEXT_COLOR = "#1E2A36"    # dark text: easy to read on the soft pastel cards
FONT_FAMILIES = ["Nirmala UI", "Segoe UI"]          # Nirmala UI covers Hindi and Telugu on Windows
FONT_FAMILY = '"Nirmala UI", "Segoe UI", sans-serif'
ICON_MAX_PX = 200         # biggest icon drawn on a card (bigger = easier to recognise by picture)


def _click_beep():
    """Short high 'tick' so the user HEARS that a card was selected."""
    if winsound is not None:
        threading.Thread(target=lambda: winsound.Beep(1500, 90), daemon=True).start()


class DwellCard(QPushButton):
    dwell_completed = pyqtSignal(str)

    def __init__(self, text, bg_color="#A8D5BA", dwell_time_ms=1300,
                 font_px=44, radius=24, icon=None, parent=None):
        super().__init__(text, parent)
        self.text_label = text
        self.bg_color = bg_color
        self.dwell_time_ms = dwell_time_ms
        self.font_px = font_px
        self.radius = radius
        self.icon_name = icon            # name from ui/icons.py, or None for a text-only card
        self._icon_cache = (None, None)  # (key, QPixmap)
        self._style_state = (False, False)
        self.dwell_progress = 0.0
        self.is_locked = False
        self.is_gaze_inside = False
        self.is_confirming = False

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._apply_style()

        self.clicked.connect(self._manual_click)

        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self._update_dwell)

    def set_icon(self, name):
        self.icon_name = name
        self._icon_cache = (None, None)
        self._apply_style(*self._style_state)
        self.update()

    def _apply_style(self, focused=False, confirmed=False):
        self._style_state = (focused, confirmed)
        if confirmed:
            border_color, border_width, bg = "#2E8B57", "10px", "#E3F3E8"
        elif focused:
            border_color, border_width, bg = "#4FD1E8", "6px", self.bg_color
        else:
            border_color, border_width, bg = "#2C3240", "2px", self.bg_color
        # with an icon the card draws its own text (below the icon), so the button's text is hidden
        text_color = "transparent" if self.icon_name else TEXT_COLOR
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {text_color};
                font-family: {FONT_FAMILY};
                font-size: {self.font_px}px;
                font-weight: bold;
                border-radius: {self.radius}px;
                border: {border_width} solid {border_color};
            }}
            QPushButton:pressed {{
                background-color: #CBD5E1;
            }}
        """)

    def set_locked(self, locked: bool):
        self.is_locked = locked
        if locked:
            self.reset_dwell()

    def start_dwell(self):
        if self.is_locked or self.is_confirming:
            return
        if not self.is_gaze_inside:
            self.is_gaze_inside = True
            self._apply_style(focused=True)
            self.timer.start()

    def reset_dwell(self):
        if self.is_confirming:          # a selection in progress must not be cancelled
            return
        if self.is_gaze_inside or self.dwell_progress > 0.0:
            self.is_gaze_inside = False
            self.timer.stop()
            self.dwell_progress = 0.0
            self._apply_style()
            self.update()

    def _manual_click(self):
        if not self.is_locked and not self.is_confirming:
            self.dwell_completed.emit(self.text_label)

    def _update_dwell(self):
        if self.is_locked or not self.is_gaze_inside:
            self.reset_dwell()
            return

        self.dwell_progress += 20 / self.dwell_time_ms
        if self.dwell_progress >= 1.0:
            # SELECTED: stop counting, flash green with a tick + beep, then proceed
            self.timer.stop()
            self.dwell_progress = 1.0
            self.is_confirming = True
            self.setText("✓  " + self.text_label)
            self._apply_style(confirmed=True)
            _click_beep()
            self.update()
            QTimer.singleShot(CONFIRM_MS, self._finish_confirm)
            return
        self.update()

    def _finish_confirm(self):
        self.is_confirming = False
        self.is_gaze_inside = False
        self.dwell_progress = 0.0
        self.setText(self.text_label)
        self._apply_style()
        self.dwell_completed.emit(self.text_label)

    # ------------------------------------------------------------------ drawing
    def _fit_font(self, text, max_w):
        font = QFont()
        font.setFamilies(FONT_FAMILIES)
        font.setBold(True)
        px = self.font_px
        while px > 18:
            font.setPixelSize(px)
            if QFontMetrics(font).horizontalAdvance(text) <= max_w:
                break
            px -= 2
        font.setPixelSize(px)
        return font

    def _icon_pixmap(self, bw, bh):
        dpr = self.devicePixelRatioF()
        key = (self.icon_name, round(bw), round(bh), dpr)
        if self._icon_cache[0] != key:
            self._icon_cache = (key, icons.icon_pixmap(self.icon_name, bw, bh, dpr))
        return self._icon_cache[1]

    def _paint_icon_and_text(self, p):
        """Icon above the label (or icon left of the label on wide, short cards).
        Returns the y position where the drawn block ends."""
        w, h = self.width(), self.height()
        text = self.text()
        aspect = icons.icon_aspect(self.icon_name)

        if w / max(h, 1) > 2.6:                                  # wide and short: icon | label
            font = self._fit_font(text, w * 0.55)
            fm = QFontMetrics(font)
            bh = min(h * 0.68, ICON_MAX_PX)
            bw = bh * aspect
            tw = fm.horizontalAdvance(text)
            left = (w - (bw + 22 + tw)) / 2
            p.drawPixmap(QPointF(left, (h - bh) / 2), self._icon_pixmap(bw, bh))
            p.setFont(font)
            p.setPen(QColor(TEXT_COLOR))
            p.drawText(QRectF(left + bw + 22, 0, tw + 12, h),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
            return h

        font = self._fit_font(text, w - 28)
        th = QFontMetrics(font).height()
        gap = 10 if h > 180 else 4
        bh = max(20.0, min(h - th - gap - 22, h * 0.54, ICON_MAX_PX))
        bw = bh * aspect
        if bw > w * 0.8:
            bw = w * 0.8
            bh = bw / aspect
        top = (h - (bh + gap + th)) / 2
        p.drawPixmap(QPointF((w - bw) / 2, top), self._icon_pixmap(bw, bh))
        p.setFont(font)
        p.setPen(QColor(TEXT_COLOR))
        p.drawText(QRectF(0, top + bh + gap, w, th), Qt.AlignmentFlag.AlignCenter, text)
        return top + bh + gap + th

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        block_bottom = None
        if self.icon_name:
            block_bottom = self._paint_icon_and_text(painter)

        if self.dwell_progress > 0.0 and not self.is_locked and not self.is_confirming:
            # soft darker fill that grows left -> right
            path = QPainterPath()
            path.addRoundedRect(QRectF(self.rect()), self.radius, self.radius)
            painter.setClipPath(path)
            painter.fillRect(QRectF(0, 0, self.width() * self.dwell_progress, self.height()),
                             QColor(30, 42, 54, 40))
            painter.setClipping(False)

            # progress ring (only on big cards, and only where it does not cover the drawing)
            if self.height() > 90:
                if block_bottom is None:
                    radius, cy = 26, self.height() - 54
                elif self.height() - block_bottom > 56:
                    radius, cy = 16, self.height() - 30
                else:
                    radius, cy = 0, 0
                if radius:
                    painter.setPen(QPen(QColor("#0E7490"), 8 if block_bottom is None else 6))
                    cx = self.width() / 2
                    rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
                    painter.drawArc(rect, 90 * 16, int(-self.dwell_progress * 360 * 16))
        painter.end()