"""
nlp/multilang_speech.py
Speaks a sentence in the selected language using an installed Windows voice (pyttsx3).
"""
import threading

import pyttsx3

from nlp.languages import LANG


class MultiLangSpeech:
    def __init__(self, lang="en"):
        self.lang = lang
        self.last_voice_missing = False
        self._lock = threading.Lock()

    def set_language(self, lang):
        self.lang = lang

    def _pick_voice(self, engine):
        hints = [h.upper() for h in LANG[self.lang]["voice_hints"]]
        for v in engine.getProperty("voices"):
            langs = " ".join(str(x) for x in (getattr(v, "languages", None) or []))
            blob = f"{v.id} {v.name} {langs}".upper()
            if any(h in blob for h in hints):
                return v.id
        return None

    def speak(self, text):
        threading.Thread(target=self._run, args=(text,), daemon=True).start()

    def _run(self, text):
        with self._lock:
            try:
                try:
                    import comtypes
                    comtypes.CoInitialize()      # needed when speaking from a worker thread on Windows
                except Exception:
                    pass
                engine = pyttsx3.init()
                voice_id = self._pick_voice(engine)
                self.last_voice_missing = voice_id is None
                if voice_id is None and self.lang != "en":
                    print(f"[TTS] No '{self.lang}' voice installed - install it in Windows settings.")
                    return
                if voice_id:
                    engine.setProperty("voice", voice_id)
                engine.setProperty("rate", 150)
                engine.say(text)
                engine.runAndWait()
                engine.stop()
            except Exception as e:
                print(f"[TTS error] {e}")