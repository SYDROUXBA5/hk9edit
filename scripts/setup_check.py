#!/usr/bin/env python3
"""Check that this computer has everything the hk9edit skill needs, and say exactly what to install if not.

Usage:  python setup_check.py          (on a Mac: python3 setup_check.py)
"""
import os, platform, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
for s in (sys.stdout, sys.stderr):
    try: s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
WIN = os.name == "nt"
ok_all = True


def report(ok, what, fix=""):
    global ok_all
    print(("  OK    " if ok else "  MISSING ") + what + ("" if ok or not fix else f"\n          -> {fix}"))
    ok_all &= ok


print(f"hk9edit setup check ({platform.system()} {platform.release()}, Python {platform.python_version()})")

# Python packages
for mod, pip in (("numpy", "numpy"), ("scipy", "scipy"), ("PIL", "pillow")):
    try: __import__(mod); report(True, f"python package {pip}")
    except ImportError: report(False, f"python package {pip}", f"{'py' if WIN else 'python3'} -m pip install {pip}")

# ffmpeg / ffprobe
ff = shutil.which("ffmpeg"); fp = shutil.which("ffprobe")
fix_ff = "winget install --id Gyan.FFmpeg -e   (then close and reopen the terminal)" if WIN else "brew install ffmpeg"
report(bool(ff and fp), "ffmpeg and ffprobe on PATH", fix_ff)
if ff:
    ver = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.splitlines()[0]
    filters = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    encs = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    report(True, ver[:70])
    for f in ("lut3d", "overlay", "noise", "gblur", "colorchannelmixer"):
        report(f" {f} " in filters, f"ffmpeg filter {f}", "install a full ffmpeg build (" + fix_ff + ")")
    report("libx264" in encs, "ffmpeg encoder libx264", "install a full ffmpeg build (" + fix_ff + ")")

# Whisper (speech to text)
sys.path.insert(0, HERE)
from common import WHISPER_CLI as cli, WHISPER_MODEL as model
report(bool(shutil.which(cli) or os.path.isfile(cli)), f"whisper-cli ({cli})",
       "run install_windows.ps1 (README.md), or set WHISPER_CLI to whisper-cli.exe" if WIN else "brew install whisper-cpp")
report(os.path.isfile(model), f"Whisper model {model}",
       "download https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin into ~/.whisper-models"
       + (" (install_windows.ps1 does it)" if WIN else ""))

# Browser + one test graphic
sys.path.insert(0, HERE)
try:
    import gfx
    exe = gfx.find_browser(); report(True, f"browser {exe}")
    tmp = tempfile.mkdtemp(prefix="hk9check_")
    try:
        n = gfx.render(dict(W=1080, H=1920, n=4, fps=30, events=[dict(scene="lower-third", t0=0, dur=4, p=dict(name="Setup Check"))]),
                       tmp, quiet=True)
        report(n > 0, "graphics drawn by the browser (test name tag)")
    except Exception as e:
        report(False, "graphics drawn by the browser", f"{e}  (set HK9_BROWSER to chrome.exe or msedge.exe)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
except SystemExit as e:
    report(False, "Chrome or Edge", str(e))

print("\nAll set." if ok_all else "\nInstall what is MISSING (README.md has every step), then run this check again.")
print(f"Run the skill's scripts with: {'py' if WIN else 'python3'} <skill>/scripts/<script>.py")
sys.exit(0 if ok_all else 1)
