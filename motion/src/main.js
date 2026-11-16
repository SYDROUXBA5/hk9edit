// Entry point. Driven by scripts/gfx.py: it serves this folder, opens it in headless Edge/Chrome with ?job=1,
// and the page renders the job's frames and POSTs each PNG back. Opened by hand (?preview) it plays one scene.
import { SCENES } from './scenes.js';
import { setFormat, grain, placeholder, FPS, W, H } from './kit.js';

const cv = document.getElementById('c'), ctx = cv.getContext('2d', { willReadFrequently: true });
const SC = Object.fromEntries(SCENES.map((s) => [s.id, s]));
const q = new URLSearchParams(location.search);
const say = (path, body) => fetch(path, { method: 'POST', body }).catch(() => {});
window.addEventListener('error', (e) => say('/fail', String(e.message || e)));
window.addEventListener('unhandledrejection', (e) => say('/fail', String(e.reason && e.reason.stack || e.reason)));

const face = new FontFace('HK9Sans', 'url(fonts/HK9Sans-lnum.ttf)', { weight: '100 900' });   // Raleway, lining figures (fonts/README.txt)
await face.load(); document.fonts.add(face);
const img = (src) => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error('cannot load ' + src)); i.src = src; });
const A = { logo: await img('assets/logo-transparent.png') };

// Draw every event active at time t (seconds) into the canvas. Returns false when nothing is on screen.
let SCALE = 1, GRAIN = true;   // a job may draw at a fraction of full size (previews) and leave the grain to ffmpeg
function drawAt(events, t, frame, preview) {
  const act = events.filter((e) => t >= e.t0 - 1e-6 && t < e.t0 + e.dur - 1e-6);
  ctx.setTransform(SCALE, 0, 0, SCALE, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
  ctx.clearRect(0, 0, W, H);
  if (!act.length) return false;
  if (preview && !act.some((e) => SC[e.scene].card)) placeholder(ctx, 0, 0, W, H, 'YOUR FOOTAGE');
  for (const e of act) {
    const sc = SC[e.scene];
    if (!sc) throw new Error('unknown graphic ' + e.scene);
    let tt = t - e.t0, d = e.dur;
    if (sc.base && d < sc.base && !(e.p && e.p.times)) { tt *= sc.base / d; d = sc.base; }   // short event: play faster
    ctx.save(); sc.draw(ctx, tt, e.p || {}, A, { alpha: !preview, preview, dur: d, frame }); ctx.restore();
  }
  if (GRAIN && act.some((e) => SC[e.scene].card)) grain(ctx, frame);
  return true;
}
// Frames go up as data-URL text, not Blobs: Chrome keeps Blobs in a capped store and refuses uploads after a few
// hundred big frames, while strings are garbage-collected as the loop runs.
const png = () => cv.toDataURL('image/png');

if (q.has('job')) {
  const job = await (await fetch('/job?k=' + q.get('job'))).json();
  SCALE = job.scale || 1; GRAIN = job.grain !== false;
  setFormat(job.W, job.H); cv.width = Math.round(job.W * SCALE); cv.height = Math.round(job.H * SCALE);
  const frames = job.frames || Array.from({ length: job.n }, (_, i) => i);
  // A frame identical to the last one uploaded (a caption or name tag holding still) is not encoded again:
  // the page sends a tiny "same as frame M" note and the server copies the file.
  const sig = () => { const d = ctx.getImageData(0, 0, cv.width, cv.height).data; let a = 2166136261, b = 7; for (let i = 0; i < d.length; i += 16) { a = Math.imul(a ^ (d[i] | d[i + 1] << 8 | d[i + 2] << 16), 16777619) ^ d[i + 3]; b = (b * 31 + d[i + 3] + d[i]) | 0; } return a + ':' + b; };
  let lastSig = null, lastUp = -1;
  const post = async (path, body) => {
    for (let k = 0; ; k++) {                       // a dropped local connection is retried, not fatal
      try { const r = await fetch(path, { method: 'POST', body, headers: { 'Content-Type': 'text/plain' } }); if (r.ok) return; throw new Error('HTTP ' + r.status); }
      catch (err) { if (k >= 4) throw new Error(path + ' failed: ' + err.message); await new Promise((res) => setTimeout(res, 250 * (k + 1))); }
    }
  };
  for (let x = 0; x < frames.length; x++) {
    const i = frames[x], t = job.times ? job.times[x] : i / (job.fps || FPS);
    if (!drawAt(job.events, t, i, !!job.preview)) { lastSig = null; continue; }
    const s = job.times ? null : sig();
    if (s && s === lastSig && lastUp >= 0) { await post('/dup?i=' + i + '&of=' + lastUp, ''); continue; }
    await post('/frame?i=' + i, png()); lastSig = s; lastUp = i;
  }
  await say('/done', String(frames.length));
} else {
  // Preview by hand: index.html?preview=quote&fmt=h  (fmt=v vertical, h horizontal)
  const id = q.get('preview') || 'logo-sting', hz = q.get('fmt') === 'h';
  setFormat(hz ? 1920 : 1080, hz ? 1080 : 1920); cv.width = W; cv.height = H;
  const sc = SC[id], dur = +(q.get('dur') || sc.base || 6), ev = [{ scene: id, t0: 0, dur }];
  let t0 = performance.now();
  const tick = (now) => { const t = ((now - t0) / 1000) % dur; drawAt(ev, t, Math.round(t * FPS), true); requestAnimationFrame(tick); };
  requestAnimationFrame(tick);
}
