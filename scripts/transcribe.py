#!/usr/bin/env python3
"""Transcribe the interview with local Whisper (whisper.cpp), with source timestamps.

Usage:  python3 transcribe.py INTERVIEW_CLIP OUT_DIR            -> OUT_DIR/<clip>.txt (+ .srt)  segment timestamps
        python3 transcribe.py INTERVIEW_CLIP OUT_DIR --words    -> also OUT_DIR/<clip>_words.csv  one word per row
        python3 transcribe.py CLIP OUT_DIR --range 3.2-4.1 [A-B ...]   Whisper on short windows only (padded with silence):
                                                                       is anyone talking under a shot or a bark?

Env: WHISPER_MODEL (default ~/.whisper-models/ggml-small.en.bin), WHISPER_CLI (default whisper-cli).
Use the transcript to find answers and rough times; place every cut from the level envelope, not from Whisper's
word times (they drift by 0.2-0.5 s around pauses). Do not use -dtw with a prompt: it garbled the transcript.
"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import WHISPER_CLI, WHISPER_MODEL, whisper, setup_console
setup_console()

if len(sys.argv) < 3: sys.exit(__doc__)
src, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
if "--range" in sys.argv:                       # one short window, padded with silence: is anyone talking in it?
    from common import load_mono, snippet_text
    x = load_mono(src)
    for r in sys.argv[sys.argv.index("--range") + 1:]:
        if r.startswith("--"): break
        a_, b_ = (float(v) for v in r.split("-"))
        print(f"{a_:.2f}-{b_:.2f}: {snippet_text(x, 48000, a_, b_, out) or '(no words)'}")
    sys.exit()
stem = os.path.join(out, os.path.splitext(os.path.basename(src))[0])
wav = stem + "_16k.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
subprocess.run([WHISPER_CLI, "-m", WHISPER_MODEL, "-f", wav, "-l", "en", "-np", "-otxt", "-osrt", "-of", stem], check=True,
               capture_output=True)
lines = [l for l in open(stem + ".srt", encoding="utf-8", errors="replace").read().split("\n\n") if l.strip()]
with open(stem + ".txt", "w", encoding="utf-8") as f:
    for block in lines:
        b = block.splitlines()
        if len(b) >= 3: f.write(f"[{b[1][:8]}.{b[1][9:11]}] {' '.join(b[2:]).strip()}\n")
print(open(stem + ".txt", encoding="utf-8").read())
if "--words" in sys.argv:
    words = whisper(wav, words=True, out_stem=stem + "_words")
    print(f"{len(words)} words -> {stem}_words.csv")
