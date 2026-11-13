"""Eye tracker: decides WHICH CARD (cell of a 3 x 2 grid) the user is looking at.

Calibration: the user looks at each of the 6 cell centres twice (12 dots).
Runtime: per-frame probabilities are averaged over the last 8 frames (voting),
and the output point is the CENTRE of the winning cell - so the pointer always
sits on the card that is being selected.
API: process_frame(frame, sw, sh) -> (coords, debug, blinking), recalibrate()."""
import csv
import os
import time
from collections import deque
from datetime import datetime

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.python.solutions import face_mesh as mp_face_mesh
from core.cell_classifier import CellClassifier

# Cell centres as fractions of the screen (match the 3 x 2 card grid in the UI)
CELL_XS = (0.247, 0.50, 0.753)
CELL_YS = (0.32, 0.77)
CELLS = [(x, y) for y in CELL_YS for x in CELL_XS]          # index = row * 3 + col
ORDER = [0, 1, 2, 5, 4, 3, 4, 1, 2, 3, 0, 5]                # 12 dots: every cell twice
CALIB_GRID = [CELLS[i] for i in ORDER]                      # used by the calibration screen

SETTLE_S = 0.55        # seconds to ignore after a dot appears (eye is still moving)
VOTE_FRAMES = 8        # average the last N frames before deciding
SWITCH_MARGIN = 0.12   # a new cell must beat the current one by this much (no flicker)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class DualModalityEyeTracker:
    def __init__(self):
        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1, refine_landmarks=True,
            min_detection_confidence=0.6, min_tracking_confidence=0.6)
        self.clf = CellClassifier()
        self.prob_buf = deque(maxlen=VOTE_FRAMES)
        self.cur_cell = None
        self.calibrated = False
        self.report_text = ""
        self.last_xy = None
        self._reset_collection()

    # ------------------------------------------------------------ calibration
    def _reset_collection(self):
        self._F, self._L, self._V = [], [], []      # features, cell label, visit number
        self._target = None
        self._visit = -1
        self._t0 = 0.0

    def recalibrate(self):
        self.calibrated = False
        self.prob_buf.clear()
        self.cur_cell = None
        self.last_xy = None
        self.report_text = ""
        self._reset_collection()

    def show_dot(self, index, screen_w, screen_h):
        self._target = ORDER[index]                 # which cell is being shown
        self._visit = index
        self._t0 = time.perf_counter()

    def hide_dot(self):
        self._target = None

    def _save_csv(self, F, L, V, screen_w, screen_h):
        """Keep the raw calibration data so accuracy problems can be analysed later."""
        try:
            folder = os.path.join(ROOT, "logs")
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, datetime.now().strftime("calibration_%Y%m%d_%H%M%S.csv"))
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["visit", "cell", "gx_right", "gx_left", "gy_right", "gy_left",
                            "g2_right", "g2_left", "yaw", "pitch", "screen_w", "screen_h"])
                for fv, lab, vis in zip(F, L, V):
                    w.writerow([vis, lab] + [f"{x:.6f}" for x in fv] + [screen_w, screen_h])
            print(f"[Calibration] data saved: {path}")
        except Exception as e:
            print(f"[Calibration] could not save data: {e}")

    def finish_calibration(self, screen_w=1920, screen_h=1080):
        """Returns accuracy 0..1 (None = failed). Text for the screen is in report_text."""
        self._target = None
        F, L, V = list(self._F), list(self._L), list(self._V)
        if len(F) < 120:
            self.report_text = "Calibration failed: face not seen well enough."
            self._reset_collection()
            return None
        try:
            self.clf.fit(np.array(F), np.array(L), np.array(V))
        except Exception as e:
            self.report_text = f"Calibration failed: {e}"
            self._reset_collection()
            return None
        self._save_csv(F, L, V, screen_w, screen_h)
        self.calibrated = True
        self.prob_buf.clear()
        self.cur_cell = None
        acc = self.clf.accuracy
        self.report_text = (f"Calibration accuracy: {acc * 100:.0f}%   "
                            f"(method: {self.clf.feat_name} + {self.clf.model_name})")
        print(f"[Calibration] {self.report_text}  per-frame: {self.clf.frame_accuracy * 100:.0f}%")
        for fn, mn, a, fa in self.clf.table:
            print(f"    tried {fn:11s} {mn:4s} -> {a * 100:5.1f}%")
        return acc

    # --------------------------------------------------------------- features
    @staticmethod
    def _eye_feats(out_, in_, top, bot, iris):
        """Iris offset in the eye's own axes (corrects head roll), divided by eye width."""
        width = np.linalg.norm(in_ - out_) + 1e-6
        u = (in_ - out_) / width
        v = np.array([-u[1], u[0]])
        c = (out_ + in_) / 2.0
        d = iris - c
        lid_c = (top + bot) / 2.0
        return d @ u / width, d @ v / width, (iris - lid_c) @ v / width

    def _features(self, lms, w, h):
        P = lambda i: np.array([lms[i].x * w, lms[i].y * h])
        r = self._eye_feats(P(33), P(133), P(159), P(145), P(468))
        l = self._eye_feats(P(362), P(263), P(386), P(374), P(473))
        r_w, l_w = np.linalg.norm(P(33) - P(133)), np.linalg.norm(P(362) - P(263))
        ear = (np.linalg.norm(P(159) - P(145)) / (r_w + 1e-6) +
               np.linalg.norm(P(386) - P(374)) / (l_w + 1e-6)) / 2.0
        nose, cl, cr = P(1), P(234), P(454)
        fore, chin = P(10), P(152)
        face_w = np.linalg.norm(cr - cl) + 1e-6
        face_h = np.linalg.norm(chin - fore) + 1e-6
        yaw = (nose[0] - (cl[0] + cr[0]) / 2) / face_w
        pitch = (nose[1] - (fore[1] + chin[1]) / 2) / face_h
        vec = np.array([r[0], l[0], r[1], l[1], r[2], l[2], yaw, pitch])
        return vec, ear, min(r_w, l_w)

    # ---------------------------------------------------------------- runtime
    def _cell_xy(self, feats, screen_w, screen_h):
        """Vote over the last frames and return the centre pixel of the winning cell."""
        self.prob_buf.append(self.clf.proba(feats))
        avg = np.mean(self.prob_buf, axis=0)
        best = int(avg.argmax())
        if self.cur_cell is None or (best != self.cur_cell and
                                     avg[best] > avg[self.cur_cell] + SWITCH_MARGIN):
            self.cur_cell = best
        fx, fy = CELLS[self.cur_cell]
        return int(fx * screen_w), int(fy * screen_h)

    def process_frame(self, frame, screen_w, screen_h):
        try:
            h, w, _ = frame.shape
            res = self.face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            dbg = cv2.resize(frame, (180, 120))
            if not res.multi_face_landmarks:
                cv2.putText(dbg, "No Face", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                return None, dbg, True
            feats, ear, eye_w = self._features(res.multi_face_landmarks[0].landmark, w, h)
            if eye_w < 14:
                cv2.putText(dbg, "Move closer", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
                return None, dbg, True
            if ear < 0.14:
                cv2.putText(dbg, "Blink", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
                return self.last_xy, dbg, True

            if self._target is not None:                     # collecting calibration data
                if time.perf_counter() - self._t0 >= SETTLE_S:
                    self._F.append(feats); self._L.append(self._target); self._V.append(self._visit)
                cv2.putText(dbg, f"Calib {self._visit + 1}/{len(ORDER)}", (5, 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
                return None, dbg, False

            if not self.calibrated:
                cv2.putText(dbg, "Needs calibration", (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
                return None, dbg, False

            self.last_xy = self._cell_xy(feats, screen_w, screen_h)
            cv2.putText(dbg, "Tracking", (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
            return self.last_xy, dbg, False
        except Exception as e:
            print(f"Tracking error: {e}")
            return None, None, True