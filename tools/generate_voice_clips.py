"""
tools/generate_voice_clips.py
One-time script (needs internet): creates an MP3 for every sentence in every language.
The app then plays these files OFFLINE.

Run from the project root:   python tools/generate_voice_clips.py
Add --force to re-create clips that already exist (e.g. after editing a sentence).
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from gtts import gTTS
from nlp.languages import LANG, LANG_CODES, build_sentence

OUT_DIR = os.path.join(ROOT, "voice_clips")
FORCE = "--force" in sys.argv


def all_phrases(lang):
    """Yields (file_name_without_ext, sentence). Names match VoicePlayer.speak()."""
    data = LANG[lang]
    for key in data["direct"]:                       # water, help, yes, no
        yield key, build_sentence(lang, key)
    for cat, c in data["cats"].items():              # eat, go, pain
        for item in c["items"]:
            yield f"{cat}_{item[0]}", build_sentence(lang, cat, item[0])


def make_clip(lang, text, path):
    kwargs = {"tld": "co.in"} if lang == "en" else {}    # Indian-accent English
    for attempt in range(3):
        try:
            gTTS(text=text, lang=lang, **kwargs).save(path)
            return True
        except Exception as e:
            print(f"    retry {attempt + 1}/3 ({e})")
            time.sleep(2)
    return False


def main():
    done = failed = skipped = 0
    for lang in LANG_CODES:
        folder = os.path.join(OUT_DIR, lang)
        os.makedirs(folder, exist_ok=True)
        print(f"\n=== {LANG[lang]['native']} ({lang}) ===")
        for name, text in all_phrases(lang):
            path = os.path.join(folder, name + ".mp3")
            if os.path.exists(path) and not FORCE:
                skipped += 1
                continue
            print(f"  {name:<22} {text}")
            if make_clip(lang, text, path):
                done += 1
            else:
                failed += 1
                print("    FAILED")
    print(f"\nCreated {done}, skipped {skipped}, failed {failed}. Clips are in: {OUT_DIR}")


if __name__ == "__main__":
    main()