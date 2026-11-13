"""STEP A: list every sentence the app can say -> audio/sentences.txt
Run from the project folder:  python tools/list_sentences.py"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nlp.speech_engine import SpeechEngine
from ui.main_window import SUB_ITEMS

engine = SpeechEngine()
sentences = []

for category, items in SUB_ITEMS.items():          # every sub-card
    for item in items:
        sentences.append(engine.build_sov_sentence(category, item))

sentences.append(engine.build_sov_sentence("पानी", ""))   # direct cards
sentences.append(engine.build_sov_sentence("मदद", ""))
sentences += ["हाँ", "नहीं"]                                # yes / no

seen, unique = set(), []
for s in sentences:                                 # remove duplicates, keep order
    if s and s not in seen:
        seen.add(s)
        unique.append(s)

out = os.path.join(ROOT, "audio", "sentences.txt")
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(unique) + "\n")

print(f"{len(unique)} sentences written to {out}")
for s in unique:
    print("  -", s)