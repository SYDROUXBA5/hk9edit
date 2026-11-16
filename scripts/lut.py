#!/usr/bin/env python3
"""3D LUTs that turn phone HDR (HLG or PQ, BT.2020) into standard Rec.709 video, applied by ffmpeg's lut3d.

ffmpeg builds often lack zscale/libplacebo, so the HDR -> SDR step is a .cube file. Method (tested on iPhone HLG):
  1. inverse transfer per channel -> scene-linear BT.2020 (PQ is first mapped so 203 nits = HLG reference white)
  2. 3x3 matrix -> BT.709 primaries (fixes the washed-out look of HDR simply relabelled as SDR)
  3. tone curve on luminance only (hue kept), fitted to Apple's own SDR rendering of iPhone HLG (tone_curve.json)
  4. out-of-gamut colours are clipped and dimmed, never whitened (whitening turns bright reds pink)
  5. encode with 1/2.4 (BT.1886)
Usage: python lut.py OUT.cube [--pq]
"""
import json, os, sys
import numpy as np
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
A, B, C = 0.17883277, 0.28466892, 0.55991073
M = np.array([[1.6605, -0.5876, -0.0728], [-0.1246, 1.1329, -0.0083], [-0.0182, -0.1006, 1.1187]])
L2020 = np.array([0.2627, 0.6780, 0.0593]); L709 = np.array([0.2126, 0.7152, 0.0722])
GRADE = dict(exposure=0.0, contrast=1.0, pivot=0.45, sat=1.07)


def hlg_inv(v): return np.where(v <= 0.5, v * v / 3.0, (np.exp((v - C) / A) + B) / 12.0)
def hlg_oetf(e):
    e = np.clip(e, 0, 1); return np.where(e <= 1 / 12, np.sqrt(3 * e), A * np.log(np.maximum(12 * e - B, 1e-9)) + C)
def pq_eotf(v):  # signal -> cd/m2
    m1, m2, c1, c2, c3 = 0.1593017578125, 78.84375, 0.8359375, 18.8515625, 18.6875
    p = np.power(np.clip(v, 0, 1), 1 / m2); return 10000 * np.power(np.maximum(p - c1, 0) / (c2 - c3 * p), 1 / m1)


def write_cube(path, pq=False, n=65):
    g = np.linspace(0, 1, n)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")          # .cube order: R fastest
    rgb = np.stack([r, gg, b], -1).reshape(-1, 3)
    lin2020 = pq_eotf(rgb) / 203.0 * hlg_inv(0.75) if pq else hlg_inv(rgb)
    ys = lin2020 @ L2020; lin709 = lin2020 @ M.T
    curve = json.load(open(os.path.join(HERE, "tone_curve.json"), encoding="utf-8"))
    yt = np.interp(hlg_oetf(ys), curve["x"], curve["y"]) ** 2.4 * 2.0 ** GRADE["exposure"]
    out = lin709 * (yt / np.maximum(ys, 1e-9))[:, None]
    y = out @ L709; out = np.maximum(y[:, None] + (out - y[:, None]) * GRADE["sat"], 0)
    m = out.max(1); knee = 0.85
    ms = np.where(m > knee, knee + (1 - knee) * np.tanh((m - knee) / (1 - knee)), m)
    out = np.clip(out * (ms / np.maximum(m, 1e-9))[:, None], 0, 1) ** (1 / 2.4)
    p, c = GRADE["pivot"], GRADE["contrast"]
    out = np.clip(np.where(out < p, p * (out / p) ** c, 1 - (1 - p) * ((1 - out) / (1 - p)) ** c), 0, 1)
    with open(path, "w", encoding="ascii", newline="\n") as f:
        f.write(f"TITLE \"{'PQ' if pq else 'HLG'} BT.2020 to Rec.709\"\nLUT_3D_SIZE {n}\n")
        np.savetxt(f, out, fmt="%.6f")
    return path


if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(__doc__)
    print("->", write_cube(sys.argv[1], pq="--pq" in sys.argv))
