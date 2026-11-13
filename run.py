import sys
import cv2
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, QTimer, pyqtSignal
from ui.main_window import AACMainWindow
from ui.calibration_widget import CalibrationOverlay
from core.eye_tracker import DualModalityEyeTracker


class GazeTrackingThread(QThread):
    gaze_updated = pyqtSignal(int, int, bool)
    frame_updated = pyqtSignal(np.ndarray)

    def __init__(self, screen_w, screen_h):
        super().__init__()
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.running = True
        self.tracker = DualModalityEyeTracker()

    def open_camera(self):
        print("[Camera Init] Connecting directly to primary webcam...")
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)

        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
            return cap

        return None

    def run(self):
        cap = self.open_camera()
        if cap is None:
            err_img = np.zeros((120, 180, 3), dtype=np.uint8)
            cv2.putText(err_img, "Camera Blocked", (15, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            self.frame_updated.emit(err_img)
            return

        while self.running:
            ret, frame = cap.read()
            if not ret or frame is None:
                self.msleep(10)
                continue

            gaze_coords, debug_frame, is_blinking = self.tracker.process_frame(
                frame, self.screen_w, self.screen_h
            )

            if debug_frame is not None:
                self.frame_updated.emit(debug_frame)

            if gaze_coords is not None:
                self.gaze_updated.emit(gaze_coords[0], gaze_coords[1], is_blinking)

            self.msleep(15)

        cap.release()

    def stop(self):
        self.running = False
        self.wait()


def main():
    app = QApplication(sys.argv)
    window = AACMainWindow()
    window.show()

    screen_geometry = app.primaryScreen().geometry()
    screen_w = screen_geometry.width()
    screen_h = screen_geometry.height()

    tracker_thread = GazeTrackingThread(screen_w, screen_h)
    tracker_thread.gaze_updated.connect(window.update_gaze_point)
    tracker_thread.frame_updated.connect(window.update_camera_preview)

    # 9-point calibration (runs at launch and on RE-CALIBRATE)
    calib = CalibrationOverlay(tracker_thread.tracker, screen_w, screen_h)
    calib.finished.connect(
        lambda err: print(f"Calibration error: {err:.0f}px" if err else
                          "Calibration failed - please try again")
    )
    window.recalibrate_requested.connect(calib.start)

    tracker_thread.start()
    QTimer.singleShot(800, calib.start)   # auto-start calibration at launch

    app.aboutToQuit.connect(tracker_thread.stop)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()