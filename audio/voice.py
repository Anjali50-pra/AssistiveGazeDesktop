"""Voice output for the caretaker alert.

  * Plays a short chime, then the sentence (pre-recorded clip, else live voice).
  * A NEW sentence (or stop()) cuts the old one off IMMEDIATELY - voices never
    pile up, and the eye tracking keeps working while it speaks.
  * The live voice runs as a separate process that is killed on stop(), because
    the Windows speech engine cannot be interrupted reliably from inside Python.
"""
import hashlib
import os
import subprocess
import sys
import threading
import time
import wave

try:
    import winsound            # Windows only
except ImportError:
    winsound = None

CLIPS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clips")
REPEAT_TIMES = 2        # how many times the sentence is spoken
REPEAT_GAP_S = 1.0      # pause between repeats
SPEECH_RATE = 140       # live-voice speed (words/min)

# Small program run in a child process for the live (non-recorded) voice
_CHILD = r'''
import sys
import pyttsx3
text = sys.argv[1]
engine = pyttsx3.init()
engine.setProperty("volume", 1.0)
engine.setProperty("rate", int(sys.argv[2]))
vid = None
for v in engine.getProperty("voices"):
    blob = (v.name + " " + str(getattr(v, "id", "")) + " " + str(getattr(v, "languages", ""))).lower()
    if "hindi" in blob or "hi-in" in blob or "hemant" in blob or "kalpana" in blob:
        vid = v.id
        break
if vid:
    engine.setProperty("voice", vid)
engine.say(text)
engine.runAndWait()
'''


def clip_path(text: str) -> str:
    """Same naming rule as tools/make_audio.py (hash of the sentence)."""
    name = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12] + ".wav"
    return os.path.join(CLIPS_DIR, name)


def _wav_seconds(path) -> float:
    try:
        with wave.open(path, "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return 3.0


class VoiceOutput:
    def __init__(self):
        self._cond = threading.Condition()
        self._plock = threading.Lock()
        self._proc = None
        self._gen = 0              # changes on every speak()/stop(); old jobs see it and quit
        self._pending = None
        self._warned = False
        self._worker = threading.Thread(target=self._loop, daemon=True)
        self._worker.start()
        n = len([f for f in os.listdir(CLIPS_DIR) if f.endswith(".wav")]) if os.path.isdir(CLIPS_DIR) else 0
        print(f"[Voice] {n} pre-recorded clips found" + ("" if n else " (using live voice fallback)"))

    # ------------------------------------------------------------- public API
    def speak(self, text: str):
        """Start speaking `text`; anything still playing is cut off first."""
        with self._cond:
            self._gen += 1
            self._pending = (self._gen, text)
            self._cond.notify()
        self._silence()

    def stop(self):
        """Silence everything right now (used by the BACK card)."""
        with self._cond:
            self._gen += 1
            self._pending = None
        self._silence()

    # ---------------------------------------------------------------- helpers
    def _alive(self, gen) -> bool:
        return gen == self._gen

    def _silence(self):
        if winsound is not None:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
        with self._plock:
            if self._proc is not None and self._proc.poll() is None:
                try:
                    self._proc.kill()
                except Exception:
                    pass

    def _wait(self, gen, seconds) -> bool:
        """Sleep, but wake up instantly if cancelled. False = cancelled."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if not self._alive(gen):
                self._silence()
                return False
            time.sleep(0.03)
        return self._alive(gen)

    def _chime(self, gen):
        if winsound is None:
            return
        for freq in (880, 1175):
            if not self._alive(gen):
                return
            try:
                winsound.Beep(freq, 150)
            except Exception:
                return

    def _speak_live_once(self, gen, text) -> bool:
        """Speak with the live voice in a child process; killed instantly if cancelled."""
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.Popen([sys.executable, "-c", _CHILD, text, str(SPEECH_RATE)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                creationflags=flags)
        with self._plock:
            self._proc = proc
        while proc.poll() is None:
            if not self._alive(gen):
                proc.kill()
                break
            time.sleep(0.03)
        with self._plock:
            self._proc = None
        if proc.returncode not in (0, None) and self._alive(gen) and not self._warned:
            self._warned = True
            print("[Voice] live voice failed - is pyttsx3 installed?  pip install pyttsx3")
        return self._alive(gen)

    def _run_job(self, gen, text):
        self._chime(gen)
        if not self._alive(gen):
            return
        path = clip_path(text)
        if winsound is not None and os.path.isfile(path):
            dur = _wav_seconds(path)
            for i in range(REPEAT_TIMES):
                if not self._alive(gen):
                    return
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                if not self._wait(gen, dur + 0.15):
                    return
                if i < REPEAT_TIMES - 1 and not self._wait(gen, REPEAT_GAP_S):
                    return
            return
        for i in range(REPEAT_TIMES):
            if not self._speak_live_once(gen, text):
                return
            if i < REPEAT_TIMES - 1 and not self._wait(gen, REPEAT_GAP_S):
                return

    def _loop(self):
        while True:
            with self._cond:
                while self._pending is None:
                    self._cond.wait()
                gen, text = self._pending
                self._pending = None
            try:
                self._run_job(gen, text)
            except Exception as e:
                print(f"[Voice] error: {e}")