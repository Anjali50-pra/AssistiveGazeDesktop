# NayanVaani - Eye-Gaze Communication System (AAC)

A Windows desktop app that lets a patient who cannot speak choose Hindi cards
with the eyes (webcam only). The chosen sentence is shown on screen and spoken
aloud with an alert chime for the caretaker.

Built at the Assistive Technology Lab, BVRIT Narsapur.

## Requirements
- Windows, Python 3.11, a webcam
- Install packages:  pip install -r requirements.txt

## Run
    python run.py

On start, follow the 12 dots with your eyes. Sit facing a light, about
50-60 cm from the screen, and keep your head still.

## Keys
- C or F5: recalibrate
- F11: toggle full screen
- Esc: quit

## Folders
- core/   eye tracking (MediaPipe face landmarks + card classifier)
- ui/     screens, cards, calibration
- nlp/    Hindi sentence builder
- audio/  voice output (recorded clips, with live-voice fallback)
- tools/  scripts that list sentences and create the audio clips

## Voice clips (optional, better voice)
1. python tools/list_sentences.py
2. Put a Piper Hindi voice (.onnx and .onnx.json) in models/ (not stored in this repo)
3. Run tools/make_audio.py with an environment that has piper-tts installed

## Versions
- Tag `gemini-base-v1`: the original first version
- Branch `claude-version`: the improved version