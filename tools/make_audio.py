"""STEP B: create one loud, clear WAV clip per sentence with Piper (offline Hindi voice).

Setup (once):
  pip install piper-tts
  Download the 2 files of a Hindi voice into  AssistiveGazeDesktop/models/ :
     hi_IN-rohan-medium.onnx   and   hi_IN-rohan-medium.onnx.json
  (or the priyamvada voice) from
     https://huggingface.co/rhasspy/piper-voices/tree/main/hi/hi_IN/rohan/medium

Run from the project folder:
  python tools/make_audio.py
  python tools/make_audio.py models/hi_IN-priyamvada-medium.onnx   (other voice)"""
import hashlib
import os
import sys
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "models", "hi_IN-rohan-medium.onnx")
SENTENCES = os.path.join(ROOT, "audio", "sentences.txt")
CLIPS = os.path.join(ROOT, "audio", "clips")
PEAK = 0.95          # make every clip loud (95% of maximum) and equally loud


def clip_name(text):                      # must match audio/voice.py
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12] + ".wav"


def normalise(path):
    with wave.open(path, "rb") as r:
        params = r.getparams()
        data = np.frombuffer(r.readframes(r.getnframes()), dtype=np.int16).astype(np.float32)
    peak = float(np.max(np.abs(data))) or 1.0
    data = np.clip(data * (PEAK * 32767.0 / peak), -32768, 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setparams(params)
        w.writeframes(data.tobytes())


def main():
    try:
        from piper import PiperVoice
    except ImportError:
        sys.exit("Piper is not installed. Run:  pip install piper-tts")
    if not os.path.isfile(MODEL):
        sys.exit(f"Voice file not found: {MODEL}\nDownload the .onnx and .onnx.json files into the models folder.")
    if not os.path.isfile(SENTENCES):
        sys.exit("Run STEP A first:  python tools/list_sentences.py")

    os.makedirs(CLIPS, exist_ok=True)
    voice = PiperVoice.load(MODEL)
    with open(SENTENCES, encoding="utf-8") as f:
        sentences = [line.strip() for line in f if line.strip()]

    index_lines = []
    for i, text in enumerate(sentences, 1):
        name = clip_name(text)
        path = os.path.join(CLIPS, name)
        with wave.open(path, "wb") as wf:
            voice.synthesize_wav(text, wf)
        normalise(path)
        index_lines.append(f"{name}\t{text}")
        print(f"[{i}/{len(sentences)}] {text}")

    with open(os.path.join(CLIPS, "_index.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines) + "\n")
    print(f"\nDone: {len(sentences)} clips in {CLIPS}")
    print("Listen to each clip (double-click the .wav files) and check the pronunciation.")


if __name__ == "__main__":
    main()