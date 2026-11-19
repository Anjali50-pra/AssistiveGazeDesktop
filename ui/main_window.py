import os
import threading
import math
import time
from functools import partial
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QGridLayout, QVBoxLayout,
    QHBoxLayout, QLabel, QStackedWidget, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, QPoint, QRect, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QImage, QPixmap, QShortcut, QKeySequence
from ui.dwell_card import DwellCard, FONT_FAMILY
from nlp.languages import LANG_CODES, menu_cards, sub_items, build_sentence, ui, native_name
from nlp.voice_player import VoicePlayer

# ------------------------------------------------------------------ theme (dark, easy on the eyes)
THEME = {
    "bg_window": "#14161D",
    "output_bg": "#D5E3EA",
    "output_text": "#0F3D4A",
}


def _dim(hex_color, factor):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#{:02X}{:02X}{:02X}".format(int(r * factor), int(g * factor), int(b * factor))


CARD_DIM = 0.92        # lower this (0.85, 0.80) if the cards still look too bright
_PASTELS = ["#A9C7E8", "#A8D5BA", "#F0C3A3", "#C5B8E3",
            "#EBDDA0", "#EBB5C3", "#9FD6D6", "#D3C1B0"]
CARD_COLORS = [_dim(c, CARD_DIM) for c in _PASTELS]   # blue, mint, peach, lavender, butter, rose, aqua, sand
BACK_COLOR = _dim("#B8C0CC", CARD_DIM)                # soft grey, used for every BACK button

DWELL_MS = 1300          # time you must look at a card to select it
SNAP_MAX_PX = 220        # gaze farther than this from every card = nothing selected
HYSTERESIS_PX = 45       # a new card must be this much closer to steal the highlight
LOST_GAZE_S = 0.6        # no tracking update for this long -> cancel any dwell
SHOW_POINTER = True      # False = hide the floating dot; only the highlighted card shows the gaze

ITEM_SLOTS = [(0, 0), (0, 1), (0, 2), (1, 0)]   # 4 items per page; (1,1)=NEXT, (1,2)=BACK
TITLE = "AAC Assistive Gaze Interface"
LANG_CARD_DWELL_MS = 1800                      # the 'Language' cards need a slightly longer look (no accidents)
SENTENCE_BACK_HAS_LANGUAGE = True              # False = BACK on the sentence screen goes back in ONE step


MAIN_ICONS = {"eat": "food", "water": "water", "go": "walk",
              "pain": "pain_face", "help": "help_ring", "yesno": "yes_no_lang"}


def _font_px(text):
    """Longer words get a smaller font so they fit on the card (Telugu words are long)."""
    n = len(text)
    return 44 if n <= 8 else (36 if n <= 12 else 30)


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
        self.setWindowTitle(TITLE)
        self.showFullScreen()

        self.lang = None                 # chosen on the first page
        self.voice = VoicePlayer("en")
        self.active_category = None      # 'eat' | 'go' | 'pain'
        self.cards = []
        self._lang_origin = ("main",)    # where 'Back' on the language page returns to
        self.active_card = None
        self.sub_page = 0
        self.prev_view = ("main",)       # where BACK on the output screen returns to
        self.page_locked = False
        self.auto_return_timer = None
        self._last_gaze_t = time.monotonic()
        self.calibrating = False         # True while the calibration screen is running
        self._skip_card = None           # card you were already looking at when a page unlocked
        self._skip_pending = False

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
        self.header_title = QLabel(TITLE)
        self.header_title.setStyleSheet(
            f"color: #78909C; font-family: {FONT_FAMILY}; font-size: 18px; font-weight: bold;")
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
            font-family: {FONT_FAMILY};
            font-size: 58px;
            font-weight: bold;
            border-radius: 20px;
            padding: 30px;
        """)
        self.output_layout.addWidget(self.output_label, stretch=2)

        self.output_back_btn = DwellCard("BACK", bg_color=BACK_COLOR, dwell_time_ms=DWELL_MS,
                                         icon="back_lang")
        self.output_back_btn.setMinimumHeight(120)
        self.output_back_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.output_back_btn.dwell_completed.connect(lambda *_: self.on_output_back())
        self.output_layout.addWidget(self.output_back_btn, stretch=1)

        # ---------------- Page 3: Language selection ----------------
        self.lang_page = QWidget()
        self.lang_layout = QVBoxLayout(self.lang_page)
        self.lang_layout.setContentsMargins(pad, 0, pad, 0)
        self.lang_title = QLabel("")
        self.lang_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lang_title.setStyleSheet(
            f"color: #B0BEC5; font-family: {FONT_FAMILY}; font-size: 34px; font-weight: bold; padding: 10px;")
        self.lang_layout.addWidget(self.lang_title)
        self.lang_grid_container = QWidget()
        self.lang_grid = QGridLayout(self.lang_grid_container)
        self.lang_grid.setSpacing(30)
        self.lang_grid.setRowStretch(0, 1)
        for c in range(len(LANG_CODES)):
            self.lang_grid.setColumnStretch(c, 1)
        self.lang_layout.addWidget(self.lang_grid_container, stretch=1)

        self.stacked_widget.addWidget(self.main_menu_page)   # index 0
        self.stacked_widget.addWidget(self.sub_menu_page)    # index 1
        self.stacked_widget.addWidget(self.output_page)      # index 2
        self.stacked_widget.addWidget(self.lang_page)        # index 3

        self.cursor_overlay = GazePointerOverlay() if SHOW_POINTER else None

        # safety: if tracking stops (face lost), never let a dwell finish by itself
        self.watchdog = QTimer(self)
        self.watchdog.setInterval(250)
        self.watchdog.timeout.connect(self._check_gaze_alive)
        self.watchdog.start()

        # Esc / Ctrl+Q quit from ANY window, including the calibration screen
        self._quit_shortcuts = []
        for seq in ("Esc", "Ctrl+Q"):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
            sc.activated.connect(self.quit_now)
            self._quit_shortcuts.append(sc)            # keep references alive

        self.show_waiting_page()             # language cards appear only AFTER calibration

    # ------------------------------------------------------------------ basics
    def closeEvent(self, event):
        if hasattr(self, 'cursor_overlay') and self.cursor_overlay:
            self.cursor_overlay.close()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.quit_now()
        elif event.key() in (Qt.Key.Key_C, Qt.Key.Key_F5):
            self.trigger_recalibration()
        elif event.key() == Qt.Key.Key_L:            # caretaker: change language
            self.open_language_page(("main",))
        elif event.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()

    def quit_now(self):
        """Esc from anywhere: stop the voice and exit; force-exit if a thread hangs."""
        try:
            self.voice.stop()
        except Exception:
            pass
        if self.cursor_overlay is not None:
            self.cursor_overlay.close()
        killer = threading.Timer(1.5, lambda: os._exit(0))   # a plain thread still fires if Qt is blocked
        killer.daemon = True
        killer.start()
        QApplication.quit()

    # ------------------------------------------------------- calibration hooks
    def show_waiting_page(self):
        """Empty page shown until calibration has finished (no cards, nothing selectable)."""
        self.clear_active_cards()
        self.stacked_widget.setCurrentIndex(3)
        self._clear_grid(self.lang_grid)
        self.lang_title.setText("Calibrating...")

    def set_calibrating(self, flag: bool):
        """run.py calls this when calibration starts / ends. While True, gaze is ignored."""
        self.calibrating = flag
        if flag:
            self._set_active_card(None)
            self.voice.stop()
            if self.cursor_overlay is not None:
                self.cursor_overlay.hide()          # the gaze dot would distract from the calibration dots
        else:
            if self.cursor_overlay is not None:
                self.cursor_overlay.show()

    def after_calibration(self):
        """First calibration -> language page. A later re-calibration -> back to the menu."""
        if self.lang is None:
            self.render_language_page()
        else:
            self.render_main_menu()

    def lock_page_briefly(self, ms=900, skip_current=False):
        """Short pause after a page change so the eyes can settle.
        skip_current=True: the card you are looking at when the page unlocks cannot be
        selected until you have looked away from it once."""
        self.page_locked = True
        self._set_active_card(None)
        for card in self.cards:
            card.set_locked(True)

        def unlock():
            self.page_locked = False
            for card in self.cards:
                card.set_locked(False)
            if skip_current:
                self._skip_pending = True

        QTimer.singleShot(ms, unlock)

    def clear_active_cards(self):
        for card in self.cards:
            card.reset_dwell()
        self.cards.clear()
        self.active_card = None
        self._skip_card = None
        self._skip_pending = False

    def _make_card(self, text, color, grid, r, c, handler, rowspan=1, colspan=1, font_px=None,
                   dwell_ms=None, icon=None):
        """handler is called with no arguments when the card is selected."""
        card = DwellCard(text, bg_color=color, dwell_time_ms=dwell_ms or DWELL_MS,
                         font_px=font_px or _font_px(text), icon=icon)
        card.dwell_completed.connect(lambda _label, h=handler: h())
        grid.addWidget(card, r, c, rowspan, colspan)
        self.cards.append(card)
        return card

    @staticmethod
    def _clear_grid(grid):
        while grid.count():
            w = grid.takeAt(0).widget()
            if w:
                w.deleteLater()

    def _stop_auto_return(self):
        if self.auto_return_timer:
            self.auto_return_timer.stop()
            self.auto_return_timer = None

    def trigger_recalibration(self):
        """Caretaker presses C (or F5): stop any voice and run the calibration screen."""
        self.voice.stop()
        self.recalibrate_requested.emit()

    # ------------------------------------------------------------------- pages
    def open_language_page(self, origin=("main",)):
        """origin = the view that 'Back' on the language page returns to."""
        self._lang_origin = origin
        self.render_language_page()

    def restore_view(self, view):
        """Show a view again: ('main',) / ('sub', category, page) / ('yesno',)."""
        if view[0] == "sub":
            self.render_sub_menu(view[1], view[2])
        elif view[0] == "yesno":
            self.render_yes_no()
        else:
            self.render_main_menu()

    def render_language_page(self, *_):
        self._stop_auto_return()
        self.voice.stop()
        self.clear_active_cards()
        self.active_category = None
        self.stacked_widget.setCurrentIndex(3)
        self._clear_grid(self.lang_grid)
        self.header_title.setText(TITLE)
        self.lang_title.setText("  •  ".join(ui(code, "choose") for code in LANG_CODES))

        for i, code in enumerate(LANG_CODES):
            self._make_card(native_name(code), CARD_COLORS[i], self.lang_grid, 0, i,
                            partial(self.select_language, code), font_px=52)

        has_back = self.lang is not None
        self.lang_grid.setRowStretch(1, 1 if has_back else 0)
        if has_back:        # changing language: a big BACK card under the three languages
            self._make_card(ui(self.lang, "back"), BACK_COLOR, self.lang_grid, 1, 0,
                            partial(self.restore_view, self._lang_origin), 1, len(LANG_CODES),
                            icon="back")
        self.lock_page_briefly(ms=2000, skip_current=True)

    def select_language(self, code):
        self.lang = code
        self.voice.set_language(code)
        self.header_title.setText(f"{TITLE}  •  {native_name(code)}")
        self._set_output_back_text()
        self.render_main_menu()

    def _set_output_back_text(self):
        key = "back_lang" if SENTENCE_BACK_HAS_LANGUAGE else "output_back"
        text = ui(self.lang, key)
        self.output_back_btn.text_label = text
        self.output_back_btn.setText(text)
        self.output_back_btn.set_icon("back_lang" if SENTENCE_BACK_HAS_LANGUAGE else "back")

    def render_main_menu(self, *_):
        if self.lang is None:
            self.render_language_page()
            return
        self._stop_auto_return()
        self.clear_active_cards()
        self.active_category = None
        self.stacked_widget.setCurrentIndex(0)
        self._clear_grid(self.main_grid)

        positions = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]
        for i, ((key, label), (r, c)) in enumerate(zip(menu_cards(self.lang), positions)):
            self._make_card(label, CARD_COLORS[i], self.main_grid, r, c,
                            partial(self.handle_main_card_selection, key), icon=MAIN_ICONS[key])
        self.lock_page_briefly()

    def render_sub_menu(self, category: str, page: int = 0):
        self.clear_active_cards()
        self.active_category = category
        self.stacked_widget.setCurrentIndex(1)
        self._clear_grid(self.sub_grid)

        items = sub_items(self.lang, category)          # [(item_key, label), ...]
        per_page = len(ITEM_SLOTS)
        n_pages = max(1, math.ceil(len(items) / per_page))
        page %= n_pages
        self.sub_page = page
        chunk = items[page * per_page:(page + 1) * per_page]

        for i, ((item_key, label), (r, c)) in enumerate(zip(chunk, ITEM_SLOTS)):
            self._make_card(label, CARD_COLORS[i], self.sub_grid, r, c,
                            partial(self.handle_sub_card_selection, item_key),
                            icon=f"{category}_{item_key}")
        if n_pages > 1:
            self._make_card(ui(self.lang, "next"), CARD_COLORS[4], self.sub_grid, 1, 1,
                            partial(self.render_sub_menu, category, page + 1), icon="next")
        self._make_card(ui(self.lang, "back_lang"), BACK_COLOR, self.sub_grid, 1, 2,
                        partial(self.render_back_or_language, ("main",), ("sub", category, page)),
                        font_px=30, icon="back_lang")
        self.lock_page_briefly()

    def render_yes_no(self):
        """Yes and No are huge; Language and Back share the right-hand column."""
        self.clear_active_cards()
        self.active_category = None
        self.stacked_widget.setCurrentIndex(1)
        self._clear_grid(self.sub_grid)
        self._make_card(build_sentence(self.lang, "yes"), CARD_COLORS[1], self.sub_grid, 0, 0,
                        partial(self.handle_yesno_selection, "yes"), 2, 1, icon="check")
        self._make_card(build_sentence(self.lang, "no"), CARD_COLORS[5], self.sub_grid, 0, 1,
                        partial(self.handle_yesno_selection, "no"), 2, 1, icon="cross")
        self._make_card(ui(self.lang, "language"), CARD_COLORS[2], self.sub_grid, 0, 2,
                        partial(self.open_language_page, ("yesno",)), dwell_ms=LANG_CARD_DWELL_MS,
                        icon="globe")
        self._make_card(ui(self.lang, "back"), BACK_COLOR, self.sub_grid, 1, 2,
                        self.render_main_menu, icon="back")
        self.lock_page_briefly()

    def render_back_or_language(self, back_target, language_origin):
        """Two big cards: Back (goes to back_target) and Language (opens the language page;
        its own Back card returns to language_origin)."""
        self._stop_auto_return()
        self.clear_active_cards()
        self.active_category = None
        self.stacked_widget.setCurrentIndex(1)
        self._clear_grid(self.sub_grid)
        self._make_card(ui(self.lang, "back"), BACK_COLOR, self.sub_grid, 0, 0,
                        partial(self.restore_view, back_target), 2, 2, icon="back")
        self._make_card(ui(self.lang, "language"), CARD_COLORS[7], self.sub_grid, 0, 2,
                        partial(self.open_language_page, language_origin), 2, 1,
                        dwell_ms=LANG_CARD_DWELL_MS, icon="globe")
        self.lock_page_briefly()

    # ---------------------------------------------------------------- handlers
    def handle_main_card_selection(self, key: str):
        if key in ("eat", "go", "pain"):
            self.render_sub_menu(key)
        elif key in ("water", "help"):
            self.prev_view = ("main",)
            self.show_final_output(build_sentence(self.lang, key), key)
        elif key == "yesno":
            self.render_yes_no()

    def handle_yesno_selection(self, key: str):
        self.prev_view = ("yesno",)
        self.show_final_output(build_sentence(self.lang, key), key)

    def handle_sub_card_selection(self, item_key: str):
        sentence = build_sentence(self.lang, self.active_category, item_key)
        self.prev_view = ("sub", self.active_category, self.sub_page)
        self.show_final_output(sentence, self.active_category, item_key)

    def show_final_output(self, sentence: str, key=None, item_key=None, speak: bool = True):
        self.clear_active_cards()
        self.output_label.setText(sentence)
        self.stacked_widget.setCurrentIndex(2)

        self.cards.append(self.output_back_btn)
        self.output_back_btn.reset_dwell()

        if speak and key is not None:
            QTimer.singleShot(200, lambda: self.voice.speak(key, item_key, sentence))

        self._stop_auto_return()
        self.auto_return_timer = QTimer(self)
        self.auto_return_timer.setSingleShot(True)
        self.auto_return_timer.setInterval(8000)
        self.auto_return_timer.timeout.connect(self.render_main_menu)
        self.auto_return_timer.start()

        self.lock_page_briefly()

    def on_output_back(self):
        """BACK on the sentence screen."""
        if SENTENCE_BACK_HAS_LANGUAGE:
            self.voice.stop()
            self.render_back_or_language(self.prev_view, self.prev_view)
        else:
            self.go_back_from_output()

    def go_back_from_output(self):
        """Silence the voice at once and return to the menu the sentence came from,
        so a wrong choice is fixed in ONE step."""
        self.voice.stop()
        self._stop_auto_return()
        self.restore_view(self.prev_view)

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

        if self.calibrating or self.page_locked:
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
        if self._skip_pending:                       # first gaze sample after the page unlocked
            self._skip_card = best_card if best_d <= SNAP_MAX_PX else None
            self._skip_pending = False
        if self._skip_card is not None:
            if best_card is self._skip_card and best_d <= SNAP_MAX_PX:
                self._set_active_card(None)          # still on the card you were already looking at: wait
                return
            self._skip_card = None                   # you looked away once: normal selection from now on

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