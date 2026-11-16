#!/usr/bin/env python3
"""Render a Highland edit from an edit file (the whole edit as data): interview + action b-roll + the Highland
graphics, captions and music, vertical 9:16 and/or horizontal 16:9.

Usage:  python build.py EDIT.py --dry        timeline, graphics, captions and warnings only (seconds; run after every change)
        python build.py EDIT.py              render the edit's FORMATS
        python build.py EDIT.py --preview    a quick half-size draft (<OUTPUT>_<format>_preview.mp4) for review rounds
        python build.py EDIT.py --audio      sound only: rebuild the mix (a new MUSIC_STYLE, levels) and re-mux; picture kept
        python build.py EDIT.py --vertical   (or --horizontal) one format only
Env:    WORK=<dir>  intermediate files (default: work_<edit name>/ next to the edit file)

Outputs, in OUT_DIR (default: the footage folder): <OUTPUT>_<format>_nomusic.mp4 while MUSIC_STYLE is None (the draft to
review), <OUTPUT>_<format>.mp4 once a MUSIC_STYLE is set. 1080x1920 / 1920x1080, 30 fps, H.264, Rec.709 (SDR).

What it does
  voice    cuts the interview into the edit's pieces (minus CUTS), 20 ms crossfades, room tone across gaps, background
           cleaned (denoise.py), high-passed at 80 Hz, normalised to LUFS
  nat      short natural-sound windows from the b-roll, placed by the edit
  music    music.py scores the finished cut (tempo bent so bars land on the edit's moments, transitions on the graphics),
           ducked under the voice; only when MUSIC_STYLE is set, the draft has none
  picture  every shot is a crop of its clip with a smoothed camera path (subject keys, zoom keys, punch, whip blur);
           phone HDR (HLG/PQ) is converted to Rec.709 with a LUT so the brand colours come out exact
  graphics motion/ drawn by gfx.py in headless Edge/Chrome (logo sting, name tags, cards, hook, captions, end card),
           laid over the picture as one transparent track
"""
import csv, glob, hashlib, importlib.util, json, math, os, re, subprocess, sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import FILLERS, setup_console, whisper
from denoise import extract_clean
import gfx, lut
setup_console()

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
if not ARGS: sys.exit(__doc__)
EDIT_PATH = os.path.abspath(ARGS[0])
_spec = importlib.util.spec_from_file_location("edit", EDIT_PATH); E = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(E)
DRY, AUDIO_ONLY, PREVIEW = "--dry" in sys.argv, "--audio" in sys.argv, "--preview" in sys.argv
PSCALE = 0.5 if PREVIEW else 1.0                # previews: half size, quick encode, same cut
SUFFIX = "_p" if PREVIEW else ""
def opt(name, default): return getattr(E, name, default)
ORIENTS = [o for o in ("vertical", "horizontal") if f"--{o}" in sys.argv] or list(opt("FORMATS", ("vertical", "horizontal")))
assert ORIENTS and set(ORIENTS) <= {"vertical", "horizontal"}, f"FORMATS must be vertical and/or horizontal, not {ORIENTS}"

FOOTAGE, OUTPUT = E.FOOTAGE, E.OUTPUT
OUT_DIR = opt("OUT_DIR", FOOTAGE)
WORK = os.path.abspath(os.environ.get("WORK") or os.path.join(os.path.dirname(EDIT_PATH), "work_" + os.path.splitext(os.path.basename(EDIT_PATH))[0]))
FPS, SR, XF = 30, 48000, 0.02                    # frame rate, audio rate, splice crossfade
VOICE = bool(opt("INTERVIEW", None))             # False: a footage-only edit (no voice): natural sound, on-screen text, music
TONE = opt("ROOM_TONE", 0.0)                     # interview edits: start of >= 0.6 s of speech-free room tone in the interview
NOROT = tuple(opt("NOROT", ()))                  # clips carrying a wrong rotation flag: read with -noautorotate
EDIT_TYPE = opt("EDIT_TYPE", "regular")
assert EDIT_TYPE in ("regular", "social"), "EDIT_TYPE is 'regular' or 'social'"
SOCIAL = EDIT_TYPE == "social"
LUFS, PEAK = opt("LUFS", -14.0 if SOCIAL else -16.0), -2.0      # -2 dBFS sample peak keeps the AAC true peak under -1
AIR = opt("SECTION_AIR", 0.25 if SOCIAL else 0.35)      # pause before each section
SECTIONS, ENERGY = opt("SECTIONS", []), opt("ENERGY", {})
PARTS = opt("PARTS", [])                         # footage-only: [(part, output start)]: the story's parts (music energy, downbeats)
LENGTH = opt("LENGTH", None)                     # footage-only: seconds of picture before the end card
SHOT_SOUND = opt("SHOT_SOUND", 0.0)              # footage-only: each shot's own sound, dB re -26 dBFS (None: silent)
CAPTION_TEXT = opt("CAPTION_TEXT", [])           # footage-only captions: [(start, end, "short line")]
CUTS = sorted(opt("CUTS", []))
COLD = opt("COLD", None)                         # natural-sound cold open (regular), or None
HOOK = opt("HOOK", None)                         # social: dict(lines=[...]) laid over the first section
LOGO_STING = opt("LOGO_STING", not SOCIAL); STING_LEN = 3.0
END_CARD = opt("END_CARD", True); END_CARD_LEN = float(opt("END_CARD_LEN", 4.0))
END_HOLD = float(opt("END_HOLD", (0.5 if END_CARD else 2.6) if VOICE else 0.0))   # picture after the last word
CAPTIONS = opt("CAPTIONS", SOCIAL if VOICE else bool(CAPTION_TEXT))
MUSIC_STYLE = opt("MUSIC_STYLE", None)
# music level re the speech level: under the voice, where nobody speaks (sting, cards, end card), extra dip while he talks
MUSIC_UNDER_VOICE, MUSIC_ALONE, DUCK = opt("MUSIC_UNDER_VOICE", -15.0), opt("MUSIC_ALONE", -3.0), opt("DUCK", 5.0)
TARGET = opt("TARGET_LENGTH", None)
H_ZOOM_BACK = opt("HORIZONTAL_TALKING_HEAD_ZOOM_BACK", 0.15)


def clip(name):
    """A clip by file name or by any unique tail of its stem ("IMG_0001.MOV", "IMG_0001", "0001")."""
    exact = os.path.join(FOOTAGE, name)
    if os.path.isfile(exact): return exact
    hits = sorted(glob.glob(os.path.join(FOOTAGE, glob.escape(name) + ".*")) or glob.glob(os.path.join(FOOTAGE, "*" + glob.escape(name) + ".*")))
    if not hits: raise FileNotFoundError(f"no clip '{name}' in {FOOTAGE}")
    return hits[0]
def run(cmd, **kw): return subprocess.run(cmd, check=True, **kw)
INTERVIEW = clip(E.INTERVIEW) if VOICE else None

# ---------------------------------------------------------------- TIMELINE
T_COLD = (COLD["cout"] - COLD["cin"]) if COLD else 0.0
T_HIT = (COLD["hit"] - COLD["cin"]) if COLD else None
STING = (T_COLD, T_COLD + STING_LEN) if LOGO_STING else None
T0 = STING[1] if STING else T_COLD

def split(a, b):
    """Source range minus CUTS, as a list of (a, b) parts."""
    parts = []
    for c0, c1 in CUTS:
        if a < c0 < b: parts.append((a, c0)); a = max(a, c1)
    return parts + [(a, b)]

def timeline():
    """Pieces [(name, src_in, src_out, out_start)], section starts, voice end."""
    t, tl, sec = T0, [], {}
    for i, (name, pieces) in enumerate(SECTIONS):
        t += AIR if (i or T0 > 0) else 0.12
        sec[name] = t
        for p in pieces:
            if p[0] == "gap": t += p[1]; continue
            for a, b in split(p[1], p[2]): tl.append((p[0], a, b, t)); t += b - a
    return tl, sec, t
if VOICE:
    TL, SEC, VOICE_END = timeline(); ORDER = [s for s, _ in SECTIONS]
else:                                            # footage-only: the parts and LENGTH set the timing
    assert LENGTH, "a footage-only edit needs LENGTH (seconds of picture before the end card)"
    TL, SEC, VOICE_END = [], {n: float(t) for n, t in PARTS}, float(LENGTH); ORDER = [n for n, _ in PARTS]
PICTURE_END = VOICE_END + END_HOLD
TOTAL = PICTURE_END + (END_CARD_LEN if END_CARD else 0.0)
if HOOK and VOICE: HOOK_END = SEC[ORDER[1]] - AIR / 2 if len(ORDER) > 1 else VOICE_END
elif HOOK: HOOK_END = T0 + float(HOOK.get("dur", 2.6))       # no voice: the hook's words land in rhythm
else: HOOK_END = None

def m(name, src):
    """Output time of a source time inside a named voice piece (a time inside a cut maps to the cut point)."""
    seg = [(a, b, o) for n, a, b, o in TL if n == name]
    if not seg: raise KeyError(name)
    assert seg[0][0] - 1e-6 <= src <= seg[-1][1] + 1e-6, (name, src, seg[0][0], seg[-1][1])
    for a, b, o in seg:
        if src <= b + 1e-6: return o + max(src, a) - a
def start(name): return [o for n, a, b, o in TL if n == name][0]
def end(name): return [o + b - a for n, a, b, o in TL if n == name][-1]
def nxt(name):
    """Output time at which the section after `name` begins (the voice end for the last one)."""
    i = ORDER.index(name); return SEC[ORDER[i + 1]] if i + 1 < len(ORDER) else VOICE_END

def S(label, clip_, cin, tend, keys, zk=None, punch=0.0, whip="", line="", fit="cover", sound=0.0):
    """A shot: label (first word = id), clip, clip in-point, OUTPUT time the shot ends, subject keys [(clip_t, cx, cy)],
    zoom keys [(clip_t, z)], punch = extra zoom that decays in 0.1 s after the cut, whip = "i"/"o" blur in/out,
    fit = "cover" (fill the frame, crop around the subject) or "contain" (whole clip over a blurred copy of itself),
    sound = footage-only edits: this shot's own sound in dB re SHOT_SOUND (None: silent)."""
    return dict(kind="clip", label=label, clip=clip_, cin=cin, tend=tend, keys=keys, zk=zk or [(cin, 1.0)], punch=punch,
                whip=whip, line=line, fit=fit, sound=sound)
def B(label, tend, line=""):
    """Black picture, under a full-screen graphic (logo sting, end card, quote card...)."""
    return dict(kind="black", label=label, clip=None, cin=0.0, tend=tend, keys=[(0.0, .5, .5)], zk=[(0.0, 1.0)], punch=0.0,
                whip="", line=line, fit="cover")
def SPLIT(label, before, after, tend, line=""):
    """Under a before-after card: before/after = (clip, clip_in, keys) fill the card's two windows."""
    return dict(kind="split", label=label, clip=None, cin=0.0, tend=tend, parts=[before, after], keys=[(0.0, .5, .5)],
                zk=[(0.0, 1.0)], punch=0.0, whip="", line=line, fit="cover")
def G(scene, at, dur=None, **p):
    """A graphic: scene id (python gfx.py list), OUTPUT start time, length in seconds, its words as keywords."""
    if scene not in gfx.SCENES: raise KeyError(f"unknown graphic '{scene}'; see python gfx.py list")
    return dict(scene=scene, t0=round(float(at), 3), dur=round(float(dur if dur is not None else gfx.SCENES[scene][0]), 3), p=p)

class Api: pass
api = Api()
for k, v in dict(m=m, start=start, end=end, nxt=nxt, S=S, B=B, SPLIT=SPLIT, G=G, SEC=SEC, VOICE_END=VOICE_END,
                 PICTURE_END=PICTURE_END, TOTAL=TOTAL, STING=STING, T_COLD=T_COLD, T_HIT=T_HIT, COLD=COLD,
                 HOOK_END=HOOK_END, INTERVIEW=opt("INTERVIEW", None), SOCIAL=SOCIAL, VOICE=VOICE).items(): setattr(api, k, v)
RAW_SHOTS = E.shots(api)
USER_GFX = list(E.graphics(api)) if hasattr(E, "graphics") else []

# ---------------------------------------------------------------- PICTURE
def cam(cin, keys, zk, dur, punch):
    """Smoothed camera path: time samples of the subject position (cx, cy) and zoom."""
    ts = np.arange(0, dur + 0.051, 0.05); src = cin + ts
    kt = [k[0] for k in keys]
    cx = np.interp(src, kt, [k[1] for k in keys]); cy = np.interp(src, kt, [k[2] for k in keys])
    z = np.interp(src, [k[0] for k in zk], [k[1] for k in zk])
    g = np.exp(-0.5 * (np.arange(-8, 9) / 3.5) ** 2); g /= g.sum()          # ~0.18 s gaussian: no hard corners
    sm = lambda v: np.convolve(np.pad(v, 8, mode="edge"), g, "valid")
    return (ts, sm(cx), sm(cy), sm(z) + punch * np.exp(-ts / 0.10))

def prepare(raw, orient):
    shots, f0 = [], 0
    for s in raw:
        sh = dict(s)
        if orient == "horizontal" and sh["kind"] == "clip" and clip(sh["clip"]) == INTERVIEW:   # 16:9 already frames him
            sh["zk"] = [(t, max(1.0, z - H_ZOOM_BACK)) for t, z in sh["zk"]]
        f1 = round(sh["tend"] * FPS); sh["n"] = f1 - f0; sh["t0"] = f0 / FPS; sh["dur"] = sh["n"] / FPS; f0 = f1
        assert sh["n"] > 0, f"shot {sh['label']} has no frames (ends before the previous one)"
        sh["path"] = cam(sh["cin"], sh["keys"], sh["zk"], sh["dur"], sh["punch"])
        if sh["kind"] == "split": sh["paths"] = [cam(c[1], c[2], [(c[1], 1.0)], sh["dur"], 0.0) for c in sh["parts"]]
        shots.append(sh)
    assert abs(f0 / FPS - TOTAL) < 0.04, f"last shot ends at {f0 / FPS:.2f}s, film is {TOTAL:.2f}s: end it at api.TOTAL"
    return shots
SHOTS = prepare(RAW_SHOTS, "vertical")
SH = {s["label"].split()[0]: s for s in SHOTS}

def pw(ts, vs, tol):
    """ffmpeg piecewise-linear expression of t through (ts, vs), thinned to within tol."""
    keep = [0]
    for i in range(1, len(ts) - 1):
        a = keep[-1]; pred = vs[a] + (vs[i + 1] - vs[a]) * (ts[i] - ts[a]) / (ts[i + 1] - ts[a])
        if abs(pred - vs[i]) > tol or ts[i] - ts[a] > 1.0: keep.append(i)
    keep.append(len(ts) - 1); e = f"{vs[keep[-1]]:.5f}"
    for a, b in reversed(list(zip(keep, keep[1:]))):
        e = f"if(lt(t,{ts[b]:.3f}),{vs[a]:.5f}+({(vs[b] - vs[a]) / (ts[b] - ts[a]):.6f})*(t-{ts[a]:.3f}),{e})"
    return e

_PROBE = {}
def probe(path):
    if path not in _PROBE:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=width,height,color_transfer:stream_side_data=rotation", "-of", "json", path],
                             capture_output=True, text=True).stdout
        s = json.loads(out)["streams"][0]; rot = next((int(d.get("rotation", 0)) for d in s.get("side_data_list", []) if "rotation" in d), 0)
        _PROBE[path] = (s["width"], s["height"], rot, s.get("color_transfer", "") or "")
    return _PROBE[path]
def shown(name):
    w, h, rot, trc = probe(clip(name))
    if name in NOROT: rot = 0
    return ((h, w) if rot % 180 else (w, h)), trc

def to_rgb(trc):
    """Colour step after the crop: phone HDR through the LUT, SDR as is; out comes 8-bit RGB (Rec.709)."""
    if trc == "arib-std-b67":
        return "scale=in_color_matrix=bt2020:in_range=tv,format=gbrp10le,lut3d=file=hlg2sdr.cube:interp=tetrahedral,format=gbrp"
    if trc == "smpte2084":
        return "scale=in_color_matrix=bt2020:in_range=tv,format=gbrp10le,lut3d=file=pq2sdr.cube:interp=tetrahedral,format=gbrp"
    return "scale=in_color_matrix=bt709,format=gbrp"

def framing(name, path, W, H, whip="", dur=0.0):
    """Scale + crop chain that fills W x H from the clip, following the camera path."""
    (sw, sh_), trc = shown(name); s = max(W / sw, H / sh_)
    ts, cx, cy, z = path; TY = 0.46 * H                 # TY: screen height at which the subject (cy) is held
    ex, ey, ez = pw(ts, cx, 0.0008), pw(ts, cy, 0.0008), pw(ts, z, 0.0015)
    blur = ""
    if "i" in whip: blur += "gblur=sigma=42:sigmaV=0:steps=1:enable='lt(t,0.085)',"
    if "o" in whip: blur += f"gblur=sigma=42:sigmaV=0:steps=1:enable='gt(t,{dur - 0.075:.3f})',"
    return (f"fps={FPS},format=yuv420p10le,"
            f"scale=w='2*ceil({sw * s:.2f}*({ez})/2)':h='2*ceil({sh_ * s:.2f}*({ez})/2)':eval=frame:flags=bicubic,"
            f"crop={W}:{H}:x='clip(({ex})*iw-{W / 2:.0f},0,iw-{W})':y='clip(({ey})*ih-{TY:.0f},0,ih-{H})',"
            f"{blur}unsharp=5:5:0.35:5:5:0,{to_rgb(trc)}")

def shot_graph(sh, k, W, H, orient, sc=1.0):
    """(ffmpeg input args, filtergraph lines) for one shot, ending in label [v<k>]."""
    n, dur, fin = sh["n"], sh["dur"], f"trim=end_frame={sh['n']},setpts=PTS-STARTPTS,setsar=1"
    black = ["-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={FPS}:d={dur + 0.5:.3f}"]
    def src(name, cin):
        return ["-ss", f"{cin:.3f}", "-t", f"{dur + 0.5:.3f}"] + (["-noautorotate"] if name in NOROT else []) + ["-i", clip(name)]
    if sh["kind"] == "black":
        return black, lambda i: [f"[{i}:v]format=gbrp,{fin}[v{k}]"]
    if sh["kind"] == "split":
        (ax, ay, aw, ah), (bx, by, bw, bh) = [[2 * round(v * sc / 2) for v in r] for r in gfx.BA_RECTS[orient]]; (ca, ia, _), (cb, ib, _) = sh["parts"]
        return black + src(ca, ia) + src(cb, ib), lambda i: [
            f"[{i + 1}:v]setpts=PTS-STARTPTS,{framing(ca, sh['paths'][0], aw, ah)}[a{k}]",
            f"[{i + 2}:v]setpts=PTS-STARTPTS,{framing(cb, sh['paths'][1], bw, bh)}[b{k}]",
            f"[{i}:v]format=gbrp[k{k}]", f"[k{k}][a{k}]overlay={ax}:{ay}:format=gbrp[ka{k}]",
            f"[ka{k}][b{k}]overlay={bx}:{by}:format=gbrp,{fin}[v{k}]"]
    if sh["fit"] == "contain":
        trc = shown(sh["clip"])[1]
        return src(sh["clip"], sh["cin"]), lambda i: [
            f"[{i}:v]setpts=PTS-STARTPTS,fps={FPS},format=yuv420p10le,split[p{k}][q{k}]",
            f"[p{k}]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},gblur=sigma=28,{to_rgb(trc)},"
            f"colorchannelmixer=rr=0.72:gg=0.72:bb=0.72[pb{k}]",
            f"[q{k}]scale={W}:{H}:force_original_aspect_ratio=decrease,{to_rgb(trc)}[qf{k}]",
            f"[pb{k}][qf{k}]overlay=x=(W-w)/2:y=(H-h)/2:format=gbrp,{fin}[v{k}]"]
    return src(sh["clip"], sh["cin"]), lambda i: [
        f"[{i}:v]setpts=PTS-STARTPTS,{framing(sh['clip'], sh['path'], W, H, sh['whip'], dur)},{fin}[v{k}]"]

# ---------------------------------------------------------------- WORDS AND CAPTIONS
def norm(w): return re.sub(r"[^a-z0-9']", "", w.lower().replace("’", "'"))
def shown_word(w): return re.sub(r"[^\w'’?!%$&+\-]", "", w).strip("-")

def source_words():
    """Interview words with source times [(t0, t1, word)]: WORDS (a transcribe.py --words csv) or Whisper run here once."""
    path = opt("WORDS", None)
    if path and not os.path.isabs(path): path = os.path.join(os.path.dirname(EDIT_PATH), path)
    if not path:
        path = os.path.join(WORK, "interview_words.csv")
        if not os.path.isfile(path):
            if DRY: return None
            os.makedirs(WORK, exist_ok=True); wav = os.path.join(WORK, "interview_16k.wav")
            run(["ffmpeg", "-v", "error", "-y", "-i", INTERVIEW, "-vn", "-ac", "1", "-ar", "16000", wav])
            whisper(wav, words=True, out_stem=path[:-4])
    out = []
    for r in csv.reader(open(path, encoding="utf-8", errors="replace")):
        try: a, b, w = int(r[0]) / 1000, int(r[1]) / 1000, r[2].strip()
        except (ValueError, IndexError): continue
        if w and not w.startswith("[") and norm(w) and norm(w) not in FILLERS: out.append((a, b, w))
    return align(out, interview_runs())

def runs_of(x, sr, bridge=0.12, shortest=0.08):
    """Stretches of speech [(start, end)] in a mono signal: 10 ms frames over a threshold set from the clip's own
    speech and noise levels; pauses shorter than `bridge` are bridged."""
    k = int(0.01 * sr); fr = x[:len(x) // k * k].reshape(-1, k); db = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-9)
    live = db[db > -90]
    if not len(live): return []
    on = db > max(np.percentile(live, 10) + 8, np.percentile(live, 90) - 25)
    runs, i, n = [], 0, len(on)
    while i < n:
        if on[i]:
            j = i
            while j < n and on[j]: j += 1
            if runs and i - runs[-1][1] < bridge * 100: runs[-1][1] = j
            else: runs.append([i, j])
            i = j
        else: i += 1
    return [(a / 100, b / 100) for a, b in runs if b - a >= shortest * 100]

def interview_runs():
    """Speech stretches in the interview (source times), measured once and cached in WORK."""
    path = os.path.join(WORK, "interview_runs.json")
    if os.path.isfile(path): return [tuple(r) for r in json.load(open(path, encoding="utf-8"))]
    from common import load_mono
    runs = runs_of(load_mono(INTERVIEW, 16000), 16000)
    os.makedirs(WORK, exist_ok=True); json.dump(runs, open(path, "w", encoding="utf-8"))
    return runs

def align(words, runs):
    """Whisper gives the words; the audio gives the timing. Whisper bunches the first words of a sentence onto one
    instant and drifts 0.2-0.5 s, so each word goes to the speech stretch nearest its Whisper time and the words of a
    stretch are spread over it by syllables (a comma or full stop adds a short pause)."""
    if not runs or not words: return words
    def syl(w): return max(1, len(re.findall(r"[aeiouy]+", norm(w))))
    # In-order assignment (dynamic programming): words keep their order across stretches, each sits as close as
    # possible to its Whisper time, and a move to the next stretch costs extra unless the previous word ends a phrase.
    ra_, rb_ = np.array([r[0] for r in runs]), np.array([r[1] for r in runs]); K = len(runs)
    mids = [(a + b) / 2 for a, b, _ in words]
    def dist(m): return np.maximum(0, np.maximum(ra_ - m, m - rb_))
    dp = dist(mids[0]); back = []
    for i in range(1, len(words)):
        pen = 0.0 if re.search(r"[,.;:?!]$", words[i - 1][2]) else 0.35
        stay_pen = 0.3 if re.search(r"[.?!]$", words[i - 1][2]) else 0.0                # a new sentence usually starts a new stretch
        best_prev = np.concatenate([[np.inf], np.minimum.accumulate(dp)[:-1]]) + pen     # any earlier stretch
        arg_prev = np.concatenate([[0], [int(np.argmin(dp[:k + 1])) for k in range(K - 1)]]) if K < 400 else None
        if arg_prev is None:                                                           # long interviews: windowed argmin
            run_min, run_arg, arg_prev = np.inf, 0, np.zeros(K, int)
            for k in range(1, K):
                if dp[k - 1] < run_min: run_min, run_arg = dp[k - 1], k - 1
                arg_prev[k] = run_arg
        stay = dp + stay_pen; choose_prev = best_prev < stay
        back.append(np.where(choose_prev, arg_prev, np.arange(K)))
        dp = np.where(choose_prev, best_prev, stay) + dist(mids[i])
    k = int(np.argmin(dp)); ks = [k]
    for bk in reversed(back): k = int(bk[k]); ks.append(k)
    ks.reverse()
    groups, keep = {}, []
    for (a, b, w), k, mid in zip(words, ks, mids):
        if dist(mid)[k] > 1.5: keep.append((a, b, w))            # no stretch near it: trust Whisper's own time
        else: groups.setdefault(k, []).append(w)
    out = []
    for k in sorted(groups):
        ra, rb = runs[k]; ws = groups[k]
        weights = [syl(w) for w in ws]; pauses = [0.8 if re.search(r"[,.;:?!]$", w) else 0.0 for w in ws]
        total = sum(weights) + sum(pauses[:-1]); acc = 0.0
        for w, wt, pz in zip(ws, weights, pauses):
            t0 = ra + (rb - ra) * acc / total; t1 = ra + (rb - ra) * (acc + wt) / total
            out.append((round(t0, 3), round(t1, 3), w)); acc += wt + pz
    return sorted(out + keep)

def output_words(src):
    """Source words placed on the output timeline (words inside CUTS or outside the pieces drop out), fixes applied."""
    res = []
    for n, a, b, o in TL:
        for w0, w1, w in src:
            if a - 0.05 <= w0 < b - 0.03: res.append(dict(t0=o + max(0.0, w0 - a), t1=o + min(b - a, max(w1, w0 + 0.05) - a), w=w))
    res.sort(key=lambda d: d["t0"])
    fixes = {k.lower(): v for k, v in opt("CAPTION_FIXES", {}).items()}
    for key, rep in fixes.items():              # one word or a phrase -> replacement (times spread over the match)
        kw, i = [norm(x) for x in key.split()], 0
        while i <= len(res) - len(kw):
            if [norm(r["w"]) for r in res[i:i + len(kw)]] == kw:
                t0, t1, new = res[i]["t0"], res[i + len(kw) - 1]["t1"], rep.split()
                res[i:i + len(kw)] = [dict(t0=t0 + (t1 - t0) * j / len(new), t1=t0 + (t1 - t0) * (j + 1) / len(new), w=x) for j, x in enumerate(new)]
                i += len(new)
            else: i += 1
    return res

def speech_runs(voice):
    """Stretches of speech in the output voice track [(start, end)] (output times)."""
    return runs_of(voice.mean(1), SR)

WEAK = {"a", "an", "the", "of", "to", "and", "or", "but", "in", "on", "at", "for", "with", "my", "her", "his", "their",
        "our", "your", "is", "was", "i", "we", "you", "she", "he", "they", "it", "that", "so", "if"}

def phrase_chunks(ws, most=3, chars=18):
    """Split one phrase into caption chunks of up to `most` words / `chars` characters: evenly sized chunks, no lone
    words, and no chunk ending on a small word ("a", "the", "her") when that can be avoided."""
    n = len(ws); best = [0.0] + [math.inf] * n; prev = [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(max(0, j - most), j):
            seg = ws[i:j]; ln = sum(len(shown_word(x["w"])) + 1 for x in seg) - 1
            if ln > chars and j - i > 1: continue
            c = 0.5 * (most - len(seg)) ** 2 + (2.0 if len(seg) == 1 and n > 1 else 0) + (1.0 if j < n and norm(seg[-1]["w"]) in WEAK else 0)
            if best[i] + c < best[j]: best[j], prev[j] = best[i] + c, i
    out, j = [], n
    while j > 0: out.append(ws[prev[j]:j]); j = prev[j]
    return out[::-1]

def caption_chunks(words, blocked, runs=None):
    """Words -> caption chunks, broken at punctuation and pauses; a chunk that starts a phrase is snapped onto the
    measured speech onset of the finished voice track."""
    words = [w for w in words if not any(a <= w["t0"] < b for a, b in blocked)]
    phrases, cur = [], []
    for i, w in enumerate(words):
        if cur and w["t0"] - words[i - 1]["t1"] > 0.3: phrases.append(cur); cur = []
        cur.append(w)
        if re.search(r"[.?!,;:]$", w["w"]): phrases.append(cur); cur = []
    if cur: phrases.append(cur)
    out = []
    for ph in phrases:
        d = 0.0
        for j, c in enumerate(phrase_chunks([x for x in ph if shown_word(x["w"])])):
            ws = [dict(w=shown_word(x["w"]), t0=x["t0"]) for x in c]
            if runs and j == 0:                  # only a phrase's first chunk snaps; the rest of the phrase follows it
                near = [a for a, b in runs if abs(a - ws[0]["t0"]) <= 0.35]
                if near: d = min(near, key=lambda a: abs(a - ws[0]["t0"])) - ws[0]["t0"]
            for x in ws: x["t0"] += d
            if out and ws[0]["t0"] < out[-1]["t0"] + 0.15:                  # never before (or on) the previous chunk
                sh = out[-1]["t0"] + 0.15 - ws[0]["t0"]
                for x in ws: x["t0"] += sh
            out.append(dict(t0=ws[0]["t0"], t1=c[-1]["t1"] + d + 0.35, words=ws))
    for a, b in zip(out, out[1:]): a["t1"] = min(a["t1"], b["t0"])
    for c in out: c["t1"] = max(c["t1"], c["t0"] + 0.3)
    return out

def hook_times(lines, words, t_start):
    """Each hook word lands when it is spoken: match the hook's words to the spoken ones in order."""
    hw = [norm(w) for ln in lines for w in str(ln).replace("*", "").split()]
    spoken = [(norm(w["w"]), w["t0"]) for w in words]; times, j = [], 0
    for x in hw:
        k = next((i for i in range(j, len(spoken)) if spoken[i][0] == x), None)
        if k is None: times.append(None)
        else: times.append(spoken[k][1] - t_start); j = k + 1
    known = [(i, t) for i, t in enumerate(times) if t is not None]
    if len(known) < max(1, len(hw) // 2): return None
    for i, t in enumerate(times):                # unmatched words: in step between their neighbours
        if t is None:
            prev = max((kt for ki, kt in known if ki < i), default=0.0); nx = min((kt for ki, kt in known if ki > i), default=prev + 0.3)
            times[i] = prev + 0.5 * (nx - prev)
    return [max(0.0, min(t, times[-1])) for t in times]

# ---------------------------------------------------------------- GRAPHICS TRACK
def graphics_events(words=None, runs=None):
    ev = []
    if STING: ev.append(G("logo-sting", STING[0], STING_LEN))
    ev += USER_GFX
    if END_CARD: ev.append(G("end-card", PICTURE_END, END_CARD_LEN, **opt("END_CARD_WORDS", {})))
    if HOOK:
        t_start = (0.0 if T0 == 0 else SEC[ORDER[0]] - AIR) if VOICE else T0
        hw = [w for w in (words or []) if t_start <= w["t0"] < HOOK_END]
        p = dict(lines=HOOK["lines"]); ht = hook_times(HOOK["lines"], hw, t_start) if hw else None
        if ht: p["times"] = ht
        ev.append(G("hook", t_start, HOOK_END - t_start, **p))
    blocked = [(e["t0"], e["t0"] + e["dur"]) for e in ev if gfx.SCENES[e["scene"]][1] or e["scene"] == "hook"]
    avoid = [[e["t0"], e["t0"] + e["dur"]] for e in ev if e["scene"] == "lower-third"]
    if CAPTIONS and VOICE and words is not None:
        ev.append(G("captions", 0.0, TOTAL, chunks=caption_chunks(words, blocked, runs), avoid=avoid))
    elif CAPTIONS and not VOICE:
        ev.append(G("captions", 0.0, TOTAL, chunks=text_chunks(blocked), avoid=avoid))
    return ev

def text_chunks(blocked):
    """Footage-only captions: each CAPTION_TEXT line is one caption; the light-blue box walks its words at reading pace."""
    out = []
    for a, b, txt in CAPTION_TEXT:
        if any(x <= a < y for x, y in blocked): print(f"WARNING: caption at {a:.2f} s sits under a card or the hook: move it"); continue
        ws = [w.replace("*", "") for w in str(txt).split() if shown_word(w)]          # written lines keep their punctuation
        step = min(0.24, max(0.1, (b - a) * 0.5 / max(1, len(ws))))
        out.append(dict(t0=float(a), t1=float(b), words=[dict(w=w, t0=float(a) + i * step) for i, w in enumerate(ws)]))
    return out

def graphics_frames(orient, events):
    """Draw the graphics track for one format (cached: redrawn only when the graphics or motion/ change)."""
    W, H = gfx.SIZE[orient]; job = dict(W=W, H=H, n=round(TOTAL * FPS), fps=FPS, events=events, grain=False, scale=PSCALE)
    h = hashlib.sha1(json.dumps(job, sort_keys=True).encode())
    for f in sorted(glob.glob(os.path.join(gfx.MOTION, "**", "*"), recursive=True)):
        if os.path.isfile(f): h.update(f.encode()); h.update(open(f, "rb").read())
    out = os.path.join(WORK, f"gfx_{orient}{SUFFIX}"); key = os.path.join(out, "key.txt")
    if os.path.isfile(key) and open(key, encoding="utf-8").read() == h.hexdigest() and len(glob.glob(os.path.join(out, "f_*.png"))) == job["n"]:
        print(f"graphics ({orient}): unchanged, reused"); return out, h.hexdigest()
    if os.path.isdir(out):
        for f in glob.glob(os.path.join(out, "f_*.png")): os.remove(f)
    gfx.render(job, out)
    open(key, "w", encoding="utf-8").write(h.hexdigest())
    return out, h.hexdigest()

# ---------------------------------------------------------------- CHECKS
def warnings(events):
    w = []
    for sh in SHOTS:
        names = [sh["clip"]] if sh["kind"] == "clip" else [c[0] for c in sh.get("parts", [])]
        for name in names:
            (wd, ht), _ = shown(name)
            if sh["kind"] == "clip" and sh["fit"] == "cover" and abs(wd / ht - 16 / 9) > 0.02 and abs(wd / ht - 9 / 16) > 0.02:
                w.append(f"{name}: plays as {wd}x{ht} (not 16:9 or 9:16): check the framing, or a wrong rotation flag (NOROT)")
    for sh in SHOTS:                                    # on-camera shots must show the words being heard
        if sh["kind"] != "clip" or clip(sh["clip"]) != INTERVIEW: continue
        t0, t1 = sh["t0"], sh["t0"] + sh["dur"]; tq = t0 + 0.5 / FPS
        cur = next(((n, a, b2, o) for n, a, b2, o in TL if o - 1e-6 <= tq < o + b2 - a), None) or \
              next(((n, a, b2, o) for n, a, b2, o in TL if o > tq), None)
        if cur:
            want = cur[1] + (t0 - cur[3])
            if abs(want - sh["cin"]) > 0.04:
                w.append(f"{sh['label'].split()[0]} is out of sync with the voice by {sh['cin'] - want:+.2f} s: set its clip_in to {want:.2f}")
        for (n1, a1, b1, o1), (n2, a2, b2, o2) in zip(TL, TL[1:]):
            j = o1 + b1 - a1
            if t0 + 0.02 < j < t1 - 0.02 and abs(a2 - (b1 + (o2 - j))) > 0.01:
                w.append(f"{sh['label'].split()[0]} runs across a cut in the voice at {j:.2f} s: end it there and continue in a new shot")
    for e in events:
        if e["t0"] < -0.01 or e["t0"] + e["dur"] > TOTAL + 0.05:
            w.append(f"graphic {e['scene']} at {e['t0']:.2f}-{e['t0'] + e['dur']:.2f} s runs outside the film (0-{TOTAL:.2f} s)")
    cards = [e for e in events if gfx.SCENES[e["scene"]][1]]
    for a, b in zip(cards, cards[1:]):
        if b["t0"] < a["t0"] + a["dur"] - 0.01: w.append(f"cards {a['scene']} and {b['scene']} overlap")
    if TARGET and abs(TOTAL - TARGET) > 0.1 * TARGET:
        w.append(f"film is {TOTAL:.1f} s, the user asked for about {TARGET:.0f} s: add or drop answers (never pad)")
    if SOCIAL and TOTAL > 62: w.append(f"social edit is {TOTAL:.1f} s: keep it within 30-60 s")
    if not SOCIAL and TOTAL > 110: w.append(f"film is {TOTAL:.1f} s: over the 1:45 ceiling of this style (+ end card)")
    if SOCIAL and not HOOK: w.append("social edit without HOOK: the first two seconds need the hook line as big type")
    for (n, a, b, o) in TL:
        if a < TONE + 0.6 and b > TONE: w.append(f"piece {n} overlaps the room-tone span {TONE}-{TONE + 0.6:.2f}: fine only if that stretch is silent")
    return w

# ---------------------------------------------------------------- SOUND
def stem(src_path, a, b):
    raw = os.path.join(WORK, "tmp.wav")
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", src_path, "-vn", "-ar", str(SR), "-ac", "2", raw])
    return wavfile.read(raw)[1].astype(np.float64) / 32768.0

def build_voice():
    if not VOICE: return np.zeros((int(TOTAL * SR), 2))
    raw = os.path.join(WORK, "interview48.wav")
    extract_clean(INTERVIEW, raw, SR, **opt("DENOISE", dict(gmin_db=-24.0, beta=1.7)))
    x = wavfile.read(raw)[1].astype(np.float64) / 32768.0
    h, nx = XF / 2, int(XF * SR); n = int(TOTAL * SR)
    buf = np.zeros((n + SR, 2)); ramp = np.linspace(0, 1, nx)[:, None]
    def put(a, b, o):
        c = x[int(round((a - h) * SR)):int(round((b + h) * SR))].copy(); c[:nx] *= ramp; c[-nx:] *= ramp[::-1]
        s = int(round((o - h) * SR)); buf[s:s + len(c)] += c
    for (n1, a, b, o), nx_ in zip(TL, TL[1:] + [None]):
        put(a, b, o)
        gap = (nx_[3] - (o + b - a)) if nx_ else 0.0
        t = o + b - a
        while gap > 0.01:                                           # room tone across gaps so the voice bed never drops out
            d = min(gap, 0.55); put(TONE, TONE + d, t); t += d; gap -= d
    mono = x.mean(1)
    def lvl(t): g = mono[int((t - .015) * SR):int((t + .015) * SR)]; return 20 * np.log10(np.sqrt((g ** 2).mean()) + 1e-9)
    edges = [f"{n} {lvl(a):.0f}/{lvl(b):.0f}" + (" <-- on a sound" if max(lvl(a), lvl(b)) > -40 else "") for n, a, b, _ in TL]
    print("level at each voice piece's in/out edge (dB; above about -40 means the cut lands on a sound):\n  " + "\n  ".join(edges))
    sos = signal.butter(2, 80, "hp", fs=SR, output="sos")
    return signal.sosfilt(sos, buf[:n], axis=0)

def shot_sound():
    """Footage-only edits: every shot's own sound at its place, levelled to about -26 dBFS (+ SHOT_SOUND + the shot's
    `sound`), 30 ms fades at the cuts. Boost is capped at +12 dB so a quiet clip's hiss is not pumped up."""
    y = np.zeros((int(TOTAL * SR), 2))
    if VOICE or SHOT_SOUND is None: return y
    f = int(0.03 * SR); ramp = np.linspace(0, 1, f)[:, None]
    for sh in SHOTS:
        if sh["kind"] != "clip" or sh.get("sound", 0.0) is None: continue
        try: x = stem(clip(sh["clip"]), sh["cin"], sh["cin"] + sh["dur"])
        except subprocess.CalledProcessError: continue                       # a clip without sound
        if len(x) < 2 * f: continue
        rms = np.sqrt((x ** 2).mean()) + 1e-9
        g = min(10 ** (12 / 20), 10 ** ((-26 + SHOT_SOUND + sh.get("sound", 0.0)) / 20) / rms)
        x = x * g; x[:f] *= ramp; x[-f:] *= ramp[::-1]
        i = int(round(sh["t0"] * SR)); y[i:i + len(x)] += x[:len(y) - i]
    return y

def build_nat():
    y = np.zeros((int(TOTAL * SR), 2)); f = int(0.03 * SR); ramp = np.linspace(0, 1, f)[:, None]
    for c, a, b, o, g in (E.nat(api, SH) if hasattr(E, "nat") else []):
        s = stem(clip(c), a, b); s[:f] *= ramp; s[-f:] *= ramp[::-1]
        i = int(o * SR); y[i:i + len(s)] += s[:len(y) - i] * 10 ** (g / 20)
    return y

def loudness(path):
    lo = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float([l for l in lo.splitlines() if l.strip().startswith("I:")][-1].split()[1])

def cue_sheet(events, active):
    """What music.py needs to score the cut."""
    return dict(total=TOTAL, sr=SR, voice_end=VOICE_END, picture_end=PICTURE_END, sections=[(s, SEC[s]) for s in ORDER],
                energy=ENERGY, lift=opt("LIFT", None), cold=(0.0, T_COLD, T_HIT) if COLD else None, sting=STING,
                hook=(0.0, HOOK_END) if HOOK else None, end_card=(PICTURE_END, TOTAL) if END_CARD else None,
                cards=[(e["t0"], e["t0"] + e["dur"], e["scene"]) for e in events if gfx.SCENES[e["scene"]][1] and e["scene"] not in ("logo-sting", "end-card")],
                overlays=[(e["t0"], e["scene"]) for e in events if e["scene"] in ("lower-third", "title")],
                voice_active=active, frame=0.02, social=SOCIAL, seed=opt("MUSIC_SEED", 1), voice=VOICE,
                cuts=[sh["t0"] for sh in SHOTS[1:] if not any(c0 - 0.05 <= sh["t0"] <= c1 + 0.05 for c0, c1, _ in
                      [(e["t0"], e["t0"] + e["dur"], 0) for e in events if gfx.SCENES[e["scene"]][1]])])

def build_audio(voice, events):
    os.makedirs(WORK, exist_ok=True)
    if not VOICE: return footage_audio(events, len(voice))
    wavfile.write(os.path.join(WORK, "voice_raw.wav"), SR, (np.clip(voice, -1, 1) * 32767).astype(np.int16))
    vg = 10 ** ((LUFS - loudness(os.path.join(WORK, "voice_raw.wav"))) / 20); voice = voice * vg
    k = int(0.02 * SR); fr = voice.mean(1)[:len(voice) // k * k].reshape(-1, k); rms = np.sqrt((fr ** 2).mean(1))
    active = rms > 10 ** (-32 / 20)                                 # speech frames (after gain)
    speech_db = 20 * np.log10(np.sqrt((fr[active] ** 2).mean()))
    n = len(voice); music = np.zeros((n, 2)); fx = np.zeros((n, 2))
    if MUSIC_STYLE:
        import music as score
        bed, fxt = score.render(MUSIC_STYLE, cue_sheet(events, active))
        bed, fxt = bed[:n], fxt[:n]
        # the bed sits at the speech level minus MUSIC_UNDER_VOICE, ducks DUCK more while he speaks, rises where nobody speaks
        act = np.repeat(active, k)[:n].astype(float); act = np.pad(act, (0, n - len(act)))
        a_up, a_dn = math.exp(-1 / (0.06 * SR)), math.exp(-1 / (0.35 * SR))
        sm = signal.lfilter([1 - a_dn], [1, -a_dn], np.maximum(act, signal.lfilter([1 - a_up], [1, -a_up], act)))
        t = np.arange(n) / SR; first = SEC[ORDER[0]]
        alone = ((t < first - 0.2) | (t > VOICE_END + 0.1)).astype(float)
        if COLD: alone[:int(T_COLD * SR)] *= 0.45                     # under the cold open the natural sound leads
        for c0, c1, _ in cue_sheet(events, active)["cards"]: alone = np.maximum(alone, ((t > c0) & (t < c1)).astype(float) * (1 - np.clip(sm, 0, 1)))
        alone = signal.lfilter([1 - a_dn], [1, -a_dn], alone)
        gdb = MUSIC_UNDER_VOICE - DUCK * np.clip(sm, 0, 1) + (MUSIC_ALONE - MUSIC_UNDER_VOICE) * alone
        ref = np.sqrt((bed[int(first * SR):int(VOICE_END * SR)] ** 2).mean()) + 1e-12
        music = bed * (10 ** (speech_db / 20) / ref) * (10 ** (gdb / 20))[:, None]
        fref = np.abs(fxt).max() + 1e-12                               # transitions: loudest hit 2 dB under the speech peak
        fx = fxt * (10 ** ((speech_db + 9.0) / 20) / fref) * (1 - 0.45 * np.clip(sm, 0, 1))[:, None]
    nat = build_nat()[:n]
    mix = voice + music + fx + nat
    for nm, s in (("voice", voice), ("music", music), ("fx", fx), ("nat", nat), ("mix", mix)):
        wavfile.write(os.path.join(WORK, f"{nm}.wav"), SR, s.astype(np.float32))
    if MUSIC_STYLE:
        bed = music + fx + nat; bfr = bed.mean(1)[:n // k * k].reshape(-1, k); brms = np.sqrt((bfr ** 2).mean(1)) + 1e-9
        ratio = 20 * np.log10(rms[active] / brms[active])
        print(f"mix: speech {speech_db:.1f} dBFS; voice over music while he speaks: median {np.median(ratio):.1f} dB, "
              f"worst 5% {np.percentile(ratio, 5):.1f} dB; music style {MUSIC_STYLE}")
    return os.path.join(WORK, "mix.wav")

def footage_audio(events, n):
    """No voice: the shots' own sound and natural-sound windows, with the music leading once MUSIC_STYLE is set;
    the whole mix is brought to LUFS."""
    sound = shot_sound()[:n] + build_nat()[:n]; music = np.zeros((n, 2)); fx = np.zeros((n, 2))
    if MUSIC_STYLE:
        import music as score
        bed, fxt = score.render(MUSIC_STYLE, cue_sheet(events, np.zeros(int(TOTAL / 0.02), bool)))
        bed, fxt = bed[:n], fxt[:n]
        ref = np.sqrt((bed[:int(PICTURE_END * SR)] ** 2).mean()) + 1e-12
        music = bed * (10 ** (-18 / 20) / ref)                            # the music leads; the shots' sound sits under it
        fx = fxt * (10 ** (-8 / 20) / (np.abs(fxt).max() + 1e-12))
        sound = sound * 10 ** (-6 / 20)
    mix = music + fx + sound
    path = os.path.join(WORK, "mix.wav")
    wavfile.write(path, SR, mix.astype(np.float32))
    if np.abs(mix).max() > 0:
        target = LUFS if MUSIC_STYLE else LUFS - 6                         # a draft without music stays a little quieter
        mix = mix * 10 ** ((target - loudness(path)) / 20)
    for nm, x in (("music", music), ("fx", fx), ("sound", sound), ("mix", mix)):
        wavfile.write(os.path.join(WORK, f"{nm}.wav"), SR, x.astype(np.float32))
    print(f"mix: footage-only; music {MUSIC_STYLE or 'none (draft)'}; shots' own sound {'off' if SHOT_SOUND is None else 'on'}")
    return path

# ---------------------------------------------------------------- RENDER
def ffmpeg_graph(cmd_head, graph_file, cmd_tail, cwd):
    """Run ffmpeg with the filtergraph read from a file (-/filter_complex on ffmpeg 7+, -filter_complex_script before)."""
    try:
        run(cmd_head + ["-/filter_complex", graph_file] + cmd_tail, cwd=cwd, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        if "filter_complex" in (e.stderr or "") and ("Unrecognized option" in e.stderr or "not found" in e.stderr):
            run(cmd_head + ["-filter_complex_script", graph_file] + cmd_tail, cwd=cwd)
        else:
            sys.stderr.write((e.stderr or "")[-3000:]); raise

SHOT_VERSION = "1"   # bump when the shot pipeline changes, so cached shots are rebuilt

def render_shot(sh, k, W, H, orient, sdir):
    """One shot -> its own near-lossless file (cached: only shots whose recipe changed are rendered again)."""
    args, lines = shot_graph(sh, 0, W, H, orient, PSCALE)
    graph = ";\n".join(lines(0) + ["[v0]scale=out_color_matrix=bt709:out_range=tv,format=yuv444p[out]"])
    key = hashlib.sha1((SHOT_VERSION + orient + json.dumps(args) + graph + str(sh["n"])).encode()).hexdigest()[:12]
    out = os.path.join(sdir, f"s{k:03d}_{key}.mp4")
    if os.path.isfile(out): return out, False
    gpath = os.path.join(sdir, f"s{k:03d}_{key}.txt"); open(gpath, "w", encoding="utf-8", newline="\n").write(graph)
    tmp = out[:-4] + ".part.mp4"
    ffmpeg_graph(["ffmpeg", "-v", "error", "-y", "-threads", "2"] + args, gpath,
                 ["-map", "[out]", "-frames:v", str(sh["n"]), "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
                  "-crf", "10", "-pix_fmt", "yuv444p", "-g", str(FPS), "-an", tmp], cwd=WORK)
    os.replace(tmp, out); os.remove(gpath)
    return out, True

def render_picture(orient, gfx_dir, gfx_key, events):
    W, H = [2 * round(v * PSCALE / 2) for v in gfx.SIZE[orient]]; shots = prepare(RAW_SHOTS, orient)
    sdir = os.path.join(WORK, f"shots_{orient}{SUFFIX}"); os.makedirs(sdir, exist_ok=True)
    lut.write_cube(os.path.join(WORK, "hlg2sdr.cube")); lut.write_cube(os.path.join(WORK, "pq2sdr.cube"), pq=True)
    from concurrent.futures import ThreadPoolExecutor
    t0 = __import__("time").time()
    with ThreadPoolExecutor(max_workers=max(1, (os.cpu_count() or 2) // 2)) as ex:
        res = list(ex.map(lambda a: render_shot(a[1], a[0], W, H, orient, sdir), enumerate(shots)))
    files, made = [r[0] for r in res], sum(r[1] for r in res)
    for f in glob.glob(os.path.join(sdir, "s*.mp4")):                 # shots no longer in the edit
        if f not in files: os.remove(f)
    print(f"picture ({orient}): {made} of {len(shots)} shots rendered ({len(shots) - made} unchanged) in {__import__('time').time() - t0:.0f} s")
    lst = os.path.join(sdir, "list.txt")
    with open(lst, "w", encoding="utf-8", newline="\n") as f:
        f.write("ffconcat version 1.0\n" + "".join(f"file '{os.path.basename(p)}'\n" for p in files))
    out = os.path.join(WORK, f"picture_{orient}{SUFFIX}.mp4")
    cards = [(e["t0"], e["t0"] + e["dur"]) for e in events if gfx.SCENES[e["scene"]][1]]
    grain = (",noise=c0s=7:c0f=t+u:enable='" + "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in cards) + "'") if cards else ""
    graph = ";\n".join([f"[0:v]setpts=N/({FPS}*TB),scale=in_color_matrix=bt709:in_range=tv,format=gbrp[base]",
                        f"[1:v]setpts=N/({FPS}*TB),format=rgba[g]",
                        "[base][g]overlay=format=gbrp:eof_action=pass[ov]",
                        f"[ov]scale=out_color_matrix=bt709:out_range=tv,format=yuv420p{grain},"
                        "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709[v]"])
    n = round(TOTAL * FPS)
    # capped bitrate: footage plus card grain otherwise runs near 30 Mbit/s (140 MB for 40 s); 12 Mbit/s is plenty for social
    quality = (["-preset", "veryfast", "-crf", "23", "-maxrate", "4M", "-bufsize", "8M"] if PREVIEW
               else ["-preset", "faster", "-crf", "18", "-maxrate", "12M", "-bufsize", "24M"])
    key = hashlib.sha1(("".join(files) + graph + gfx_key + json.dumps(quality)).encode()).hexdigest()
    if os.path.isfile(out) and os.path.isfile(out + ".key") and open(out + ".key", encoding="utf-8").read() == key:
        print(f"picture ({orient}): unchanged, reused"); return out
    gpath = os.path.join(WORK, f"graph_{orient}{SUFFIX}.txt"); open(gpath, "w", encoding="utf-8", newline="\n").write(graph)

    ffmpeg_graph(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-framerate", str(FPS),
                  "-i", os.path.join(gfx_dir, "f_%05d.png")], gpath,
                 ["-map", "[v]", "-frames:v", str(n), "-r", str(FPS), "-c:v", "libx264"] + quality + [
                  "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                  "-color_range", "tv", "-an", "-movflags", "+faststart", out], cwd=WORK)
    open(out + ".key", "w", encoding="utf-8").write(key)
    return out

def mux(orient, picture, mix):
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"{OUTPUT}_{orient}" + ("_preview" if PREVIEW else "" if MUSIC_STYLE else "_nomusic") + ".mp4")
    run(["ffmpeg", "-v", "error", "-y", "-i", picture, "-i", mix, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-af", f"alimiter=limit={10 ** (PEAK / 20):.3f}:level=false:attack=5:release=60,aresample=48000",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", out])
    print("->", out); return out

def main():
    print(f"{'out':>13}  {'dur':>5}  shot")
    for sh in SHOTS:
        print(f"{sh['t0']:6.2f}-{sh['t0'] + sh['dur']:5.2f}  {sh['dur']:5.2f}  {sh['label']}  "
              + (f"[{sh['clip']} {sh['cin']:.2f}-{sh['cin'] + sh['dur']:.2f}]" if sh["kind"] == "clip" else f"[{sh['kind']}]")
              + (f"\n{'':22}{sh['line']}" if sh["line"] else ""))
    src = source_words() if VOICE and (CAPTIONS or HOOK) else None
    words = output_words(src) if src is not None else None
    events = graphics_events(words)
    print("graphics:")
    for e in sorted(events, key=lambda e: e["t0"]):
        if e["scene"] == "captions": continue
        txt = {k: v for k, v in e["p"].items() if k not in ("times", "chunks", "avoid")}
        print(f"  {e['t0']:6.2f}-{e['t0'] + e['dur']:6.2f}  {e['scene']:<12} {json.dumps(txt, ensure_ascii=False)[:110]}")
    if CAPTIONS:
        ch = next((e for e in events if e["scene"] == "captions"), None)
        if ch is None: print("captions: on; the interview is transcribed at the first render")
        else:
            print(f"captions: {len(ch['p']['chunks'])} chunks (check the words; fix with CAPTION_FIXES):")
            for c in ch["p"]["chunks"]: print(f"  {c['t0']:6.2f}  {' '.join(w['w'] for w in c['words'])}")
    print(f"edit: {EDIT_TYPE}; formats: {', '.join(ORIENTS)}; music: {MUSIC_STYLE or 'none (draft)'}; "
          f"cold open: {'yes' if COLD else 'no'}; logo sting: {'yes' if STING else 'no'}; end card: {'yes' if END_CARD else 'no'}"
          + (f"; target {TARGET:.0f} s" if TARGET else ""))
    print(f"total {TOTAL:.2f}s; sections: " + ", ".join(f"{k} {v:.2f}" for k, v in SEC.items()))
    for w in warnings(events): print("WARNING:", w)
    if DRY: return
    os.makedirs(WORK, exist_ok=True)
    voice = build_voice()
    if CAPTIONS:
        runs = speech_runs(voice); events = graphics_events(words, runs)
        ch = next(e for e in events if e["scene"] == "captions")
        with open(os.path.join(WORK, "captions.txt"), "w", encoding="utf-8") as f:
            for c in ch["p"]["chunks"]: f.write(f"{c['t0']:7.2f}-{c['t1']:6.2f}  {' '.join(w['w'] for w in c['words'])}\n")
        print("captions ->", os.path.join(WORK, "captions.txt"))
    mix = build_audio(voice, events)
    for o in ORIENTS:
        pic = os.path.join(WORK, f"picture_{o}{SUFFIX}.mp4")
        if AUDIO_ONLY:
            if not os.path.isfile(pic): sys.exit(f"--audio needs a rendered picture first ({pic}); run without --audio")
        else:
            gdir, gkey = graphics_frames(o, events); pic = render_picture(o, gdir, gkey, events)
        mux(o, pic, mix)

if __name__ == "__main__":
    main()
