// The Highland graphics. Every scene draws itself for the current format (9:16 or 16:9, see kit.setFormat),
// takes its words from p (falling back to COPY) and its length from o.dur.
// Cards are opaque full-frame graphics; overlays sit on the footage (transparent background).
import { W, H, PORTRAIT, C, L, R, CW, RAIL, HOLD, clamp, lerp, prog, outCubic, outQuint, inOut, snap, reward, mix, tw, fit, font, text, rise, soft, wrap, box, field, mark, tag, trail, layer, placeholder } from './kit.js';
import { COPY } from './copy.js';

const up = (s) => String(s).toUpperCase();
const tagIn = (t) => outCubic(prog(t, 0.05, 0.4));
// Heading of one or more lines that fits the column; returns the baseline of the last line.
function heading(ctx, lines, t, y, max, t0 = 0.3, width = CW, x = L) {
  const size = Math.min(...lines.map((s) => fit(ctx, s, width, max)));
  lines.forEach((s, i) => rise(ctx, s, x, y + i * (size * 0.72 + 26), snap(t, t0 + i * 0.12, 0.2), { size }));
  return { size, last: y + (lines.length - 1) * (size * 0.72 + 26), tMark: t0 + (lines.length - 1) * 0.12 + 0.2 };
}
// A window that opens from a hairline and shows the transparent logo, straight on the navy field.
function logoWindow(ctx, logo, cx, cy, pw, ph, open, scale = 1) {
  const hh = (ph / 2) * open;
  if (open > 0) {
    ctx.save(); ctx.beginPath(); ctx.rect(cx - pw / 2, cy - hh, pw, hh * 2); ctx.clip();
    ctx.translate(cx, cy); ctx.scale(scale, scale); ctx.drawImage(logo, -logo.width / 2, -logo.height / 2);
    ctx.restore();
  }
  return hh;
}
// "*word*" or "*several words*" marks emphasis (shown in sky blue).
function parseWords(s) {
  let on = false;
  return String(s).split(/\s+/).filter(Boolean).map((w) => {
    const open = w.startsWith('*'), close = /\*[.,!?:;'"]*$/.test(w);
    const em = on || open; if (open) on = true; if (close) on = false;
    return { s: up(w.replace(/\*/g, '')), em };
  });
}

// ------------------------------------------------------------------ CARDS

// Logo sting: straight over the footage (transparent, no field). A soft shadow keeps the white lettering readable on
// bright shots without a box; everything folds back into the hairlines at the end.
function sting(ctx, t, p, A, o) {
  // no website line over the footage (it does not read on grass); the end card carries it. p.url adds one back.
  const tagline = p.tagline || COPY.tagline, url = p.url || null, P = PORTRAIT;
  const cx = W / 2, cy = P ? 800 : 400, s0 = P ? 1 : 0.72, pw = 720 * s0, ph = 640 * s0, hw = P ? 380 : 330;
  const a = snap(t, 0.1, 0.27), m1 = 0.37;
  const b = snap(t, m1 + HOLD, 0.23), m2 = m1 + HOLD + 0.23;
  const r = reward(t, m2, 0.9), out = 1 - snap(t, o.dur - 0.45, 0.3);
  if (out <= 0) return;
  // no box, no colour: the footage just dims softly around the logo and the line under it, so white stays readable
  const gy = cy + (P ? 150 : 90), gl = Math.min(1, a * 1.4) * out;
  if (gl > 0) {
    const g = ctx.createRadialGradient(cx, gy, 0, cx, gy, P ? 620 : 520);
    g.addColorStop(0, `rgba(0,0,0,${0.5 * gl})`); g.addColorStop(0.55, `rgba(0,0,0,${0.3 * gl})`); g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.save(); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); ctx.restore();
  }
  ctx.save(); ctx.shadowColor = 'rgba(0,0,0,0.6)'; ctx.shadowBlur = 30; ctx.shadowOffsetY = 4;
  const hh = logoWindow(ctx, A.logo, cx, cy, pw, ph, b * out, s0 * (1.04 - 0.04 * r));
  box(ctx, cx - hw * a * out, cy - hh - 4, 2 * hw * a * out, 4, C.sky);
  box(ctx, cx - hw * a * out, cy + hh, 2 * hw * a * out, 4, C.sky);
  ctx.restore();
  const lines = P ? tagline : [tagline.join(' ')];
  const ty = cy + ph / 2 + (P ? 120 : 92);
  lines.forEach((s, i) => soft(ctx, s, cx, ty + i * 58, reward(t, m2 + i * 0.1, 0.9) * out, { size: P ? 38 : 34, weight: 700, track: lerp(14, 8, r), align: 'center', shadow: 1 }));
  const by = ty + (lines.length - 1) * 58, m3 = 1.8, u = snap(t, m3 - 0.15, 0.15) * out;
  box(ctx, cx - 60 * u, by + 42, 120 * u, 8, C.amber);
  if (url) soft(ctx, url, cx, by + 122, reward(t, m3, 0.8) * out, { size: 32, weight: 600, color: C.sky, track: 3, align: 'center', shadow: 1 });
}

function kinetic(ctx, t, p) {
  const words = (p.words || COPY.kinetic).map((w) => (typeof w === 'string' ? { s: w } : w)), url = p.url ?? COPY.url, P = PORTRAIT;
  field(ctx, t); tag(ctx, tagIn(t));
  const colW = P ? CW : CW * 0.78, maxS = P ? 178 : 150, gap = P ? 36 : 28, top = P ? 440 : 240, avail = P ? 940 : 600;
  let sizes = words.map((w) => fit(ctx, up(w.s), colW, maxS));
  let total = sizes.reduce((a, s) => a + s * 0.72, 0) + gap * (words.length - 1);
  if (total > avail) { const k = avail / total; sizes = sizes.map((s) => s * k); total = avail; }
  const firstKey = words.findIndex((w) => w.key);
  const T = words.map((w, i) => 0.35 + 0.45 * i + (firstKey >= 0 && i >= firstKey ? 0.1 : 0));
  const mU = T[T.length - 1] + 0.65, y0 = P ? top : top + (avail - total) / 2;
  const push = 1 + 0.03 * inOut(prog(t, mU + HOLD, 2.4));
  ctx.save(); ctx.translate(L, y0 + total / 2); ctx.scale(push, push); ctx.translate(-L, -(y0 + total / 2));
  let y = y0, under = null; const ys = [];
  words.forEach((w, i) => {
    const size = sizes[i], base = y + size * 0.72;
    rise(ctx, up(w.s), L, base, snap(t, T[i], 0.2), { size, color: w.key ? C.sky : C.white });
    ys.push(y + size * 0.36);
    if (w.under) under = { y: base + 16, w: tw(ctx, up(w.s), size) };
    y = base + gap;
  });
  if (under) box(ctx, L, under.y, under.w * snap(t, mU - 0.18, 0.18), 10, C.amber);
  ctx.restore();
  words.forEach((w, i) => mark(ctx, ys[i], t - (T[i] + 0.2)));
  if (under) mark(ctx, under.y + 5, t - mU);
  if (url) soft(ctx, url, L, y + (P ? 110 : 70), reward(t, mU, 0.9), { size: 34, weight: 600, color: C.sky, track: 3 });
}

function stat(ctx, t, p) {
  const S = { ...COPY.stat, ...p }, T0 = 0.5, T1 = 1.9, P = PORTRAIT;
  const value = Math.max(0, Math.round(+S.value)), v = value * snap(t, T0, T1 - T0), places = String(value).length;
  field(ctx, t, { railShift: 24 * Math.min(t, T0) + v * 48 + 24 * Math.max(0, t - T1 - HOLD) });
  tag(ctx, tagIn(t));
  font(ctx, 100);
  const cw100 = Math.max(...String(value).split('').map((d) => ctx.measureText(d).width)) + 2.8;
  const sfx100 = S.suffix ? tw(ctx, S.suffix, 66) + 8 : 0;
  const size = Math.min(P ? 500 : 440, ((P ? CW : CW * 0.5) * 100) / (cw100 * places + sfx100));
  const base = P ? 950 : 690, cw = (cw100 * size) / 100, step = size * 0.9;
  ctx.save(); font(ctx, size);
  ctx.beginPath(); ctx.rect(L - 20, base - size * 0.78, cw * places + 40, size * 0.84); ctx.clip();
  ctx.fillStyle = C.sky; ctx.textAlign = 'center';
  for (let k = 0; k < places; k++) {
    const unit = 10 ** k, lower = k ? (v % unit) / unit : 0;
    const pos = k ? Math.floor(v / unit) + inOut(clamp((lower - 0.9) * 10)) : v;
    const d = Math.floor(pos + 1e-6), f = pos - d, x = L + cw * (places - 1 - k) + cw / 2;
    ctx.fillText(String(d % 10), x, base - f * step);
    if (f > 0.001) ctx.fillText(String((d + 1) % 10), x, base + (1 - f) * step);
  }
  ctx.restore();
  const mP = T1 + 0.13, pp = snap(t, T1, 0.13);
  if (pp > 0 && S.suffix) text(ctx, S.suffix, L + cw * places + 8 + (1 - pp) * 90, base - size * 0.14, { size: size * 0.66, color: C.amber, alpha: pp });
  box(ctx, L, base + 56, CW * snap(t, 0.2, 0.25), 3, C.sky, 0.7);
  mark(ctx, base - size * 0.36, t - T1);
  if (P) {
    soft(ctx, up(S.big), L, base + 210, reward(t, mP, 0.8), { size: fit(ctx, up(S.big), CW, 150) });
    soft(ctx, up(S.sub), L, base + 300, reward(t, mP + 0.22, 0.8), { size: 58, weight: 700, color: C.sky, track: 6 });
    if (S.note) wrap(ctx, S.note, CW, 34, 500).forEach((ln, i) => soft(ctx, ln, L, base + 400 + i * 48, reward(t, mP + 0.5 + i * 0.1, 0.8), { size: 34, weight: 500, alpha: 0.82 }));
  } else {
    const lx = L + cw * places + (S.suffix ? (sfx100 * size) / 100 : 0) + 110, lw = R - lx;
    soft(ctx, up(S.big), lx, base - size * 0.5, reward(t, mP, 0.8), { size: fit(ctx, up(S.big), lw, 128) });
    soft(ctx, up(S.sub), lx, base - size * 0.5 + 84, reward(t, mP + 0.22, 0.8), { size: fit(ctx, up(S.sub), lw, 50, 700, 0.1), weight: 700, color: C.sky, track: 5 });
    if (S.note) wrap(ctx, S.note, lw, 32, 500).forEach((ln, i) => soft(ctx, ln, lx, base - size * 0.5 + 164 + i * 46, reward(t, mP + 0.5 + i * 0.1, 0.8), { size: 32, weight: 500, alpha: 0.82 }));
  }
}

// Footage windows of the before/after card, as [x, y, w, h]. build.py keeps a copy of these numbers.
export function baRects() {
  return PORTRAIT ? [[60, 390, 960, 520], [60, 980, 960, 520]] : [[150, 210, 780, 640], [990, 210, 780, 640]];
}

function beforeAfter(ctx, t, p, A, o) {
  const B = { ...COPY.beforeAfter, ...p }, P = PORTRAIT, [[ax, ay, aw, ah], [bx, by, bw, bh]] = baRects();
  if (o.preview) { placeholder(ctx, ax, ay, aw, ah, 'CLIP · BEFORE'); placeholder(ctx, bx, by, bw, bh, 'CLIP · AFTER'); }
  const [lc, l] = layer();
  field(l, t, { rail: false });
  const mA = 0.55, openA = snap(t, 0.3, 0.25), mD = 3.8, div = snap(t, 3.6, 0.2), openB = snap(t, mD + HOLD, 0.25), mB = mD + HOLD + 0.25;
  box(l, ax, ay - 43, 14, 14, C.sky, tagIn(t));
  rise(l, up(B.title), ax + 30, ay - 22, snap(t, 0.12, 0.2), { size: 40, track: 3 });
  const cA = ay + ah / 2;
  l.globalCompositeOperation = 'destination-out';
  l.fillRect(ax, cA - (ah / 2) * openA, aw, ah * openA);
  if (P) l.fillRect(bx, by, bw, bh * openB); else l.fillRect(bx, by, bw * openB, bh);
  l.globalCompositeOperation = 'source-over';
  box(l, ax, ay, aw, ah, C.navy, 0.5 * reward(t, mB, 0.9) * (openA >= 1 ? 1 : 0));
  box(l, ax, cA - (ah / 2) * openA - 3, aw, 3, C.sky, openA > 0 ? 1 : 0);
  box(l, ax, cA + (ah / 2) * openA, aw, 3, C.sky, openA > 0 ? 1 : 0);
  const ch = snap(t, mD, 0.12);
  l.save(); l.fillStyle = C.amber; l.beginPath();
  if (P) {
    const gy = ay + ah + 35;
    box(l, ax, gy - 2, aw * div, 4, C.sky);
    if (openB > 0) box(l, bx, by + bh * openB, bw, 3, C.sky);
    if (ch > 0) { l.moveTo(W / 2 - 22 * ch, gy - 14); l.lineTo(W / 2 + 22 * ch, gy - 14); l.lineTo(W / 2, gy - 14 + 30 * ch); }
  } else {
    const gx = ax + aw + 30;
    box(l, gx - 2, ay, 4, ah * div, C.sky);
    if (openB > 0) box(l, bx + bw * openB, by, 3, bh, C.sky);
    if (ch > 0) { const cy = ay + ah / 2; l.moveTo(gx - 14, cy - 22 * ch); l.lineTo(gx - 14, cy + 22 * ch); l.lineTo(gx - 14 + 30 * ch, cy); }
  }
  l.fill(); l.restore();
  const chip = (s, x, y, pp, bg) => {
    if (pp <= 0) return;
    const w = tw(l, s, 28, 800, 5) + 56;
    l.save(); l.beginPath(); l.rect(x + 24, y + 24, w * pp, 60); l.clip();
    box(l, x + 24, y + 24, w, 60, bg); text(l, s, x + 52, y + 64, { size: 28, track: 5 });
    l.restore();
  };
  chip(up(B.a), ax, ay, snap(t, mA + HOLD, 0.18), C.slate);
  chip(up(B.b), bx, by, snap(t, mB + HOLD, 0.18), C.sky);
  ctx.drawImage(lc, 0, 0);
}

function steps(ctx, t, p, A, o) {
  const S = { ...COPY.tip, ...p }, list = S.steps.slice(0, 4), n = list.length, P = PORTRAIT, dur = o.dur;
  // p.times (seconds from the card's start, one per step) makes each step land as it is spoken
  const gapT = n > 1 ? Math.min(2.6, (dur - 4.8) / (n - 1)) : 0;
  const T = Array.isArray(S.times) && S.times.length >= n ? S.times.slice(0, n) : list.map((_, k) => 1.3 + k * gapT), allOn = T[n - 1] + 2.4;
  field(ctx, t); tag(ctx, tagIn(t));
  const title = P ? S.title : [S.title.join(' ')];
  soft(ctx, up(S.eyebrow), L, P ? 420 : 210, outCubic(prog(t, 0.15, 0.4)), { size: 30, weight: 700, color: C.sky, track: 8 });
  heading(ctx, title.map(up), t, P ? 540 : 320, P ? 128 : 100);
  const dimOf = (k) => { let a = 1; if (k < n - 1) a = 1 - 0.62 * inOut(prog(t, T[k + 1] - 0.1, 0.4)); return lerp(a, 1, inOut(prog(t, allOn, 0.5))); };
  if (P) {
    const sp = n > 3 ? 200 : 240, ys = list.map((_, k) => 800 + k * sp);
    list.forEach((s, k) => {
      const m = T[k] + 0.2, mN = m + HOLD + 0.18;
      ctx.save(); ctx.globalAlpha = dimOf(k);
      box(ctx, L, ys[k], CW * snap(t, T[k], 0.2), 3, C.sky, 0.7);
      rise(ctx, `0${k + 1}`, L, ys[k] + 150, snap(t, m + HOLD, 0.18), { size: 132, color: C.sky });
      wrap(ctx, s, CW - 250, 46, 600).slice(0, 3).forEach((ln, i) => soft(ctx, ln, L + 250, ys[k] + 94 + i * 60, reward(t, mN + i * 0.12, 0.7), { size: 46, weight: 600 }));
      ctx.restore();
      mark(ctx, ys[k], t - m);
    });
    let my = ys[0];
    for (let k = 1; k < n; k++) my += (ys[k] - ys[k - 1]) * snap(t, T[k], 0.2);
    const sq = snap(t, T[0], 0.12);
    box(ctx, RAIL + 5, ys[0], 4, my - ys[0], C.sky);
    box(ctx, RAIL + 7 - 10 * sq, my - 10 * sq, 20 * sq, 20 * sq, C.amber);
  } else {
    const colW = CW / n, ly = 520;
    list.forEach((s, k) => {
      const x = L + k * colW, m = T[k] + 0.2, mN = m + HOLD + 0.18;
      ctx.save(); ctx.globalAlpha = dimOf(k);
      box(ctx, x, ly, (colW - 50) * snap(t, T[k], 0.2), 3, C.sky, 0.7);
      rise(ctx, `0${k + 1}`, x, ly + 150, snap(t, m + HOLD, 0.18), { size: 120, color: C.sky });
      wrap(ctx, s, colW - 70, 40, 600).slice(0, 4).forEach((ln, i) => soft(ctx, ln, x, ly + 230 + i * 54, reward(t, mN + i * 0.12, 0.7), { size: 40, weight: 600 }));
      ctx.restore();
      mark(ctx, ly, t - m);
    });
    let mx = L;
    for (let k = 1; k < n; k++) mx += colW * snap(t, T[k], 0.2);
    const sq = snap(t, T[0], 0.12);
    box(ctx, L, ly - 40, mx - L, 4, C.sky);
    box(ctx, mx - 10 * sq, ly - 38 - 10 * sq, 20 * sq, 20 * sq, C.amber);
  }
}

function quote(ctx, t, p) {
  const Q = { ...COPY.quote, ...p }, P = PORTRAIT;
  field(ctx, t); tag(ctx, tagIn(t));
  const tx = P ? L : L + 250, tw_ = P ? CW : CW - 250;
  let size = P ? 66 : 62, lines;
  for (;;) { lines = wrap(ctx, Q.text, tw_, size, 600); if (lines.length * size * 1.42 <= (P ? 660 : 470) || size <= 40) break; size -= 2; }
  const lh = size * 1.42, y0 = P ? 700 : 560 - ((lines.length - 1) * lh) / 2 - 40;
  rise(ctx, '“', P ? L - 18 : L - 10, P ? 810 : y0 + 250, snap(t, 0.3, 0.2), { size: P ? 560 : 420, color: C.sky });
  mark(ctx, P ? 480 : y0 - 60, t - 0.5);
  const all = String(Q.text).split(/\s+/).filter(Boolean), total = all.length, hlP = inOut(prog(t, 3.5, 0.7));
  let wi = 0;
  lines.forEach((ln, i) => {
    const pp = outQuint(prog(t, 0.75 + i * 0.24, 0.7));
    let x = tx;
    for (const w of ln.split(' ')) {
      const on = wi >= total - (Q.highlight || 0); wi++;
      if (pp > 0) text(ctx, w, x, y0 + i * lh + (1 - pp) * 30, { size, weight: 600, alpha: pp, color: on ? mix(C.white, C.sky, hlP) : C.white });
      x += tw(ctx, `${w} `, size, 600);
    }
  });
  const end = y0 + (lines.length - 1) * lh, mQ = 2.78;
  box(ctx, tx, end + 76, 110 * snap(t, mQ - 0.18, 0.18), 10, C.amber); mark(ctx, end + 81, t - mQ);
  if (Q.by) soft(ctx, up(Q.by), tx, end + 160, reward(t, mQ, 0.8), { size: 36, track: 4 });
  if (Q.src) soft(ctx, Q.src, tx, end + 214, reward(t, mQ + 0.15, 0.8), { size: 28, weight: 600, color: C.sky, track: 1 });
}

function programs(ctx, t, p) {
  const PR = { ...COPY.programs, ...p }, list = PR.list.slice(0, 8), n = list.length, P = PORTRAIT, H0 = 4.1, ST = 0.6;
  field(ctx, t); tag(ctx, tagIn(t));
  soft(ctx, up(PR.eyebrow), L, P ? 410 : 210, outCubic(prog(t, 0.15, 0.4)), { size: 30, weight: 700, color: C.sky, track: 8 });
  const hd = heading(ctx, (P ? PR.title : [PR.title.join(' ')]).map(up), t, P ? 500 : 300, P ? 84 : 76);
  box(ctx, L, hd.last + 30, 110 * snap(t, hd.tMark + HOLD, 0.15), 10, C.amber);
  const rows = P ? n : Math.ceil(n / 2), rh = P ? 100 : 110, colW = P ? CW : CW / 2;
  const pos = (i) => (P ? [L, 690 + i * rh] : [L + Math.floor(i / rows) * colW, 430 + (i % rows) * rh]);
  let sx = 0, sy = 0, slabA = 0, slabW = 0;
  if (t >= H0) {
    const k = Math.min(n - 1, Math.floor((t - H0) / ST));
    const [x1, y1] = pos(k), [x0, y0] = k ? pos(k - 1) : pos(0), e = k ? snap(t, H0 + k * ST, 0.14) : 1;
    sx = lerp(x0, x1, e); sy = lerp(y0, y1, e);
    slabW = snap(t, H0, 0.18); slabA = 1 - outQuint(prog(t, H0 + n * ST, 0.6));
    box(ctx, sx - 24, sy + 8, (colW - (P ? 0 : 40) + 48) * slabW, rh - 16, C.sky, slabA);
  }
  list.forEach((s, i) => {
    const Ti = 1.2 + i * 0.26, name = up(s), size = fit(ctx, name, colW - (P ? 120 : 160), 50), [x, y] = pos(i);
    const cover = slabA > 0 ? clamp(1 - Math.hypot(sx - x, sy - y) / (rh * 0.6)) * slabW * slabA : 0;
    trail(ctx, t, (tt) => {
      if (tt < Ti) return;
      const dx = (1 - snap(tt, Ti, 0.2)) * 760;
      text(ctx, String(i + 1).padStart(2, '0'), x + dx, y + 64, { size: 28, weight: 700, color: mix(C.sky, C.white, cover), track: 2 });
      text(ctx, name, x + 96 + dx, y + 68, { size, track: 1 });
    });
    box(ctx, x, y + rh - 1, (colW - (P ? 0 : 40)) * snap(t, Ti, 0.2), 2, C.sky, 0.28);
    mark(ctx, y + rh / 2, t - (Ti + 0.2));
  });
}

function dates(ctx, t, p) {
  const D = { ...COPY.dates, ...p }, P = PORTRAIT, MON = ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER'];
  const months = D.months.slice(0, 4);
  field(ctx, t); tag(ctx, tagIn(t));
  soft(ctx, up(D.eyebrow), L, P ? 410 : 210, outCubic(prog(t, 0.15, 0.4)), { size: 30, weight: 700, color: C.sky, track: 6 });
  heading(ctx, (P ? D.title : [D.title.join(' ')]).map(up), t, P ? 505 : 300, P ? 96 : 80);
  const mL = 1.0, ly = P ? 716 : 380;
  box(ctx, L, ly, 96 * snap(t, mL - 0.15, 0.15), 10, C.amber); mark(ctx, ly + 5, t - mL);
  soft(ctx, up(D.label), L, ly + 76, reward(t, mL, 0.6), { size: 34, weight: 700, track: 10 });
  const TM = months.map((_, i) => 1.5 + 0.6 * i);
  if (P) {
    const size = Math.min(...months.map((m) => fit(ctx, MON[m], CW, months.length > 2 ? 150 : 190)));
    months.forEach((m, i) => {
      const base = 980 + i * (size * 0.72 + 44);
      rise(ctx, MON[m], L, base, snap(t, TM[i], 0.2), { size, color: i ? C.white : C.sky });
      mark(ctx, base - size * 0.36, t - (TM[i] + 0.2));
    });
  } else {
    const cw = CW / months.length, size = Math.min(...months.map((m) => fit(ctx, MON[m], cw - 50, 170)));
    months.forEach((m, i) => {
      rise(ctx, MON[m], L + i * cw, 680, snap(t, TM[i], 0.2), { size, color: i ? C.white : C.sky });
      mark(ctx, 680 - size * 0.36, t - (TM[i] + 0.2));
    });
  }
  const ry = P ? 1330 : 830, draw = snap(t, 0.9, 0.5);
  for (let m = 0; m < 12; m++) {
    const x = L + (CW * (m + 0.5)) / 12, k = months.indexOf(m);
    if ((m + 0.5) / 12 > draw) continue;
    const upk = k >= 0 ? snap(t, TM[k] + 0.2, 0.12) : 0;
    box(ctx, x - 2, ry - 18 - 46 * upk, 4, 18 + 46 * upk, C.sky, lerp(0.4, 1, upk));
    text(ctx, MON[m][0], x, ry + 40, { size: 22, weight: 700, align: 'center', alpha: lerp(0.5, 1, upk) });
  }
  box(ctx, L, ry, CW * draw, 2, C.sky, 0.5);
  const tl = TM[TM.length - 1] + 0.2;
  if (P) {
    soft(ctx, up(D.place), L, 1440, reward(t, tl, 0.8), { size: 30, weight: 700, track: 5 });
    soft(ctx, D.url ?? COPY.url, L, 1492, reward(t, tl + 0.2, 0.8), { size: 28, weight: 600, color: C.sky, track: 2 });
  } else {
    soft(ctx, up(D.place), L, 950, reward(t, tl, 0.8), { size: 30, weight: 700, track: 5 });
    soft(ctx, D.url ?? COPY.url, R, 950, reward(t, tl + 0.2, 0.8), { size: 28, weight: 600, color: C.sky, track: 2, align: 'right' });
  }
}

function endCard(ctx, t, p, A, o) {
  const E = { ...COPY.end, ...p }, P = PORTRAIT, DUR = o.dur, OUT = DUR - 0.7;
  const cx = W / 2, cy = P ? 720 : 330, s0 = P ? 1 : 0.6, pw = 720 * s0, ph = 640 * s0, hw = P ? 380 : 300;
  field(ctx, t, { loop: DUR });
  const mO = 0.38, open = snap(t, 0.15, 0.23) * (1 - snap(t, OUT + 0.3, 0.2));
  const hh = logoWindow(ctx, A.logo, cx, cy, pw, ph, open, s0);
  box(ctx, cx - hw, cy - hh - 4, 2 * hw, 4, C.sky); box(ctx, cx - hw, cy + hh, 2 * hw, 4, C.sky);
  const by = P ? 1140 : 590, bw = P ? 560 : 480, bh = P ? 116 : 96, mB = mO + HOLD + 0.2;
  const bo = snap(t, mO + HOLD, 0.2) * (1 - snap(t, OUT + 0.12, 0.16));
  if (bo > 0) {
    ctx.save(); ctx.beginPath(); ctx.rect(cx - (bw / 2) * bo, by, bw * bo, bh); ctx.clip();
    box(ctx, cx - bw / 2, by, bw, bh, C.sky);
    text(ctx, up(E.cta), cx, by + bh / 2 + (P ? 15 : 13), { size: P ? 42 : 36, track: 7, align: 'center' });
    ctx.restore();
  }
  const out = 1 - outCubic(prog(t, OUT, 0.2)), u = snap(t, 1.15, 0.15) * (1 - snap(t, OUT, 0.15));
  box(ctx, cx - 48 * u, by + bh + (P ? 62 : 46), 96 * u, 8, C.amber);
  soft(ctx, E.url ?? COPY.url, cx, by + bh + (P ? 150 : 122), reward(t, mB, 0.7) * out, { size: P ? 54 : 48, align: 'center', track: 1 });
  const contact = [E.phone, E.handle].filter(Boolean).join('   ·   ');
  if (contact) soft(ctx, contact, cx, by + bh + (P ? 216 : 178), reward(t, mB + 0.15, 0.7) * out, { size: 30, weight: 600, color: C.sky, track: 2, align: 'center' });
  mark(ctx, cy, t - mO); mark(ctx, by + bh / 2, t - mB);
}

// ------------------------------------------------------------------ OVERLAYS (on the footage)

function lower(ctx, t, p, A, o) {
  const name = up(p.name || COPY.lower.name), role = up(p.role || COPY.lower.role), P = PORTRAIT;
  const x = P ? 80 : 110, y = P ? 1290 : H - 330, OUT = o.dur - 0.7, m1 = 0.4;
  const PH = P ? 136 : 118, RH = P ? 78 : 66, MAXW = P ? 800 : 900;
  const ns = fit(ctx, name, MAXW, P ? 86 : 74, 800, 2 / 86), rs = fit(ctx, role, MAXW, P ? 37 : 31, 800, 4 / 37);
  const bar = snap(t, 0.2, 0.2) * (1 - snap(t, OUT + 0.3, 0.15));
  const open = snap(t, m1 + HOLD, 0.28) * (1 - snap(t, OUT + 0.1, 0.2)), m2 = m1 + HOLD + 0.28;
  const rp = reward(t, m2, 0.7) * (1 - outCubic(prog(t, OUT, 0.15)));
  const bw = Math.max(tw(ctx, name, ns, 800, 2), tw(ctx, role, rs, 800, 4)) + 96;
  ctx.save(); ctx.beginPath(); ctx.rect(x + 14, y + PH, bw, RH * rp); ctx.clip();
  box(ctx, x + 14, y + PH, bw, RH, C.sky);
  text(ctx, role, x + 58, y + PH + RH / 2 + rs * 0.36 - (1 - rp) * 30, { size: rs, weight: 800, track: 4 });
  ctx.restore();
  ctx.save(); ctx.beginPath(); ctx.rect(x + 14, y, bw * open, PH); ctx.clip();
  box(ctx, x + 14, y, bw, PH, C.navy, 0.94);
  text(ctx, name, x + 58, y + PH / 2 + ns * 0.36, { size: ns, track: 2 });
  ctx.restore();
  const sq = snap(t, m2, 0.1) * (1 - snap(t, OUT, 0.1));
  box(ctx, x + 14 + bw + 14, y, 18 * sq, 18 * sq, C.amber);
  // the bar flashes white for the 4 held frames: that is the marker on footage
  const flash = t >= m1 && t < m1 + HOLD ? 1 : 1 - prog(t, m1 + HOLD, 0.25);
  box(ctx, x, y, 14, (PH + RH) * bar, t >= m1 ? mix(C.sky, C.white, flash) : C.sky);
}

// Section plate over footage: small eyebrow + one title line, top left.
function title(ctx, t, p0, A, o) {
  const p = { ...COPY.title, ...p0 }, P = PORTRAIT, y = P ? 330 : 150, out = 1 - snap(t, o.dur - 0.32, 0.22);
  if (out <= 0) return;
  const g = ctx.createLinearGradient(0, 0, 0, y + 260);
  g.addColorStop(0, `rgba(0,16,46,${0.55 * out})`); g.addColorStop(1, 'rgba(0,16,46,0)');
  ctx.save(); ctx.fillStyle = g; ctx.fillRect(0, 0, W, y + 260); ctx.restore();
  ctx.save(); ctx.beginPath(); ctx.rect(0, 0, W, y + 200 * out); ctx.clip();
  if (p.eyebrow) soft(ctx, up(p.eyebrow), L, y, outCubic(prog(t, 0.05, 0.35)), { size: 28, weight: 700, color: C.sky, track: 7, shadow: 1 });
  const s = up(p.text || ''), size = fit(ctx, s, CW, P ? 80 : 76);
  rise(ctx, s, L, y + 30 + size * 0.8, snap(t, 0.12, 0.2), { size, shadow: 1 });
  box(ctx, L, y + 60 + size * 0.8, 96 * snap(t, 0.32 + HOLD, 0.15), 9, C.amber);
  ctx.restore();
}

// Social hook: the strongest line as big type over the action. p.lines use *word* for emphasis;
// p.times (seconds from the event start, one per word) makes each word land as it is spoken.
// Split words into k lines of about equal length, never inside an emphasised (light-blue) phrase.
function balanced(words, k) {
  const units = [];
  for (const w of words) { const u = units[units.length - 1]; if (w.em && u && u[u.length - 1].em) u.push(w); else units.push([w]); }
  const len = (u) => u.reduce((a, w) => a + w.s.length + 1, 0);
  const total = units.reduce((a, u) => a + len(u), 0), out = [[]]; let acc = 0;
  for (const u of units) {
    if (out[out.length - 1].length && out.length < k && acc >= (total / k) * out.length - 1e-9) out.push([]);
    out[out.length - 1].push(...u); acc += len(u);
  }
  return out;
}
function hook(ctx, t, p, A, o) {
  const P = PORTRAIT, maxW = P ? CW + 40 : 1150, maxS = P ? 150 : 128, avail = P ? 900 : 720;
  let lines = (p.lines || COPY.hook.lines).map(parseWords);
  const all = lines.flat(), n = all.length;
  const sizeOf = (ls) => Math.min(maxS, avail / (ls.length * 1.12), ...ls.map((ws) => fit(ctx, ws.map((w) => w.s).join(' '), maxW, maxS)));
  let size = sizeOf(lines);
  // the edit's own line breaks win unless more, shorter lines make the type clearly bigger (at most 4 lines)
  if (size < maxS * 0.8) for (let k = 1; k <= Math.min(4, n); k++) { const ls = balanced(all, k), s = sizeOf(ls); if (s > size * 1.08) { lines = ls; size = s; } }
  const yf = (p.y || {})[P ? 'vertical' : 'horizontal'];          // edit file: HOOK = dict(..., y={"vertical": 0.4})
  const lh = size * 1.12, blockH = (lines.length - 1) * lh, cy = yf ? yf * H : (P ? 820 : 540), y0 = cy - blockH / 2 + size * 0.36;
  const sc = clamp(t / 0.18);
  if (P) {
    const g = ctx.createLinearGradient(0, cy - blockH / 2 - 420, 0, cy + blockH / 2 + 420);
    g.addColorStop(0, 'rgba(0,16,46,0)'); g.addColorStop(0.5, `rgba(0,16,46,${0.62 * sc})`); g.addColorStop(1, 'rgba(0,16,46,0)');
    ctx.save(); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); ctx.restore();
  } else {
    const g = ctx.createLinearGradient(0, 0, 1500, 0);
    g.addColorStop(0, `rgba(0,16,46,${0.7 * sc})`); g.addColorStop(1, 'rgba(0,16,46,0)');
    ctx.save(); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); ctx.restore();
  }
  const step = Math.min(0.24, (o.dur * 0.55) / Math.max(1, n));
  const times = Array.isArray(p.times) && p.times.length === n ? p.times : all.map((_, i) => 0.08 + i * step);
  let k = 0, lastEm = null;
  lines.forEach((ws, li) => {
    const lw = tw(ctx, ws.map((w) => w.s).join(' '), size), base = y0 + li * lh;
    let x = P ? W / 2 - lw / 2 : L, run = null;
    ws.forEach((w) => {
      const ti = times[k++], wwid = tw(ctx, w.s, size);
      rise(ctx, w.s, x, base, snap(t, ti, 0.16), { size, color: w.em ? C.sky : C.white, shadow: 1 });
      if (w.em) { run = run || { x, y: base + size * 0.1 }; run.w = x + wwid - run.x; run.t = ti; lastEm = run; } else run = null;
      x += wwid + tw(ctx, ' ', size);
    });
    mark(ctx, base - size * 0.36, t - (times[k - 1] + 0.16));
  });
  if (lastEm) box(ctx, lastEm.x, lastEm.y, lastEm.w * snap(t, Math.max(lastEm.t + 0.25, times[n - 1] + 0.2), 0.18), 10, C.amber);
}

// Burned-in captions. p.chunks: [{t0, t1, words: [{w, t0, t1}]}] in seconds from the event start.
// The word being spoken sits on a sky box (white text, the house rule). p.avoid: [[a, b]] windows where a
// lower third is on screen; in 16:9 the captions lift above it.
function captions(ctx, t, p) {
  const ch = (p.chunks || COPY.captions.chunks).find((c) => t >= c.t0 && t < c.t1);
  if (!ch) return;
  const P = PORTRAIT, words = ch.words.map((w) => up(w.w)), maxW = P ? CW + 80 : 1400, maxS = P ? 78 : 66;
  let lines = [words], size = fit(ctx, words.join(' '), maxW, maxS, 800, 0.02);
  if (size < maxS * 0.82 && words.length > 1) {
    let best = 1, bestD = 1e9;
    for (let i = 1; i < words.length; i++) {
      const d = Math.abs(tw(ctx, words.slice(0, i).join(' '), 100) - tw(ctx, words.slice(i).join(' '), 100));
      if (d < bestD) { bestD = d; best = i; }
    }
    lines = [words.slice(0, best), words.slice(best)];
    size = Math.min(...lines.map((ws) => fit(ctx, ws.join(' '), maxW, maxS, 800, 0.02)));
  }
  const lifted = !P && (p.avoid || []).some(([a, b]) => t >= a - 0.2 && t < b + 0.2);
  const yf = (p.y || {})[P ? 'vertical' : 'horizontal'];          // edit file: CAPTION_Y
  const lh = size * 1.18, cy = (yf ? yf * H : (P ? 1170 : 900)) - (lifted ? 230 : 0), y0 = cy - ((lines.length - 1) * lh) / 2 + size * 0.36;
  const e = snap(t, ch.t0, 0.1), sc = 0.94 + 0.06 * e, track = size * 0.02, space = tw(ctx, ' ', size) + track;
  let ai = 0; ch.words.forEach((w, i) => { if (t >= w.t0 - 0.03) ai = i; });
  ctx.save(); ctx.translate(W / 2, cy); ctx.scale(sc, sc); ctx.translate(-W / 2, -cy);
  const boxes = []; let k = 0;
  lines.forEach((ws, li) => {
    const widths = ws.map((w) => tw(ctx, w, size, 800, track)), lw = widths.reduce((a, b) => a + b, 0) + space * (ws.length - 1);
    let x = W / 2 - lw / 2;
    ws.forEach((w, i) => { boxes.push({ x, y: y0 + li * lh, w: widths[i], s: w, k: k++ }); x += widths[i] + space; });
  });
  const cur = boxes[ai], prev = boxes[Math.max(0, ai - 1)], mv = ai ? snap(t, ch.words[ai].t0 - 0.03, 0.08) : 1;
  const bx = lerp(prev.x, cur.x, mv), bwid = lerp(prev.w, cur.w, mv), byy = lerp(prev.y, cur.y, mv), px = size * 0.16;
  box(ctx, bx - px, byy - size * 0.82, bwid + 2 * px, size * 1.04, C.sky);
  boxes.forEach((b) => text(ctx, b.s, b.x, b.y, { size, track, shadow: b.k === ai ? 0 : 1 }));
  ctx.restore();
}

// id, base length (a shorter event plays the animation faster), card (opaque full frame) or overlay
export const SCENES = [
  { id: 'logo-sting', base: 3, card: false, draw: sting },
  { id: 'kinetic', base: 6, card: true, draw: kinetic },
  { id: 'stat', base: 6, card: true, draw: stat },
  { id: 'before-after', base: 8, card: true, draw: beforeAfter },
  { id: 'steps', base: 10, card: true, draw: steps },
  { id: 'quote', base: 7, card: true, draw: quote },
  { id: 'programs', base: 10, card: true, draw: programs },
  { id: 'dates', base: 6, card: true, draw: dates },
  { id: 'end-card', base: 4, card: true, draw: endCard },
  { id: 'lower-third', base: 4, card: false, draw: lower },
  { id: 'title', base: 2, card: false, draw: title },
  { id: 'hook', base: 1.5, card: false, draw: hook },
  { id: 'captions', base: 0, card: false, draw: captions },
];
