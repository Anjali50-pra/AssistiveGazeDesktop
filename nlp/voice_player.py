"""
nlp/voice_player.py
Plays the pre-recorded clip for the chosen language (offline).
If a clip is missing, falls back to your existing audio.voice.VoiceOutput.
"""
import os

from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from audio.voice import VoiceOutput

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIPS_DIR = os.path.join(ROOT, "voice_clips")


class VoicePlayer:
    def __init__(self, lang="en"):
        self.lang = lang
        self.audio_out = QAudioOutput()
        self.audio_out.setVolume(1.0)
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_out)
        self.fallback = VoiceOutput()

    def set_language(self, lang):
        self.lang = lang

    def speak(self, key, item_key=None, text=""):
        """key = water | help | yes | no | eat | go | pain ; item_key for eat / go / pain."""
        name = key if item_key is None else f"{key}_{item_key}"
        path = os.path.join(CLIPS_DIR, self.lang, name + ".mp3")
        if os.path.exists(path):
            self.fallback.stop()
            self.player.stop()
            self.player.setSource(QUrl.fromLocalFile(path))
            self.player.play()
        else:
            print(f"[Voice] clip missing: {path}")
            self.fallback.speak(text)

    def stop(self):
        self.player.stop()
        try:
            self.fallback.stop()
        except Exception:
            pass