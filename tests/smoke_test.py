#!/usr/bin/env python3
"""End-to-end check on made-up footage, on any computer (it is what the Windows test on GitHub runs).

A synthetic interview (text-to-speech voice: Windows SAPI, macOS say, or espeak-ng) and test-pattern b-roll (one clip
tagged HLG to exercise the HDR path, one vertical) -> transcribe -> a regular edit in both formats with graphics and
music -> a social edit (vertical preview) with hook, captions and music. Fails loudly if any output is missing or wrong.

Usage:  python tests/smoke_test.py [OUT_DIR]          (default tests/out)
"""
import json, os, shutil, subprocess, sys, textwrap
import numpy as np
from scipy.io import wavfile

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
HERE = os.path.dirname(os.path.abspath(__file__)); SK = os.path.dirname(HERE); S = os.path.join(SK, "scripts")
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out"))
PY = sys.executable
SENTENCES = ["My name is Sam, and I train detection dogs.", "Every search starts the same way.",
             "The first time she found the hide on her own, I knew she was ready.", "Start with the basics, and stay consistent."]
SR, GAP = 48000, 0.8


def run(cmd, **kw):
    print("$", " ".join(str(c) for c in cmd)[:220], flush=True); return subprocess.run([str(c) for c in cmd], check=True, **kw)


def tts(text, wav):
    if os.name == "nt":
        ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              f"$s.SetOutputToWaveFile('{wav}'); $s.Speak('{text}'); $s.Dispose()")
        run(["powershell", "-NoProfile", "-Command", ps])
    elif sys.platform == "darwin":
        run(["say", "-o", wav[:-4] + ".aiff", text]); run(["ffmpeg", "-v", "error", "-y", "-i", wav[:-4] + ".aiff", wav])
    elif shutil.which("espeak-ng"):
        run(["espeak-ng", "-w", wav, text])
    else:
        sys.exit("no text-to-speech engine (Windows SAPI, macOS say or espeak-ng) to make a test voice")


def load(wav):
    run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-ac", "1", "-ar", str(SR), wav[:-4] + "_48.wav"])
    x = wavfile.read(wav[:-4] + "_48.wav")[1].astype(np.float64) / 32768.0
    on = np.where(np.abs(x) > 0.01)[0]
    return x[max(0, on[0] - 200):on[-1] + 200] if len(on) else x


def main():
    if os.path.isdir(OUT): shutil.rmtree(OUT)
    foot, edit = os.path.join(OUT, "footage"), os.path.join(OUT, "edit"); os.makedirs(foot); os.makedirs(edit)
    # 1. voice: one sentence at a time, joined with 0.8 s of silence, so every sentence's times are known exactly
    parts, times, t = [], [], GAP
    for i, s in enumerate(SENTENCES):
        wav = os.path.join(OUT, f"s{i}.wav"); tts(s, wav); x = load(wav)
        parts.append(np.zeros(int(GAP * SR))); parts.append(x); times.append((t, t + len(x) / SR)); t += len(x) / SR + GAP
    parts.append(np.zeros(int(1.5 * SR)))
    voice = np.concatenate(parts); voice = voice / np.abs(voice).max() * 0.5
    wavfile.write(os.path.join(OUT, "voice.wav"), SR, (voice * 32767).astype(np.int16))
    dur = len(voice) / SR
    print("sentences:", [(round(a, 2), round(b, 2)) for a, b in times])
    # 2. footage: interview (16:9 SDR) with the voice + light room noise; b-roll A tagged HLG (10-bit), b-roll B vertical
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s=1920x1080:r=30:d={dur:.2f}", "-i", os.path.join(OUT, "voice.wav"),
         "-f", "lavfi", "-i", "anoisesrc=color=pink:amplitude=0.003:r=48000", "-filter_complex", "[1:a][2:a]amix=inputs=2:duration=first:normalize=0[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-t", f"{dur:.2f}",
         os.path.join(foot, "INTERVIEW.mp4")])
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1920x1080:r=30:d=14", "-f", "lavfi", "-i", "sine=f=330:d=14",
         "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p10le", "-profile:v", "high10", "-color_primaries", "bt2020",
         "-color_trc", "arib-std-b67", "-colorspace", "bt2020nc", "-c:a", "aac", os.path.join(foot, "BROLL_A.mp4")])
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "mandelbrot=s=1080x1920:r=30", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-t", "14", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", os.path.join(foot, "BROLL_B.mp4")])
    # 3. transcribe (word times for captions and the hook)
    run([PY, os.path.join(S, "transcribe.py"), os.path.join(foot, "INTERVIEW.mp4"), edit, "--words"])
    (a0, b0), (a1, b1), (a2, b2), (a3, b3) = times
    common = f'''
import os
HERE = os.path.dirname(os.path.abspath(__file__))
FOOTAGE = os.path.join(HERE, "..", "footage")
OUT_DIR = os.path.join(HERE, "..", "videos")
INTERVIEW = "INTERVIEW"
ROOM_TONE = {b0 + 0.1:.2f}
WORDS = "INTERVIEW_words.csv"
'''
    regular = common + textwrap.dedent(f'''
        OUTPUT = "SMOKE_regular"
        EDIT_TYPE = "regular"
        FORMATS = ("vertical", "horizontal")
        MUSIC_STYLE = "uplifting"
        COLD = dict(clip="BROLL_A", cin=1.0, cout=4.0, hit=3.0)
        ENERGY = {{"intro": 1, "why": 2, "proof": 3, "close": 1}}
        LIFT = "proof"
        SECTIONS = [("intro", [("i1", {a0 - .05:.2f}, {b0 + .05:.2f})]), ("why", [("w1", {a1 - .05:.2f}, {b1 + .05:.2f})]),
                    ("proof", [("p1", {a2 - .05:.2f}, {b2 + .05:.2f})]), ("close", [("c1", {a3 - .05:.2f}, {b3 + .05:.2f})])]
        def shots(e):
            return [
                e.S("COLD", "BROLL_A", 1.0, e.STING[0], [(1.0, .5, .5)], zk=[(1.0, 1.0), (4.0, 1.1)]),
                e.B("STING", e.STING[1]),
                e.S("CAM", INTERVIEW, {a0 - .05:.2f} - 0.35, e.nxt("intro"), [({a0:.2f}, .5, .4)]),
                e.S("B1", "BROLL_B", 2.0, e.nxt("why"), [(2.0, .5, .5)], fit="contain"),
                e.B("QUOTE", e.nxt("proof")),
                e.S("B2", "BROLL_A", 6.0, e.PICTURE_END, [(6.0, .5, .5)], punch=.05, whip="i"),
                e.B("END", e.TOTAL),
            ]
        def graphics(e):
            return [e.G("lower-third", e.start("i1") + 0.2, 3.5, name="Sam Tester", role="Detection dog trainer"),
                    e.G("quote", e.SEC["proof"], e.nxt("proof") - e.SEC["proof"], text="The first time she found the hide on her own, I knew she was ready.", highlight=4, by="Sam Tester")]
        def nat(e, SH):
            return [("BROLL_A", 1.0, 4.0, 0.0, -6.0)]
    ''')
    social = common + textwrap.dedent(f'''
        OUTPUT = "SMOKE_social"
        EDIT_TYPE = "social"
        FORMATS = ("vertical",)
        MUSIC_STYLE = "groove"
        HOOK = dict(lines=["The first time she found", "the hide *on her own*"])
        ENERGY = {{"hook": 3, "intro": 1, "close": 2}}
        SECTIONS = [("hook", [("h1", {a2 - .05:.2f}, {b2 + .05:.2f})]), ("intro", [("i1", {a0 - .05:.2f}, {b0 + .05:.2f})]),
                    ("close", [("c1", {a3 - .05:.2f}, {b3 + .05:.2f})])]
        def shots(e):
            return [
                e.S("H1", "BROLL_A", 2.0, e.nxt("hook"), [(2.0, .5, .5)], punch=.06),
                e.S("I1", "BROLL_B", 1.0, e.nxt("intro"), [(1.0, .5, .5)], whip="i"),
                e.S("C1", "BROLL_A", 8.0, e.PICTURE_END, [(8.0, .5, .5)]),
                e.B("END", e.TOTAL),
            ]
        def graphics(e):
            return [e.G("lower-third", e.start("i1") + 0.1, 3.0, name="Sam Tester", role="Detection dog trainer")]
    ''')
    for name, body in (("regular", regular), ("social", social)):
        open(os.path.join(edit, f"{name}_edit.py"), "w", encoding="utf-8").write(body)
    run([PY, os.path.join(S, "build.py"), os.path.join(edit, "regular_edit.py"), "--dry"])
    run([PY, os.path.join(S, "build.py"), os.path.join(edit, "regular_edit.py")])
    run([PY, os.path.join(S, "build.py"), os.path.join(edit, "social_edit.py"), "--preview"])
    # 4. check the files
    vids = os.path.join(OUT, "videos"); bad = []
    for f, w, h in (("SMOKE_regular_vertical.mp4", 1080, 1920), ("SMOKE_regular_horizontal.mp4", 1920, 1080), ("SMOKE_social_vertical_preview.mp4", 540, 960)):
        p = os.path.join(vids, f)
        if not os.path.isfile(p): bad.append(f"missing {f}"); continue
        info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration", "-of", "json", p],
                                         capture_output=True, text=True).stdout)
        v = [s for s in info["streams"] if s["codec_type"] == "video"][0]; a = [s for s in info["streams"] if s["codec_type"] == "audio"]
        if (v["width"], v["height"]) != (w, h) or not a: bad.append(f"{f}: {v['width']}x{v['height']}, audio {bool(a)}")
        d = float(info["format"]["duration"])
        for k, tq in enumerate((0.3 * d, 0.55 * d, d - 1.5)):
            run(["ffmpeg", "-v", "error", "-y", "-ss", f"{tq:.2f}", "-i", p, "-frames:v", "1", os.path.join(OUT, f"{f[:-4]}_{k}.png")])
        print(f"{f}: {v['width']}x{v['height']}, {d:.1f} s, audio {'yes' if a else 'NO'}")
    cap = os.path.join(edit, "work_social_edit", "captions.txt")
    print("captions:\n" + (open(cap, encoding="utf-8").read() if os.path.isfile(cap) else "MISSING"))
    if not os.path.isfile(cap): bad.append("no captions.txt")
    if bad: sys.exit("SMOKE TEST FAILED: " + "; ".join(bad))
    print("SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
