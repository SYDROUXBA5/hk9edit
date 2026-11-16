// Shared drawing kit. One motion signature for every graphic: "mark, then reward".
// A move arrives still travelling and stops dead (snap), sits for 4 frames (HOLD),
// then whatever follows eases in softly (reward).
// The canvas size is set per job with setFormat(): 1080x1920 (vertical) or 1920x1080 (horizontal).
export const FPS = 30;
// Colours read from highlandcanine.com CSS (navy, slate, sky, deep) and sampled from the logo file (amber).
// House rule: text on a sky (light blue) fill is always white.
export const C = { navy: '#00102e', slate: '#233452', sky: '#16a5e2', deep: '#0480b7', amber: '#f4ab12', white: '#ffffff' };

export let W = 1080, H = 1920, PORTRAIT = true;
// Text stays clear of the top 250 px and bottom 400 px in 9:16 (app chrome on Reels / TikTok / Shorts),
// and inside the title-safe area in 16:9.
export let SAFE = { top: 250, bottom: 1520, left: 120, right: 984 };
export let L = SAFE.left, R = SAFE.right, CW = R - L;
export function setFormat(w, h) {
  W = w; H = h; PORTRAIT = h >= w;
  SAFE = PORTRAIT ? { top: 250, bottom: 1520, left: 120, right: 984 } : { top: 90, bottom: 990, left: 160, right: 1760 };
  L = SAFE.left; R = SAFE.right; CW = R - L; scratch = null;
}

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, t) => a + (b - a) * t;
export const prog = (t, t0, d) => clamp((t - t0) / d);
export const outCubic = (x) => 1 - (1 - x) ** 3;
export const outQuint = (x) => 1 - (1 - x) ** 5;
export const inOut = (x) => (x < 0.5 ? 4 * x ** 3 : 1 - (-2 * x + 2) ** 3 / 2);
export const HOLD = 4 / FPS;
export const snap = (t, t0, d = 0.2) => { const x = prog(t, t0, d); return 0.7 * outCubic(x) + 0.3 * x; };
export const reward = (t, tMark, d = 0.8) => outQuint(prog(t, tMark + HOLD, d));

const rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
export const mix = (a, b, p) => { const x = rgb(a), y = rgb(b); return `rgb(${x.map((v, i) => Math.round(lerp(v, y[i], clamp(p)))).join(',')})`; };

export function font(ctx, size, weight = 800, track = 0) { ctx.font = `${weight} ${size}px HK9Sans`; ctx.letterSpacing = `${track}px`; }
export function tw(ctx, s, size, weight = 800, track = 0) { ctx.save(); font(ctx, size, weight, track); const w = ctx.measureText(s).width - track; ctx.restore(); return w; }
// Largest size (up to max) at which s fits in maxW. trackEm = letter spacing as a fraction of the size.
export const fit = (ctx, s, maxW, max, weight = 800, trackEm = 0) => Math.min(max, (100 * maxW) / Math.max(1, tw(ctx, s, 100, weight, trackEm * 100)));

export function text(ctx, s, x, y, { size = 60, weight = 800, color = C.white, track = 0, align = 'left', alpha = 1, shadow = 0 } = {}) {
  if (alpha <= 0) return;
  ctx.save(); font(ctx, size, weight, track);
  ctx.textAlign = align; ctx.textBaseline = 'alphabetic'; ctx.fillStyle = color; ctx.globalAlpha *= alpha;
  if (shadow) { ctx.shadowColor = `rgba(0,10,30,${0.7 * shadow})`; ctx.shadowBlur = size * 0.35; ctx.shadowOffsetY = size * 0.04; }
  ctx.fillText(s, align === 'center' ? x + track / 2 : align === 'right' ? x + track : x, y);
  ctx.restore();
}
// Text that rises from behind its own baseline (used with snap: it lands hard).
export function rise(ctx, s, x, y, p, o = {}) {
  if (p <= 0) return;
  const size = o.size || 60;
  ctx.save(); ctx.beginPath(); ctx.rect(0, y - size * 1.02, W, size * 1.3); ctx.clip();
  text(ctx, s, x, y + (1 - p) * size * 1.2, o);
  ctx.restore();
}
// Text that fades up softly (used with reward).
export function soft(ctx, s, x, y, p, o = {}) { if (p > 0) text(ctx, s, x, y + (1 - p) * 30, { ...o, alpha: (o.alpha ?? 1) * p }); }

export function wrap(ctx, s, maxW, size, weight = 600, track = 0) {
  ctx.save(); font(ctx, size, weight, track);
  const out = []; let line = '';
  for (const w of String(s).split(/\s+/).filter(Boolean)) {
    const tr = line ? `${line} ${w}` : w;
    if (ctx.measureText(tr).width - track > maxW && line) { out.push(line); line = w; } else line = tr;
  }
  if (line) out.push(line);
  ctx.restore(); return out;
}

export function box(ctx, x, y, w, h, color, alpha = 1) { if (w <= 0 || h <= 0 || alpha <= 0) return; ctx.save(); ctx.globalAlpha *= alpha; ctx.fillStyle = color; ctx.fillRect(x, y, w, h); ctx.restore(); }

// Navy field: soft slate glow, a measuring rail on the left edge, vignette.
export const RAIL = 36;
export function field(ctx, t, { loop = 0, rail = true, railShift = null } = {}) {
  const M = Math.max(W, H);
  ctx.save();
  ctx.fillStyle = C.navy; ctx.fillRect(0, 0, W, H);
  const ph = loop ? (Math.PI * 2 * t) / loop : t * 0.45;
  let g = ctx.createRadialGradient(W * 0.2 + Math.cos(ph) * 70, H * 0.24 + Math.sin(ph) * 70, 0, W * 0.2, H * 0.24, M * 0.65);
  g.addColorStop(0, 'rgba(35,52,82,0.95)'); g.addColorStop(0.55, 'rgba(35,52,82,0.3)'); g.addColorStop(1, 'rgba(35,52,82,0)');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  g = ctx.createRadialGradient(W * 0.98, H * 0.86, 0, W * 0.98, H * 0.86, M * 0.47);
  g.addColorStop(0, 'rgba(4,128,183,0.22)'); g.addColorStop(1, 'rgba(4,128,183,0)');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  if (rail) {
    const off = railShift ?? (loop ? (200 * t) / loop : 24 * t);
    const start = (((off % 200) + 200) % 200) - 200;
    ctx.fillStyle = C.sky;
    for (let i = 0, y = start; y < H + 40; i++, y += 40) {
      const major = i % 5 === 0;
      ctx.globalAlpha = major ? 0.34 : 0.17;
      ctx.fillRect(RAIL, y - 1, major ? 30 : 14, 2);
    }
    ctx.globalAlpha = 1;
  }
  g = ctx.createRadialGradient(W / 2, H / 2, M * 0.34, W / 2, H / 2, M * 0.76);
  g.addColorStop(0, 'rgba(0,6,20,0)'); g.addColorStop(1, 'rgba(0,6,20,0.6)');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  ctx.restore();
}

// The marker: a white dash that fires on the rail at the instant something stops.
export function mark(ctx, y, dt) {
  if (dt < 0 || dt > HOLD + 0.3) return;
  const a = dt < HOLD ? 1 : 1 - (dt - HOLD) / 0.3;
  box(ctx, RAIL - 12, y - 3, 66, 6, C.white, a);
  box(ctx, RAIL + 54, y - 1, 8 + 14 * outCubic(prog(dt, 0, 0.25)), 2, C.white, a * 0.5);
}

export function tag(ctx, p, y = PORTRAIT ? 300 : 140) {
  if (p <= 0) return;
  box(ctx, L, y - 19, 14, 14, C.sky, p);
  text(ctx, 'HIGHLAND CANINE TRAINING, LLC', L + 30, y - 6, { size: 22, weight: 700, track: 5, alpha: 0.9 * p });
}

// Fast moves leave a short trail so they read as speed, not as a jump cut.
export function trail(ctx, t, fn, n = 4, dt = 1 / 150) {
  for (let i = n; i >= 1; i--) { ctx.save(); ctx.globalAlpha *= 0.16; fn(t - i * dt); ctx.restore(); }
  fn(t);
}

let scratch = null;
export function layer() {
  if (!scratch || scratch.width !== W || scratch.height !== H) scratch = new OffscreenCanvas(W, H);
  const x = scratch.getContext('2d');
  x.setTransform(1, 0, 0, 1, 0, 0); x.globalAlpha = 1; x.globalCompositeOperation = 'source-over'; x.clearRect(0, 0, W, H);
  return [scratch, x];
}

// Stand-in for footage in previews and contact sheets.
export function placeholder(ctx, x, y, w, h, label) {
  ctx.save(); ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip();
  const g = ctx.createLinearGradient(x, y, x + w, y + h);
  g.addColorStop(0, '#465166'); g.addColorStop(1, '#1d2636');
  ctx.fillStyle = g; ctx.fillRect(x, y, w, h);
  ctx.strokeStyle = 'rgba(255,255,255,0.06)'; ctx.lineWidth = 2;
  for (let i = -h; i < w; i += 36) { ctx.beginPath(); ctx.moveTo(x + i, y + h); ctx.lineTo(x + i + h, y); ctx.stroke(); }
  ctx.restore();
  text(ctx, label, x + w / 2, y + h / 2 + 10, { size: 28, weight: 700, track: 8, align: 'center', alpha: 0.42 });
}

let gp;
export function grain(ctx, frame) {
  if (!gp) {
    const n = 512, c = new OffscreenCanvas(n, n), x = c.getContext('2d'), d = x.createImageData(n, n);
    let s = 1234567;
    const rnd = () => { s = (s + 0x6d2b79f5) | 0; let r = Math.imul(s ^ (s >>> 15), 1 | s); r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r; return ((r ^ (r >>> 14)) >>> 0) / 4294967296; };
    for (let i = 0; i < n * n; i++) {
      const v = rnd(), w = v > 0.5;
      d.data[i * 4] = d.data[i * 4 + 1] = d.data[i * 4 + 2] = w ? 255 : 0;
      d.data[i * 4 + 3] = Math.abs(v - 0.5) * 2 * (w ? 16 : 20);
    }
    x.putImageData(d, 0, 0); gp = c;
  }
  const ox = (frame * 197) % 512, oy = (frame * 89) % 512;
  ctx.save(); ctx.translate(-ox, -oy); ctx.fillStyle = ctx.createPattern(gp, 'repeat'); ctx.fillRect(ox, oy, W, H); ctx.restore();
}
