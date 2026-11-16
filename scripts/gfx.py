#!/usr/bin/env python3
"""Render the Highland graphics (motion/) with the Edge or Chrome already on the computer. No Node needed.

Usage:  python gfx.py sheet OUT.jpg [--horizontal] [--at 0.62] [--only hook,captions]
            contact sheet: every graphic with its default words, frozen at that fraction of its length
        python gfx.py scene NAME OUT.mp4 [--horizontal] [--dur S] [--params '{"name": "Jane Doe"}'] [--alpha]
            one graphic as its own video (--alpha: transparent .mov, ProRes 4444)
        python gfx.py list
            the graphics and their default lengths
Module: render(job, outdir) draws a job's frames to outdir/f_00000.png ... and returns how many it drew.
Env:    HK9_BROWSER  path to chrome.exe / msedge.exe / the Chrome binary, when it is not found by itself.

How it works: a small local web server serves motion/ to a headless browser; the page draws each frame on a canvas
and posts the PNG back here. Nothing leaves the computer.
"""
import base64, http.server, io, json, os, shutil, subprocess, sys, tempfile, threading, time
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
MOTION = os.path.join(os.path.dirname(HERE), "motion")
FPS = 30
SIZE = {"vertical": (1080, 1920), "horizontal": (1920, 1080)}
SCENES = {  # id: (base seconds, card) -- keep in step with motion/src/scenes.js
    "logo-sting": (3, False), "kinetic": (6, True), "stat": (6, True), "before-after": (8, True), "steps": (10, True),
    "quote": (7, True), "programs": (10, True), "dates": (6, True), "end-card": (4, False),
    "lower-third": (4, False), "title": (2.5, False), "hook": (2.5, False), "captions": (3, False)}
# Footage windows of the before/after card [x, y, w, h] (same numbers as baRects() in scenes.js)
BA_RECTS = {"vertical": [(60, 390, 960, 520), (60, 980, 960, 520)], "horizontal": [(150, 210, 780, 640), (990, 210, 780, 640)]}
TYPES = {".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".ttf": "font/ttf",
         ".png": "image/png", ".json": "application/json", ".css": "text/css"}


def find_browser():
    env = os.environ.get("HK9_BROWSER")
    if env and os.path.isfile(env): return env
    cands = []
    if os.name == "nt":
        for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA"),
                     r"C:\Program Files", r"C:\Program Files (x86)"):
            if base:
                cands += [os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"),
                          os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe")]
    elif sys.platform == "darwin":
        cands += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                  "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    for c in cands:
        if os.path.isfile(c): return c
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "msedge", "chrome"):
        p = shutil.which(name)
        if p: return p
    sys.exit("No Chrome or Edge found. Install Google Chrome (or Microsoft Edge), or set HK9_BROWSER to its .exe path.")


class _Handler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"          # keep-alive: one connection for all frames, not one per frame
    def __init__(self, *a, **kw): super().__init__(*a, directory=MOTION, **kw)
    def log_message(self, *a): pass
    # Windows can map .js to text/plain in the registry, which stops ES modules loading: set the types here.
    def guess_type(self, path): return TYPES.get(os.path.splitext(str(path))[1].lower(), "application/octet-stream")
    def end_headers(self): self.send_header("Cache-Control", "no-store"); super().end_headers()

    def do_GET(self):
        if self.path.startswith("/job"):
            k = int(self.path.split("k=")[1]) if "k=" in self.path else 0
            body = json.dumps(self.server.jobs[k]).encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        return super().do_GET()

    def do_POST(self):
        data = self.rfile.read(int(self.headers.get("Content-Length", 0) or 0)); st = self.server.state
        with st["lock"]:
            if self.path.startswith("/frame"):
                i = int(self.path.split("i=")[1])
                if data[:22] == b"data:image/png;base64,": data = base64.b64decode(data[22:])
                with open(os.path.join(st["out"], f"f_{i:05d}.png"), "wb") as f: f.write(data)
                st["drawn"].add(i); st["last"] = time.time()
            elif self.path.startswith("/dup"):
                q = dict(x.split("=") for x in self.path.split("?")[1].split("&"))
                st["dups"][int(q["i"])] = int(q["of"]); st["last"] = time.time()
            elif self.path.startswith("/done"): st["done"] += 1
            elif self.path.startswith("/fail"): st["error"] = data.decode("utf-8", "replace")
        self.send_response(204); self.send_header("Content-Length", "0"); self.end_headers()


class _Server(http.server.ThreadingHTTPServer):
    daemon_threads = True
    def handle_error(self, request, client_address):      # the browser closing its connection is normal, not an error
        if isinstance(sys.exc_info()[1], (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)): return
        super().handle_error(request, client_address)


def _blank_png(w, h):
    from PIL import Image
    b = io.BytesIO(); Image.new("RGBA", (w, h), (0, 0, 0, 0)).save(b, "PNG"); return b.getvalue()


def render(job, outdir, fill_blanks=True, quiet=False, workers=None):
    """Draw job["events"] ([{scene, t0, dur, p}]) at job["W"] x job["H"]: frames 0..job["n"]-1 at FPS, or the
    explicit job["frames"] (+ job["times"]). Frames with nothing on screen are written as transparent PNGs.
    Long jobs are split across several headless browsers (one per pair of CPU cores, at most 4)."""
    os.makedirs(outdir, exist_ok=True); fps = job.get("fps", FPS)
    if job.get("frames"): todo = list(job["frames"])
    else: todo = [i for i in range(job["n"]) if any(e["t0"] - 1e-6 <= i / fps < e["t0"] + e["dur"] - 1e-6 for e in job["events"])]
    k = 1 if job.get("times") else max(1, min(4, (os.cpu_count() or 2) // 2, len(todo) // 90))
    if workers: k = max(1, min(k, workers))
    size = -(-len(todo) // k) if todo else 1
    jobs = [dict(job, frames=todo[j * size:(j + 1) * size]) for j in range(k)]
    if job.get("times"): jobs = [dict(job)]
    jobs = [j for j in jobs if j["frames"]] or [dict(job, frames=[])]
    srv = _Server(("127.0.0.1", 0), _Handler)
    srv.jobs = jobs; srv.state = st = dict(out=outdir, drawn=set(), dups={}, done=0, error=None, last=time.time(), lock=threading.Lock())
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    exe, procs, profs, t0 = find_browser(), [], [], time.time()
    try:
        def launch(prof, w):
            return [exe, "--headless=new", "--no-first-run", "--no-default-browser-check", "--disable-extensions",
                    "--disable-sync", "--disable-background-networking", "--disable-component-update", "--disable-default-apps",
                    "--mute-audio", "--hide-scrollbars", "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
                    "--disable-backgrounding-occluded-windows", f"--user-data-dir={prof}", f"--window-size={job['W']},{job['H']}",
                    "--force-device-scale-factor=1", f"http://127.0.0.1:{srv.server_address[1]}/index.html?job={w}"]
        for w in range(len(jobs)):
            prof = tempfile.mkdtemp(prefix="hk9gfx_"); profs.append(prof)
            procs.append(subprocess.Popen(launch(prof, w), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        retries = 0
        while st["done"] < len(jobs) and not st["error"]:
            dead = any(p.poll() is not None for p in procs)
            if dead: time.sleep(0.5)
            if (dead and st["done"] < len(jobs)) or time.time() - st["last"] > 90:
                # a browser crashed or stalled (a busy or sleeping computer): start fresh browsers for what is missing
                missing = [i for j in jobs for i in j["frames"] if i not in st["drawn"] and i not in st["dups"]]
                if not missing or retries >= 2:
                    raise RuntimeError("the graphics browser stopped (tried 3 times); close other heavy apps and run again")
                retries += 1; print(f"graphics: a browser stalled; retrying {len(missing)} frames (attempt {retries + 1})")
                for p in procs:
                    p.terminate()
                    try: p.wait(10)
                    except subprocess.TimeoutExpired: p.kill()
                size = -(-len(missing) // len(jobs)); jobs[:] = [dict(job, frames=missing[j * size:(j + 1) * size]) for j in range(len(jobs))]
                jobs[:] = [j for j in jobs if j["frames"]]; srv.jobs = jobs; st["done"] = 0; st["last"] = time.time(); procs = []
                for w in range(len(jobs)):
                    prof = tempfile.mkdtemp(prefix="hk9gfx_"); profs.append(prof)
                    args = launch(prof, w); procs.append(subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            time.sleep(0.05)
        if st["error"]: raise RuntimeError("graphics page error: " + st["error"])
    finally:
        for p in procs:
            p.terminate()
            try: p.wait(10)
            except subprocess.TimeoutExpired: p.kill()
        srv.shutdown(); srv.server_close()
        for prof in profs: shutil.rmtree(prof, ignore_errors=True)
    for i, src in st["dups"].items():                       # identical frames: copies of the last one drawn
        shutil.copyfile(os.path.join(outdir, f"f_{src:05d}.png"), os.path.join(outdir, f"f_{i:05d}.png"))
    if fill_blanks and "n" in job and not job.get("frames"):
        blank = None
        for i in range(job["n"]):
            if i not in st["drawn"] and i not in st["dups"]:
                blank = blank or _blank_png(round(job["W"] * job.get("scale", 1)), round(job["H"] * job.get("scale", 1)))
                with open(os.path.join(outdir, f"f_{i:05d}.png"), "wb") as f: f.write(blank)
    if not quiet:
        print(f"graphics: {len(st['drawn'])} frames drawn, {len(st['dups'])} repeated, in {time.time() - t0:.1f} s "
              f"({len(jobs)} browser{'s' if len(jobs) > 1 else ''})")
    return len(st["drawn"])


def encode(frames_dir, out, alpha=False, fps=FPS):
    """PNG sequence -> H.264 MP4 (BT.709), or ProRes 4444 .mov with alpha."""
    seq = os.path.join(frames_dir, "f_%05d.png")
    tags = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
    if alpha:
        cmd = ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-alpha_bits", "8", "-qscale:v", "9"]
    else:
        cmd = ["-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx264", "-preset", "slow",
               "-crf", "19", "-maxrate", "14M", "-bufsize", "28M", "-movflags", "+faststart"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", seq] + cmd + tags + [out], check=True)


def _opt(name, default=None):
    a = sys.argv
    return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default


def main():
    a = [x for x in sys.argv[1:]]
    if not a or a[0] not in ("sheet", "scene", "list"): sys.exit(__doc__)
    orient = "horizontal" if "--horizontal" in a else "vertical"; W, H = SIZE[orient]
    if a[0] == "list":
        for k, (b, card) in SCENES.items(): print(f"{k:13} {b:>4} s  {'card (full screen)' if card else 'overlay (on footage)'}")
        return
    if a[0] == "sheet":
        out, at = a[1], float(_opt("--at", "0.62"))
        ids = [k for k in SCENES if not _opt("--only") or k in _opt("--only").split(",")]; ev, times = [], []
        for k, sid in enumerate(ids):
            dur = SCENES[sid][0] if sid != "captions" else 3.0
            ev.append(dict(scene=sid, t0=k * 100.0, dur=dur)); times.append(k * 100.0 + at * dur)
        tmp = tempfile.mkdtemp(prefix="hk9sheet_")
        try:
            render(dict(W=W, H=H, events=ev, frames=list(range(len(ids))), times=times, preview=True), tmp)
            from PIL import Image, ImageDraw
            tw_, th_ = (360, 640) if orient == "vertical" else (640, 360)
            cols = 5 if orient == "vertical" else 4; rows = -(-len(ids) // cols)
            sheet = Image.new("RGB", (cols * (tw_ + 12) + 12, rows * (th_ + 40) + 12), (17, 17, 17)); d = ImageDraw.Draw(sheet)
            for k, sid in enumerate(ids):
                p = os.path.join(tmp, f"f_{k:05d}.png")
                if not os.path.isfile(p): continue
                im = Image.open(p).convert("RGB").resize((tw_, th_)); x, y = 12 + (k % cols) * (tw_ + 12), 12 + (k // cols) * (th_ + 40)
                sheet.paste(im, (x, y)); d.text((x, y + th_ + 8), sid, fill=(220, 220, 220))
            os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True); sheet.save(out, quality=90); print("->", out)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return
    sid, out = a[1], a[2]
    if sid not in SCENES: sys.exit(f"unknown graphic {sid}; see: python gfx.py list")
    dur = float(_opt("--dur", SCENES[sid][0])); params = json.loads(_opt("--params", "{}"))
    alpha = "--alpha" in a; n = round(dur * FPS); tmp = tempfile.mkdtemp(prefix="hk9scene_")
    try:
        render(dict(W=W, H=H, n=n, fps=FPS, events=[dict(scene=sid, t0=0, dur=dur, p=params)], preview=not alpha), tmp)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True); encode(tmp, out, alpha=alpha); print("->", out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
