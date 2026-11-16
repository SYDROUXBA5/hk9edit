#!/usr/bin/env python3
"""Background music scored to a finished edit, synthesised here: no samples, nothing licensed, works offline.

Usage:  python music.py styles                         the styles and what each one suits
        python music.py demo STYLE OUT.wav [--seconds 40]   a style on a made-up cut, to hear it on its own
Module: render(style, cues) -> (bed, fx), stereo float arrays at cues["sr"]; build.py passes the edit's cue sheet.

How it scores the cut
  grid     the tempo stays within a few percent of the style's own, but is bent between anchors so that each one lands
           on a downbeat: the cold open's hit, the logo sting, the hook's cut, every section start, every card, the end card
  arrange  layers follow ENERGY per section (0 = pad only ... 3 = full), LIFT is the section that gets the full
           arrangement and a crash; the close steps down; under the end card the last chord rings out
  fx       a separate track: whoosh into each card and cut, impact on the sting, the cards and the end card, a riser
           into the lift, a soft tick when a name tag or title lands
"""
import math, os, sys
import numpy as np
from scipy import signal
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

STYLES = {
    "tactical": dict(name="Driving tactical", bpm=124, root=40, scale="minor", prog=[0, 5, 2, 6],
                     suits="police K9, detection, protection and bite work: dark, tense, driving pulse"),
    "cinematic": dict(name="Cinematic pulse", bpm=100, root=38, scale="minor", prog=[0, 5, 3, 4],
                      suits="serious testimonials and hard-won results: strings ostinato, big drums, weight"),
    "uplifting": dict(name="Uplifting modern", bpm=116, root=38, scale="major", prog=[0, 4, 5, 3],
                      suits="students, success stories, family dogs, puppy progress: bright plucks, light four-on-the-floor"),
    "warm": dict(name="Warm and gentle", bpm=84, root=43, scale="major", prog=[0, 5, 3, 4],
                 suits="service dogs, behaviour rehab, emotional stories: electric piano, soft pads, no big drums"),
    "groove": dict(name="Modern groove", bpm=90, root=45, scale="minor", prog=[0, 5, 2, 6],
                   suits="social posts, day-in-the-life, lighter moments: laid-back hip-hop drums, mellow keys"),
}
SCALES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10]}


def hz(n): return 440.0 * 2 ** ((n - 69) / 12)


class Score:
    def __init__(self, n, sr, seed):
        self.sr, self.n = sr, n
        self.bus = {k: np.zeros((n + 4 * sr, 2)) for k in ("pad", "keys", "bass", "drums", "perc", "fx")}
        self.rng = np.random.default_rng(seed); self._cache = {}

    def add(self, bus, t, sig, gain=1.0, pan=0.0):
        i = int(round(t * self.sr))
        if i >= self.n + 3 * self.sr or gain <= 0: return
        if sig.ndim == 1: sig = np.stack([sig * math.sqrt(0.5 * (1 - pan)), sig * math.sqrt(0.5 * (1 + pan))], 1) * 1.414
        if i < 0: sig, i = sig[-i:], 0
        b = self.bus[bus]; m = min(len(sig), len(b) - i)
        if m > 0: b[i:i + m] += sig[:m] * gain

    # ------------------------------------------------------------ sources
    def env(self, n, a=0.005, d=None, r=0.05, sustain=1.0):
        sr = self.sr; t = np.arange(n) / sr; e = np.minimum(1, t / max(a, 1e-4))
        if d: e = e * (sustain + (1 - sustain) * np.exp(-np.maximum(0, t - a) / d))
        rel = int(r * sr)
        if rel and n > rel: e[-rel:] *= np.linspace(1, 0, rel) ** 2
        return e

    def saw(self, f, n, phase=0.0):
        dt = f / self.sr; ph = (phase + dt * np.arange(n)) % 1.0; y = 2 * ph - 1
        m = ph < dt; x = ph[m] / dt; y[m] -= x + x - x * x - 1                      # polyBLEP: no aliasing whistle
        m = ph > 1 - dt; x = (ph[m] - 1) / dt; y[m] -= x * x + x + x + 1
        return y

    def lp(self, x, fc, order=2):
        fc = min(fc, 0.45 * self.sr); return signal.sosfilt(signal.butter(order, fc, "low", fs=self.sr, output="sos"), x, axis=0)

    def hp(self, x, fc, order=2): return signal.sosfilt(signal.butter(order, fc, "high", fs=self.sr, output="sos"), x, axis=0)

    def bp(self, x, lo, hi, order=2):
        return signal.sosfilt(signal.butter(order, [lo, min(hi, 0.45 * self.sr)], "band", fs=self.sr, output="sos"), x, axis=0)

    def noise(self, n): return self.rng.standard_normal(n)

    def pad(self, notes, dur, bright=0.5, attack=0.45):
        """Supersaw chord through a lowpass that opens with `bright`; stereo from detuned voices."""
        n = int((dur + 0.7) * self.sr); L = np.zeros(n); R = np.zeros(n)
        for nn in notes:
            for k, det in enumerate((-0.0035, -0.0012, 0.0012, 0.0035)):
                v = self.saw(hz(nn) * (1 + det), n, phase=(k * 0.27 + nn * 0.11) % 1)
                (L if k % 2 else R)[:] += v * (0.8 if k in (1, 2) else 0.55)
        fc = 500 + 2600 * bright
        y = self.lp(np.stack([L, R], 1), fc, 2) / (len(notes) * 2.2)
        return y * self.env(n, a=attack, r=0.7)[:, None]

    def pluck(self, f, dur=0.6, bright=1.0):
        n = int(dur * self.sr); t = np.arange(n) / self.sr
        y = sum(np.sin(2 * np.pi * k * f * t) * np.exp(-t * (6 + 3.4 * k / max(bright, 0.2))) / k ** 1.1 for k in range(1, 9))
        y[:int(0.004 * self.sr)] += self.hp(self.noise(int(0.004 * self.sr)), 3000) * 0.15
        return y * self.env(n, a=0.002, r=0.05)

    def epiano(self, f, dur=1.6, vel=1.0):
        """FM electric piano: 1:1 body with a decaying index plus a quick high 'tine'."""
        n = int(dur * self.sr); t = np.arange(n) / self.sr
        idx = (1.4 * vel) * np.exp(-t / 0.35) + 0.2
        body = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t))
        tine = np.sin(2 * np.pi * f * t + 2.2 * vel * np.exp(-t / 0.02) * np.sin(2 * np.pi * 14 * f * t)) * np.exp(-t / 0.08) * 0.35
        return (body * np.exp(-t / 1.1) + tine) * self.env(n, a=0.002, r=0.15)

    def bell(self, f, dur=2.0):
        n = int(dur * self.sr); t = np.arange(n) / self.sr
        return np.sin(2 * np.pi * f * t + 2.5 * np.exp(-t / 0.6) * np.sin(2 * np.pi * 3.5 * f * t)) * np.exp(-t / 0.9) * self.env(n, a=0.002, r=0.2)

    def strings(self, f, dur=0.22):
        """Spiccato string note: bright saws, quick decay."""
        n = int((dur + 0.15) * self.sr)
        y = sum(self.saw(f * (1 + d), n, phase=i * 0.3) for i, d in enumerate((-0.003, 0, 0.003))) / 3
        return self.lp(y, 2600) * self.env(n, a=0.008, d=dur * 0.6, sustain=0.0, r=0.1)

    def bass(self, f, dur, kind="sub"):
        n = int((dur + 0.05) * self.sr); t = np.arange(n) / self.sr
        if kind == "saw":
            y = self.lp(self.saw(f, n) * 0.6, 520) + np.sin(2 * np.pi * f * t) * 0.8
        else:
            # upper harmonics (and a little drive) so the bass still reads on a phone speaker
            y = np.sin(2 * np.pi * f * t) + 0.38 * np.sin(4 * np.pi * f * t) + 0.16 * np.sin(6 * np.pi * f * t) + 0.06 * np.sin(8 * np.pi * f * t)
            y = np.tanh(1.4 * y) / np.tanh(1.4)
        return y * self.env(n, a=0.006, d=dur * 0.8, sustain=0.55, r=0.04)

    def stab(self, notes, dur=0.35):
        n = int((dur + 0.2) * self.sr)
        y = sum(self.saw(hz(nn) * (1 + d), n, phase=d * 50) for nn in notes for d in (-0.004, 0.004))
        dark, bright = self.lp(y, 700), self.lp(y, 3200); e = np.exp(-np.arange(n) / self.sr / 0.09)
        return (dark * (1 - e) + bright * e) / (len(notes) * 2) * self.env(n, a=0.004, d=dur * 0.5, sustain=0.2, r=0.12)

    def hit(self, kind):
        """One-shot drums and percussion, made once and cached."""
        if kind in self._cache: return self._cache[kind]
        sr = self.sr; R = lambda s: np.arange(int(s * sr)) / sr
        if kind in ("kick", "softkick"):
            t = R(0.45); ph = 2 * np.pi * np.cumsum(46 + 120 * np.exp(-t / 0.03)) / sr
            y = np.sin(ph) * np.exp(-t / (0.28 if kind == "kick" else 0.2))
            if kind == "kick": y[:int(0.006 * sr)] += self.hp(self.noise(int(0.006 * sr)), 2500) * 0.4
        elif kind == "taiko":
            t = R(1.2); ph = 2 * np.pi * np.cumsum(52 + 70 * np.exp(-t / 0.05)) / sr
            y = np.sin(ph) * np.exp(-t / 0.45) + self.lp(self.noise(len(t)), 900) * np.exp(-t / 0.06) * 0.5
        elif kind == "tom":
            t = R(0.6); ph = 2 * np.pi * np.cumsum(95 + 80 * np.exp(-t / 0.04)) / sr
            y = np.sin(ph) * np.exp(-t / 0.22) + self.bp(self.noise(len(t)), 200, 1500) * np.exp(-t / 0.04) * 0.3
        elif kind == "snare":
            t = R(0.3); y = self.bp(self.noise(len(t)), 1200, 7000) * np.exp(-t / 0.11) * 0.9 + np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05) * 0.6
        elif kind == "clap":
            t = R(0.35); y = np.zeros(len(t)); nz = self.bp(self.noise(len(t)), 900, 4000)
            for k, d in enumerate((0.0, 0.011, 0.022)):
                i = int(d * sr); y[i:] += nz[:len(t) - i] * np.exp(-t[:len(t) - i] / (0.012 if k < 2 else 0.12))
        elif kind == "hat":
            t = R(0.08); y = self.hp(self.noise(len(t)), 7500) * np.exp(-t / 0.022)
        elif kind == "ohat":
            t = R(0.35); y = self.hp(self.noise(len(t)), 6500) * np.exp(-t / 0.14)
        elif kind == "shaker":
            t = R(0.1); y = self.bp(self.noise(len(t)), 5000, 11000) * np.minimum(1, t / 0.012) * np.exp(-t / 0.035)
        elif kind == "tick":
            t = R(0.03); y = self.hp(self.noise(len(t)), 5000) * np.exp(-t / 0.005)
        elif kind == "rim":
            t = R(0.08); y = np.sin(2 * np.pi * 820 * t) * np.exp(-t / 0.015) + self.bp(self.noise(len(t)), 2000, 6000) * np.exp(-t / 0.01) * 0.5
        elif kind == "crash":
            t = R(2.4); y = self.hp(self.noise(len(t)), 4200) * np.exp(-t / 0.8) * 0.8
        else:
            raise KeyError(kind)
        y = y / (np.abs(y).max() + 1e-9); self._cache[kind] = y; return y

    def whoosh(self, d=0.7, up=True):
        n = int(d * self.sr); t = np.arange(n) / self.sr; x = self.noise(n); s = t / d
        lo, hi = self.lp(x, 900), self.hp(x, 1800); m = s if up else 1 - s
        y = (lo * (1 - m) + hi * m) * (np.sin(np.pi * s) ** 1.5)
        return np.stack([y * (1 - 0.4 * s), y * (0.6 + 0.4 * s)], 1)

    def impact(self, size=1.0):
        n = int(2.2 * self.sr); t = np.arange(n) / self.sr
        boom = np.sin(2 * np.pi * np.cumsum(38 + 40 * np.exp(-t / 0.08)) / self.sr) * np.exp(-t / (0.5 * size))
        crack = self.lp(self.noise(n), 2500) * np.exp(-t / 0.05) * 0.5
        return boom + crack

    def riser(self, d=2.0):
        n = int(d * self.sr); t = np.arange(n) / self.sr; s = t / d
        x = self.bp(self.noise(n), 800, 9000) * s ** 2.5
        sw = np.sin(2 * np.pi * np.cumsum(200 + 900 * s ** 2) / self.sr) * s ** 3 * 0.25
        return x + sw


# ------------------------------------------------------------------ grid and arrangement
def build_grid(cues, bpm):
    """Beat times whose bars start exactly on the edit's anchors, tempo within about 9% of bpm."""
    b0, total = 60.0 / bpm, cues["total"]
    pri = []                                                     # (time, priority): higher wins when two crowd
    if cues.get("end_card"): pri.append((cues["end_card"][0], 10))
    if cues.get("sting"): pri.append((cues["sting"][0] + 0.37, 9.5))
    if cues.get("cold") and cues["cold"][2] is not None: pri.append((cues["cold"][2], 9))
    if cues.get("hook"): pri.append((cues["hook"][1], 8))
    lift = cues.get("lift")
    for name, t in cues["sections"]: pri.append((t, 7 if name == lift else 5))
    for c0, c1, _ in cues.get("cards", []): pri.append((c0, 6))
    pts = {0.0: 100}
    for t, p in sorted(pri):
        if t <= 0.25 or t >= total - 0.25: continue
        near = [k for k in pts if abs(k - t) < 0.9 * b0]
        if near:
            k = near[0]
            if p > pts[k] and k != 0.0: del pts[k]; pts[t] = p
        else: pts[t] = p
    cuts = sorted(cues.get("cuts", [])) if not cues.get("voice", True) else []
    while True:
        xs = sorted(pts); plan, bad = [], None; prev_beat = b0
        for a, b in zip(xs, xs[1:]):
            L, best = b - a, None
            for n in range(max(1, round(L / b0) - 3), round(L / b0) + 4):
                beat = L / n; dev = beat / b0 - 1
                if abs(dev) > 0.09: continue
                cost = abs(dev) * 3 + abs(beat / prev_beat - 1) * 2 + (0 if n % 4 == 0 else 0.05 if n % 2 == 0 else 0.14)
                for c in cuts:                       # no voice: prefer the tempo that puts the picture's cuts on 8th notes
                    if a < c < b:
                        ph = ((c - a) / (beat / 2)) % 1
                        if min(ph, 1 - ph) * beat / 2 > 0.045: cost += 0.12
                if best is None or cost < best[0]: best = (cost, n, beat)
            if best is None: bad = (a, b); break
            plan.append((a, best[1], best[2])); prev_beat = best[2]
        if bad is None: break
        a, b = bad; drop = b if (pts[b] <= pts[a] or a == 0.0) else a
        if drop == 0.0: drop = b
        del pts[drop]
    beats, down = [], []
    for a, n, beat in plan:
        for j in range(n): beats.append(a + j * beat); down.append(j % 4 == 0)
    last = sorted(pts)[-1]; beat = plan[-1][2] if plan else b0; j = 0
    while last + j * beat < total + 2.0: beats.append(last + j * beat); down.append(j % 4 == 0); j += 1
    return np.array(beats), np.array(down), sorted(pts)


def chord_notes(style, degree, octave=0):
    sc = SCALES[style["scale"]]; root = style["root"] + 12 + 12 * octave
    return [root + sc[(degree + 2 * i) % 7] + 12 * ((degree + 2 * i) // 7) for i in range(3)]


def voice_lead(prev, notes, lo=50, hi=67):
    """Closest inversion of `notes` to the previous chord, kept in [lo, hi]."""
    cands = []
    for inv in range(3):
        c = sorted(notes[inv:] + [x + 12 for x in notes[:inv]])
        while c[0] < lo: c = [x + 12 for x in c]
        while c[-1] > hi: c = [x - 12 for x in c]
        cands.append(c)
    if not prev: return cands[0]
    return min(cands, key=lambda c: sum(abs(a - b) for a, b in zip(sorted(c), sorted(prev))))


INFO = {}          # filled by render(): tempo range, cuts on the beat (build.py prints it)


def render(style_id, cues):
    if style_id not in STYLES: raise KeyError(f"unknown music style '{style_id}': " + ", ".join(STYLES))
    st, sr, total = STYLES[style_id], cues["sr"], cues["total"]
    n = int(total * sr); S = Score(n, sr, cues.get("seed", 1))
    beats, down, anchors = build_grid(cues, st["bpm"])
    bl = np.diff(beats[beats < total]) if len(beats) > 1 else np.array([60 / st["bpm"]])
    cuts = [c for c in cues.get("cuts", []) if c < total - 0.1] if not cues.get("voice", True) else []
    half = np.concatenate([beats, (beats[:-1] + beats[1:]) / 2]) if len(beats) > 1 else beats
    INFO.clear(); INFO.update(style=style_id, bpm_min=60 / bl.max(), bpm_max=60 / bl.min(), cuts=len(cuts),
                              cuts_on_beat=sum(1 for c in cuts if np.abs(half - c).min() <= 0.045))
    secs = cues["sections"]; first = secs[0][1] if secs else 0.0; voice_end = cues["voice_end"]
    endc = cues.get("end_card"); lift = cues.get("lift"); energy_map = cues.get("energy", {})
    hook = cues.get("hook"); cold = cues.get("cold"); sting = cues.get("sting")

    def section_at(t):
        cur = None
        for name, t0 in secs:
            if t >= t0 - 0.05: cur = name
        return cur

    def energy_at(t):
        if endc and t >= endc[0] - 0.05: return -1                          # end: ring out
        if hook and t < hook[1] - 0.05: return max(2, energy_map.get(secs[0][0], 3) if secs else 3)
        if t < first - 0.05:
            if sting and t >= sting[0] + 0.3: return 2                 # the music enters with the logo
            return 0
        name = section_at(t)
        if name == lift: return 3
        return int(energy_map.get(name, 2))

    # bars: runs of beats starting at a downbeat
    bars, cur = [], []
    for i, (t, d) in enumerate(zip(beats, down)):
        if d and cur: bars.append(cur); cur = []
        cur.append(i)
    if cur: bars.append(cur)
    prog, prev_chord, ci = st["prog"], None, 0
    restart = {round(a, 3) for a in anchors if (hook and abs(a - hook[1]) < 0.01) or any(abs(a - t) < 0.01 for nm, t in secs if nm == lift)}
    sixteenth = lambda bi, j: beats[bi] + (beats[min(bi + 1, len(beats) - 1)] - beats[bi]) * j / 4 if bi + 1 < len(beats) else beats[bi] + j * 60 / st["bpm"] / 4
    kicks = []
    for bar in bars:
        t0 = beats[bar[0]]
        if t0 >= total + 1.0: break
        t1 = beats[bar[-1] + 1] if bar[-1] + 1 < len(beats) else t0 + len(bar) * 60 / st["bpm"]
        if round(t0, 3) in restart: ci = 0
        e = energy_at(t0 + 0.01)
        deg = prog[ci % len(prog)]; ci += 1
        notes = voice_lead(prev_chord, chord_notes(st, deg)); prev_chord = notes
        rootb = style_root = st["root"] + SCALES[st["scale"]][deg % 7]
        while rootb > st["root"] + 9: rootb -= 12
        nb = len(bar); dur = t1 - t0
        if e == -1:                                                          # end card: final tonic, ring out
            fin = voice_lead(notes, chord_notes(st, 0))
            if t0 - endc[0] < 0.05:
                S.add("pad", t0, S.pad(fin + [fin[0] + 12], max(3.0, total - t0 + 0.5), bright=0.55, attack=0.05), 0.9)
                S.add("bass", t0, S.bass(hz(st["root"]), max(2.5, total - t0), "sub"), 0.9)
                S.add("keys", t0, S.bell(hz(fin[-1] + 12), 3.0) if style_id in ("cinematic", "tactical") else S.epiano(hz(fin[-1] + 12), 3.0), 0.35)
            continue
        S.add("pad", t0, S.pad(notes, dur, bright=0.25 + 0.2 * max(e, 0)), 0.55 + 0.12 * max(e, 0))
        # per-style layers
        for b_i, bi in enumerate(bar):
            for j in range(4):
                tt = sixteenth(bi, j); pos = b_i * 4 + j
                if tt >= (endc[0] if endc else total) - 0.02: continue
                if style_id == "tactical":
                    if e >= 1: S.add("bass", tt, S.bass(hz(rootb + (12 if j == 2 and e >= 3 else 0)), 0.11, "saw"), 0.22 + 0.04 * e)
                    if e >= 1 and j % 2 == 0: S.add("perc", tt, S.hit("tick"), 0.10 + 0.04 * e, pan=0.3 if j else -0.3)
                    if e >= 2 and j % 2 == 1: S.add("perc", tt, S.hit("hat"), 0.10, pan=0.2)
                    if e >= 2 and j == 0 and b_i % 2 == 0: S.add("drums", tt, S.hit("taiko"), 0.55); kicks.append(tt)
                    if e >= 3 and j == 0 and b_i % 2 == 1: S.add("drums", tt, S.hit("snare"), 0.5); S.add("drums", tt, S.hit("clap"), 0.25)
                    if e >= 3 and b_i == nb - 1 and j >= 2 and len(bars) and nb >= 4: S.add("drums", tt, S.hit("tom"), 0.35, pan=-0.2 if j == 2 else 0.2)
                elif style_id == "cinematic":
                    if e >= 1 and j % 2 == 0:
                        tone = notes[(pos // 2) % 3] + (12 if (pos // 2) % 4 == 3 else 0)
                        S.add("keys", tt, S.strings(hz(tone), 0.18), 0.22 + 0.05 * e, pan=-0.25 if j else 0.25)
                    if e >= 2 and j == 0 and b_i in (0, 2): S.add("drums", tt, S.hit("tom" if e == 2 else "taiko"), 0.55 + 0.1 * e); kicks.append(tt)
                    if e >= 2 and j == 0 and b_i % 2 == 0: S.add("bass", tt, S.bass(hz(rootb), dur / max(1, nb) * 2, "sub"), 0.7)
                    if e >= 3 and j == 2 and b_i == nb - 1: S.add("drums", tt, S.hit("snare"), 0.35)
                    if e >= 1 and b_i == 0 and j == 0 and pos == 0 and e <= 2: S.add("keys", tt, S.bell(hz(notes[-1] + 12), 1.8), 0.16, pan=0.3)
                elif style_id == "uplifting":
                    if e >= 1 and j % 2 == 0:
                        arp = [0, 2, 1, 2, 0, 2, 1, 3][(pos // 2) % 8]; tone = (notes + [notes[0] + 12])[arp] + 12
                        S.add("keys", tt, S.pluck(hz(tone), 0.5), 0.30 if j == 0 else 0.22, pan=0.35 if (pos // 2) % 2 else -0.35)
                        if e >= 3: S.add("keys", tt, S.pluck(hz(tone + 12), 0.35, 0.8), 0.10, pan=-0.5 if (pos // 2) % 2 else 0.5)
                    if e >= 1 and j == 0 and (e >= 2 or b_i % 2 == 0): S.add("bass", tt, S.bass(hz(rootb), 0.42 if e >= 2 else 0.9, "sub"), 0.62)
                    if e >= 2 and j == 0: S.add("drums", tt, S.hit("kick"), 0.62); kicks.append(tt)
                    if e >= 2 and j == 2: S.add("perc", tt, S.hit("ohat" if e >= 3 else "hat"), 0.10 if e >= 3 else 0.12)
                    if e >= 2: S.add("perc", tt, S.hit("shaker"), 0.05 + (0.03 if j % 2 else 0), pan=0.25)
                    if e >= 3 and j == 0 and b_i % 2 == 1: S.add("drums", tt, S.hit("clap"), 0.40)
                elif style_id == "warm":
                    if j == 0 and b_i == 0:
                        for k, nn in enumerate(notes): S.add("keys", tt + 0.012 * k, S.epiano(hz(nn), min(2.4, dur + 0.4), 0.8), 0.20)
                    if e >= 1 and j == 2 and b_i % 2 == 1: S.add("keys", tt, S.epiano(hz(notes[(b_i // 2) % 3] + 12), 1.2, 0.6), 0.16, pan=0.25)
                    if e >= 1 and j == 0 and b_i % 2 == 0: S.add("bass", tt, S.bass(hz(rootb), dur / max(1, nb) * 2, "sub"), 0.55)
                    if e >= 2 and j == 0 and b_i % 2 == 0: S.add("drums", tt, S.hit("softkick"), 0.38); kicks.append(tt)
                    if e >= 2: S.add("perc", tt, S.hit("shaker"), 0.035 + (0.025 if j % 2 else 0), pan=0.3)
                    if e >= 3 and j == 0 and b_i % 2 == 1: S.add("drums", tt, S.hit("rim"), 0.20)
                elif style_id == "groove":
                    swing = 0.18 * (beats[min(bi + 1, len(beats) - 1)] - beats[bi]) / 4 if j % 2 == 1 else 0.0
                    ts = tt + swing
                    if j == 0 and b_i == 0:
                        for k, nn in enumerate(notes + [notes[0] + 12]): S.add("keys", ts + 0.015 * k, S.epiano(hz(nn), min(2.6, dur + 0.3), 0.7), 0.17)
                    if e >= 1 and ((j == 0 and b_i in (0, 2)) or (j == 3 and b_i == 1)): S.add("bass", ts, S.bass(hz(rootb), 0.38, "sub"), 0.62)
                    if e >= 2 and ((j == 0 and b_i in (0, 2)) or (j == 2 and b_i == 1)): S.add("drums", ts, S.hit("kick"), 0.62); kicks.append(ts)
                    if e >= 2 and j == 0 and b_i % 2 == 1: S.add("drums", ts, S.hit("snare"), 0.45)
                    if e >= 2 and j % 2 == 0: S.add("perc", ts, S.hit("hat"), 0.09 + 0.03 * (j == 0), pan=0.2)
                    if e >= 3 and j == 3: S.add("perc", ts, S.hit("hat"), 0.05, pan=-0.2)
        if e >= 3 and style_id in ("tactical", "cinematic"):                  # low brass stab on each new chord
            S.add("keys", t0, S.stab([notes[0] - 12, notes[0], notes[1]], 0.45), 0.55)
    # no voice: a hit on every cut, so the music answers the picture
    if not cues.get("voice", True):
        kind, bus, g = {"tactical": ("snare", "drums", 0.32), "cinematic": ("tom", "drums", 0.40), "uplifting": ("clap", "drums", 0.24),
                        "warm": ("rim", "drums", 0.15), "groove": ("snare", "drums", 0.26)}[style_id]
        for c in cues.get("cuts", []):
            if endc and c >= endc[0] - 0.05: continue
            S.add(bus, c, S.hit(kind), g); S.add("perc", c, S.hit("tick"), 0.07)
    # sustained drone under a cold open / sting, before the voice
    if cold or sting:
        tone = chord_notes(st, 0)
        end_pre = first
        S.add("pad", 0.0, S.pad([tone[0] - 12, tone[0], tone[2]], end_pre + 0.5, bright=0.15, attack=0.8), 0.6)
    # transitions
    def boom(t, size=1.0, g=1.0): S.add("fx", t, S.impact(size), 0.9 * g); S.add("perc", t, S.hit("crash"), 0.22 * g)
    def into(t, d=0.7, g=1.0):
        if t - d > 0: S.add("fx", t - d, S.whoosh(d), 0.45 * g)
    if cold and cold[2] is not None: boom(cold[2], 1.0, 0.9)
    if sting:
        into(sting[0], 0.6); boom(sting[0] + 0.37, 1.2, 1.0)
        if sting[0] > 1.3: S.add("fx", sting[0] + 0.37 - 1.3, S.riser(1.3), 0.35)
    if hook:
        S.add("fx", max(0.0, hook[1] - 1.4), S.riser(1.4), 0.30); boom(hook[1], 1.0, 0.85)
    for c0, c1, scene in cues.get("cards", []): into(c0, 0.55, 0.8); S.add("fx", c0 + 0.25, S.impact(0.6), 0.45)
    for t, scene in cues.get("overlays", []): S.add("perc", t + 0.4, S.hit("tick"), 0.08)
    if lift:
        lt = next((t for nm, t in secs if nm == lift), None)
        if lt is not None and lt > 2.2: S.add("fx", lt - 2.0, S.riser(2.0), 0.28); S.add("perc", lt, S.hit("crash"), 0.25)
    if endc: into(endc[0], 0.6); boom(endc[0], 1.3, 1.0)
    # sidechain pump on pad and bass from the kicks (styles with a steady kick)
    if style_id in ("uplifting", "groove", "tactical") and kicks:
        g = np.ones(n + 4 * sr); ln = int(0.25 * sr); shape = 1 - 0.45 * np.exp(-np.arange(ln) / sr / 0.09)
        for t in kicks:
            i = int(t * sr)
            if 0 <= i < len(g) - ln: g[i:i + ln] = np.minimum(g[i:i + ln], shape)
        for b in ("pad", "bass"): S.bus[b] *= g[:, None]
    # mix: reverb sends, bus balance, gentle saturation
    ir = make_ir(sr, S.rng)
    def verb(x, wet):
        if wet <= 0: return x
        y = np.stack([signal.fftconvolve(x[:, c], ir[:, c])[:len(x)] for c in range(2)], 1)
        return x + y * wet
    # bus balance, measured: the sub bass would otherwise sit 10-13 dB over everything else and vanish on phones
    pad = S.hp(S.bus["pad"], 110, 2)
    bed = (verb(pad, 0.35) * 0.9 + verb(S.bus["keys"], 0.3) * 1.0 + S.hp(S.bus["bass"], 35, 2) * 0.3
           + verb(S.bus["drums"], 0.12) * 0.9 + verb(S.bus["perc"], 0.15) * 2.6)
    bed = S.hp(bed, 30, 2)
    if style_id in ("tactical", "cinematic"):            # their big drums measured 5-8 dB heavy below 150 Hz: a 5 dB low shelf
        bed = bed + (10 ** (-5 / 20) - 1) * S.lp(bed, 150, 2)
    bed = np.tanh(bed * 1.5 / (np.abs(bed).max() + 1e-9)) / math.tanh(1.5)
    fx = verb(S.bus["fx"], 0.4); fx = fx / (np.abs(fx).max() + 1e-9)
    t = np.arange(len(bed)) / sr; fade = np.clip((total - t) / 0.8, 0, 1)
    bed = bed * fade[:, None]; fx = fx * fade[:, None]
    return bed[:n], fx[:n]


def make_ir(sr, rng, rt60=1.9, pre=0.022):
    n = int(rt60 * 1.1 * sr); t = np.arange(n) / sr
    nz = rng.standard_normal((n, 2)); dec = np.exp(-6.9 * t / rt60)[:, None]
    lowpassed = signal.sosfilt(signal.butter(1, 3500, "low", fs=sr, output="sos"), nz, axis=0)
    ir = (lowpassed * 0.7 + nz * 0.3 * np.exp(-6.9 * t / (rt60 * 0.45))[:, None]) * dec
    ir = np.concatenate([np.zeros((int(pre * sr), 2)), ir]); return ir / np.sqrt((ir ** 2).sum(0, keepdims=True)) * 0.6


def demo_cues(total=40.0, sr=48000):
    secs = [("intro", 7.4), ("why", 13.0), ("proof", 21.5), ("close", 30.0)]
    act = np.zeros(int(total / 0.02), bool)
    for a, b in ((7.4, 12.4), (13.0, 21.0), (21.5, 29.5), (30.0, 34.0)): act[int(a / .02):int(b / .02)] = True
    return dict(total=total, sr=sr, voice_end=34.0, picture_end=34.5, sections=secs, energy={"intro": 1, "why": 2, "proof": 3, "close": 1},
                lift="proof", cold=(0.0, 4.0, 2.6), sting=(4.0, 7.0), hook=None, end_card=(34.5, total), cards=[(24.0, 28.0, "quote")],
                overlays=[(7.6, "lower-third")], voice_active=act, frame=0.02, social=False, seed=1)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] not in ("styles", "demo"): sys.exit(__doc__)
    if a[0] == "styles":
        for k, s in STYLES.items(): print(f"{k:10} {s['name']:<18} {s['bpm']:>3} bpm  {s['suits']}")
        sys.exit()
    from scipy.io import wavfile
    secs = float(a[a.index("--seconds") + 1]) if "--seconds" in a else 40.0
    bed, fx = render(a[1], demo_cues(secs))
    y = bed * 0.5 + fx * 0.35; y = y / (np.abs(y).max() + 1e-9) * 0.9
    wavfile.write(a[2], 48000, y.astype(np.float32)); print("->", a[2])
