import math
import time
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QGridLayout, QVBoxLayout,
    QHBoxLayout, QLabel, QStackedWidget, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, QPoint, QRect, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QImage, QPixmap
from ui.dwell_card import DwellCard
from nlp.speech_engine import SpeechEngine
from audio.voice import VoiceOutput

THEME = {
    "bg_window": "#14161D",
    "output_bg": "#E8F4F8",
    "output_text": "#0F4C5C",
    "card_category": "#2A7B4C",
    "card_action": "#7A4A3B",
    "card_urgent": "#8E2828",
    "card_binary": "#3D4450",
    "card_sub": "#265FB2",
    "card_next": "#5B4B8A",
    "card_back": "#8C3030",
}

DWELL_MS = 1300          # time you must look at a card to select it
SNAP_MAX_PX = 220        # gaze farther than this from every card = nothing selected
HYSTERESIS_PX = 45       # a new card must be this much closer to steal the highlight
LOST_GAZE_S = 0.6        # no tracking update for this long -> cancel any dwell
SHOW_POINTER = True      # False = hide the floating dot; only the highlighted card shows the gaze

SUB_ITEMS = {
    "खाना": ["दाल रोटी", "चावल सब्ज़ी", "नाश्ता", "बिस्कुट", "दाल भात", "कुछ और"],
    "जाना है": ["कमरे में", "वॉशरूम", "बिस्तर पर", "घर", "बाहर", "अस्पताल", "बगीचे में"],
    "दर्द": ["सर में", "पेट में", "छाती में", "हाथ में", "पैरों में", "पीठ में", "कहीं"],
}
ITEM_SLOTS = [(0, 0), (0, 1), (0, 2), (1, 0)]   # 4 items per page; (1,1)=NEXT, (1,2)=BACK
BACK_TEXT = "वापस"
NEXT_TEXT = "अगला ›"
YESNO_TEXT = "हाँ / नहीं"


class GazePointerOverlay(QWidget):
    """Small always-on-top pointer that glides (no jumping) to the gaze point."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(60, 60)
        self._tx = self._ty = self._x = self._y = 0.0
        self._glide = QTimer(self)
        self._glide.setInterval(16)
        self._glide.timeout.connect(self._step)
        self._glide.start()
        self.show()

    def move_to_gaze(self, global_pt: QPoint):
        self._tx, self._ty = float(global_pt.x()), float(global_pt.y())

    def _step(self):
        self._x += (self._tx - self._x) * 0.22
        self._y += (self._ty - self._y) * 0.22
        self.move(int(self._x - 30), int(self._y - 30))
        self.raise_()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(255, 255, 255, 230), 3))
        painter.setBrush(QColor(0, 170, 255, 150))
        painter.drawEllipse(14, 14, 32, 32)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 255, 200, 255))
        painter.drawEllipse(25, 25, 10, 10)


class AACMainWindow(QMainWindow):
    recalibrate_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AAC Assistive Gaze Interface")
        self.showFullScreen()

        self.speech_engine = SpeechEngine()
        self.voice = VoiceOutput()
        self.active_category = None
        self.cards = []
        self.active_card = None
        self.sub_page = 0
        self.prev_view = ("main",)     # where BACK on the output screen returns to
        self.page_locked = False
        self.auto_return_timer = None
        self._last_gaze_t = time.monotonic()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.root_layout = QVBoxLayout(self.central_widget)
        self.root_layout.setContentsMargins(40, 20, 40, 20)
        self.central_widget.setStyleSheet(f"background-color: {THEME['bg_window']};")

        # cards sit in the middle ~76% of the screen: smaller eye angles = better accuracy
        screen_w = QApplication.primaryScreen().geometry().width()
        pad = max(0, int(screen_w * 0.12) - 40)

        # Header with camera preview
        self.header_layout = QHBoxLayout()
        self.header_title = QLabel("AAC Assistive Gaze Interface")
        self.header_title.setStyleSheet("color: #78909C; font-size: 18px; font-weight: bold;")
        self.header_layout.addWidget(self.header_title)
        self.header_layout.addStretch()

        self.cam_preview = QLabel("Camera Loading...")
        self.cam_preview.setFixedSize(140, 95)
        self.cam_preview.setStyleSheet("border: 2px solid #00E5FF; background-color: #000; color: #FFF;")
        self.cam_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_layout.addWidget(self.cam_preview)
        self.root_layout.addLayout(self.header_layout)

        self.stacked_widget = QStackedWidget()
        self.root_layout.addWidget(self.stacked_widget, stretch=1)

        # ---------------- Page 0: Main Menu (3 x 2) ----------------
        self.main_menu_page = QWidget()
        self.main_menu_layout = QVBoxLayout(self.main_menu_page)
        self.main_menu_layout.setContentsMargins(pad, 0, pad, 0)
        self.main_grid_container = QWidget()
        self.main_grid = QGridLayout(self.main_grid_container)
        self.main_grid.setSpacing(30)
        for r in range(2):
            self.main_grid.setRowStretch(r, 1)
        for c in range(3):
            self.main_grid.setColumnStretch(c, 1)
        self.main_menu_layout.addWidget(self.main_grid_container, stretch=1)

        # ---------------- Page 1: Sub-Menu (3 x 2) ----------------
        self.sub_menu_page = QWidget()
        self.sub_menu_layout = QVBoxLayout(self.sub_menu_page)
        self.sub_menu_layout.setContentsMargins(pad, 0, pad, 0)
        self.sub_grid_container = QWidget()
        self.sub_grid = QGridLayout(self.sub_grid_container)
        self.sub_grid.setSpacing(30)
        for r in range(2):
            self.sub_grid.setRowStretch(r, 1)
        for c in range(3):
            self.sub_grid.setColumnStretch(c, 1)
        self.sub_menu_layout.addWidget(self.sub_grid_container, stretch=1)

        # ---------------- Page 2: Output ----------------
        self.output_page = QWidget()
        self.output_layout = QVBoxLayout(self.output_page)
        self.output_layout.setContentsMargins(50, 40, 50, 40)

        self.output_label = QLabel("")
        self.output_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.output_label.setWordWrap(True)
        self.output_label.setStyleSheet(f"""
            background-color: {THEME['output_bg']};
            color: {THEME['output_text']};
            font-size: 58px;
            font-weight: bold;
            border-radius: 20px;
            padding: 30px;
        """)
        self.output_layout.addWidget(self.output_label, stretch=2)

        self.output_back_btn = DwellCard("वापस (BACK)", bg_color=THEME["card_back"], dwell_time_ms=DWELL_MS)
        self.output_back_btn.setMinimumHeight(120)
        self.output_back_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.output_back_btn.dwell_completed.connect(lambda *_: self.go_back_from_output())
        self.output_layout.addWidget(self.output_back_btn, stretch=1)

        self.stacked_widget.addWidget(self.main_menu_page)
        self.stacked_widget.addWidget(self.sub_menu_page)
        self.stacked_widget.addWidget(self.output_page)

        self.cursor_overlay = GazePointerOverlay() if SHOW_POINTER else None

        # safety: if tracking stops (face lost), never let a dwell finish by itself
        self.watchdog = QTimer(self)
        self.watchdog.setInterval(250)
        self.watchdog.timeout.connect(self._check_gaze_alive)
        self.watchdog.start()

        self.render_main_menu()

    # ------------------------------------------------------------------ basics
    def closeEvent(self, event):
        if hasattr(self, 'cursor_overlay') and self.cursor_overlay:
            self.cursor_overlay.close()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() in (Qt.Key.Key_C, Qt.Key.Key_F5):
            self.trigger_recalibration()
        elif event.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()

    def lock_page_briefly(self):
        """Short pause after a page change so the eyes can settle."""
        self.page_locked = True
        self._set_active_card(None)
        for card in self.cards:
            card.set_locked(True)

        def unlock():
            self.page_locked = False
            for card in self.cards:
                card.set_locked(False)

        QTimer.singleShot(900, unlock)

    def clear_active_cards(self):
        for card in self.cards:
            card.reset_dwell()
        self.cards.clear()
        self.active_card = None

    def _make_card(self, text, color, grid, r, c, handler, rowspan=1, colspan=1):
        card = DwellCard(text, bg_color=color, dwell_time_ms=DWELL_MS)
        card.dwell_completed.connect(handler)
        grid.addWidget(card, r, c, rowspan, colspan)
        self.cards.append(card)
        return card

    @staticmethod
    def _clear_grid(grid):
        while grid.count():
            w = grid.takeAt(0).widget()
            if w:
                w.deleteLater()

    def trigger_recalibration(self):
        """Caretaker presses C (or F5): stop any voice and run the calibration screen."""
        self.voice.stop()
        self.recalibrate_requested.emit()

    # ------------------------------------------------------------------- pages
    def render_main_menu(self, *_):
        if self.auto_return_timer:
            self.auto_return_timer.stop()
            self.auto_return_timer = None

        self.clear_active_cards()
        self.active_category = None
        self.stacked_widget.setCurrentIndex(0)
        self._clear_grid(self.main_grid)

        items = [
            ("खाना", THEME["card_category"], 0, 0),
            ("पानी", THEME["card_category"], 0, 1),
            ("जाना है", THEME["card_category"], 0, 2),
            ("दर्द", THEME["card_urgent"], 1, 0),
            ("मदद", THEME["card_action"], 1, 1),
            (YESNO_TEXT, THEME["card_binary"], 1, 2),
        ]
        for text, color, r, c in items:
            self._make_card(text, color, self.main_grid, r, c, self.handle_main_card_selection)

        self.lock_page_briefly()

    def render_sub_menu(self, category: str, page: int = 0):
        self.clear_active_cards()
        self.active_category = category
        self.stacked_widget.setCurrentIndex(1)
        self._clear_grid(self.sub_grid)

        items = SUB_ITEMS.get(category, [])
        per_page = len(ITEM_SLOTS)
        n_pages = max(1, math.ceil(len(items) / per_page))
        page %= n_pages
        self.sub_page = page
        chunk = items[page * per_page:(page + 1) * per_page]

        for text, (r, c) in zip(chunk, ITEM_SLOTS):
            self._make_card(text, THEME["card_sub"], self.sub_grid, r, c, self.handle_sub_card_selection)
        if n_pages > 1:
            self._make_card(NEXT_TEXT, THEME["card_next"], self.sub_grid, 1, 1,
                            lambda *_: self.render_sub_menu(category, page + 1))
        self._make_card(BACK_TEXT, THEME["card_back"], self.sub_grid, 1, 2,
                        lambda *_: self.render_main_menu())
        self.lock_page_briefly()

    def render_yes_no(self):
        """Two huge cards + BACK: easiest screen to hit."""
        self.clear_active_cards()
        self.active_category = None
        self.stacked_widget.setCurrentIndex(1)
        self._clear_grid(self.sub_grid)
        self._make_card("हाँ", "#2A7B4C", self.sub_grid, 0, 0, self.handle_yesno_selection, 2, 1)
        self._make_card("नहीं", "#8E2828", self.sub_grid, 0, 1, self.handle_yesno_selection, 2, 1)
        self._make_card(BACK_TEXT, THEME["card_back"], self.sub_grid, 0, 2,
                        lambda *_: self.render_main_menu(), 2, 1)
        self.lock_page_briefly()

    # ---------------------------------------------------------------- handlers
    def handle_main_card_selection(self, label: str):
        if label in ("खाना", "जाना है", "दर्द"):
            self.render_sub_menu(label)
        elif label in ("पानी", "मदद"):
            self.prev_view = ("main",)
            self.show_final_output(self.speech_engine.build_sov_sentence(label, ""))
        elif label == YESNO_TEXT:
            self.render_yes_no()

    def handle_yesno_selection(self, label: str):
        self.prev_view = ("yesno",)
        self.show_final_output(label)

    def handle_sub_card_selection(self, label: str):
        sentence = self.speech_engine.build_sov_sentence(self.active_category, label)
        self.prev_view = ("sub", self.active_category, self.sub_page)
        self.show_final_output(sentence)

    def show_final_output(self, sentence: str, speak: bool = True):
        self.clear_active_cards()
        self.output_label.setText(sentence)
        self.stacked_widget.setCurrentIndex(2)

        self.cards.append(self.output_back_btn)
        self.output_back_btn.reset_dwell()

        if speak:
            QTimer.singleShot(200, lambda: self.voice.speak(sentence))

        if self.auto_return_timer:
            self.auto_return_timer.stop()
        self.auto_return_timer = QTimer(self)
        self.auto_return_timer.setSingleShot(True)
        self.auto_return_timer.setInterval(8000)
        self.auto_return_timer.timeout.connect(self.render_main_menu)
        self.auto_return_timer.start()

        self.lock_page_briefly()

    def go_back_from_output(self):
        """BACK on the sentence screen: silence the voice at once and return to the
        menu the sentence came from, so a wrong choice is fixed in ONE step."""
        self.voice.stop()
        if self.auto_return_timer:
            self.auto_return_timer.stop()
        view = self.prev_view
        if view[0] == "sub":
            self.render_sub_menu(view[1], view[2])
        elif view[0] == "yesno":
            self.render_yes_no()
        else:
            self.render_main_menu()

    # ------------------------------------------------------------ camera/gaze
    def update_camera_preview(self, cv_img):
        if cv_img is None:
            return
        h, w, ch = cv_img.shape
        qt_img = QImage(cv_img.data, w, h, ch * w, QImage.Format.Format_BGR888)
        pixmap = QPixmap.fromImage(qt_img).scaled(
            self.cam_preview.width(), self.cam_preview.height(),
            Qt.AspectRatioMode.KeepAspectRatio
        )
        self.cam_preview.setPixmap(pixmap)

    def _card_distance(self, card, pt: QPoint) -> float:
        """0 if the gaze is inside the card, else distance (px) to its nearest edge."""
        r = QRect(card.mapToGlobal(QPoint(0, 0)), card.size())
        dx = max(r.left() - pt.x(), 0, pt.x() - r.right())
        dy = max(r.top() - pt.y(), 0, pt.y() - r.bottom())
        return math.hypot(dx, dy)

    def _set_active_card(self, card):
        self.active_card = card
        for c in self.cards:
            if c is card:
                c.start_dwell()
            else:
                c.reset_dwell()

    def _check_gaze_alive(self):
        if time.monotonic() - self._last_gaze_t > LOST_GAZE_S and self.active_card is not None:
            self._set_active_card(None)

    def update_gaze_point(self, screen_x: int, screen_y: int, is_blinking: bool):
        self._last_gaze_t = time.monotonic()
        pt = QPoint(int(screen_x), int(screen_y))
        if self.cursor_overlay is not None:
            self.cursor_overlay.move_to_gaze(pt)

        if self.page_locked:
            self._set_active_card(None)
            return
        if is_blinking:        # a normal blink must not cancel the selection
            return
        if not self.cards:
            return
        if self.active_card not in self.cards:
            self.active_card = None

        # nearest card to the gaze point
        best_card, best_d = min(((c, self._card_distance(c, pt)) for c in self.cards),
                                key=lambda t: t[1])
        if best_d > SNAP_MAX_PX:
            if self.active_card is not None:
                self._set_active_card(None)
            return

        if self.active_card is None:
            self._set_active_card(best_card)
        elif best_card is not self.active_card:
            cur_d = self._card_distance(self.active_card, pt)
            # switch only if the new card is CLEARLY closer (hysteresis = no flicker)
            if best_d + HYSTERESIS_PX < cur_d:
                self._set_active_card(best_card)