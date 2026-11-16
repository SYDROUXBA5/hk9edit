# hk9edit

A Claude Code skill that turns Highland Canine Training footage (someone talking to camera plus action b-roll of the
dogs) into a finished video with the Highland motion graphics, vertical 9:16, horizontal 16:9 or both, then composes
background music to the finished cut.

Ask Claude something like *"Make a Highland video from the footage in C:\Videos\Smith interview"*, or type `/hk9edit`.
Claude asks four quick questions (format, social hook or regular edit, length, who picks the lines), builds the cut,
sends a quick preview, makes your changes, and once you are happy asks which music style you want and renders the
final files.

**Social hook edit:** the strongest line as big type over the best action in the first two seconds, captions all the
way, quick cuts, 30-60 s. **Regular edit:** action cold open, Highland logo sting, name tag, quote card, end card,
no captions, 60-105 s.

## Install on Windows (once)

1. Install Claude Code (desktop app or terminal) from https://claude.com/claude-code and sign in.
2. Open **PowerShell** and run:

   ```powershell
   winget install --id Git.Git -e
   ```

3. Close PowerShell, open it again, then run these two lines:

   ```powershell
   git clone https://github.com/SYDROUXBA5/hk9edit "$env:USERPROFILE\.claude\skills\hk9edit"
   ```

   ```powershell
   powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\skills\hk9edit\install_windows.ps1"
   ```

   The installer adds ffmpeg and Python, the Python packages, Whisper (speech-to-text that runs on your PC; nothing
   is uploaded) and its English model (about 470 MB), then checks everything. Every line should end up OK. If it
   stops, run the same line again after closing and reopening PowerShell; it keeps what is already installed.
4. Restart Claude Code so it picks up the new skill.

The graphics are drawn by Microsoft Edge, which every Windows PC already has (Google Chrome works too). If `winget`
is missing, install "App Installer" from the Microsoft Store first.

## Install on a Mac

```bash
brew install ffmpeg whisper-cpp git python
python3 -m pip install numpy scipy pillow
mkdir -p ~/.whisper-models && curl -L -o ~/.whisper-models/ggml-small.en.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin
git clone https://github.com/SYDROUXBA5/hk9edit ~/.claude/skills/hk9edit
python3 ~/.claude/skills/hk9edit/scripts/setup_check.py
```

Google Chrome or Microsoft Edge must be installed.

## Update

```powershell
git -C "$env:USERPROFILE\.claude\skills\hk9edit" pull
```

## Good to know

- Your footage is only read, never changed. Work files go in a `work_<name>` folder next to the edit file; delete it
  once the video is delivered (it holds the cached shots and graphics, a few GB for a long film).
- A preview of a 1-minute film takes a minute or two; the final full-size render a few minutes per format (longer on
  an older laptop). Changing the music afterwards takes seconds.
- Phone HDR video (iPhone) is converted to standard video so the colours match what the phone shows.
- The music is composed on your computer (no samples, nothing licensed, no account needed).

## What is inside

| folder | contents |
|---|---|
| `SKILL.md` | the instructions Claude follows |
| `scripts/` | the edit engine (Python): build, graphics, music, transcription and checking tools |
| `motion/` | the Highland graphics (canvas code, font, logo) |
| `assets/edit_template.py` | the edit file Claude fills in for each film |
| `references/` | the house style, the graphics catalogue, the music guide, lessons learned |
| `tests/smoke_test.py` | an end-to-end test on made-up footage (also run on Windows by GitHub Actions) |

The Highland Canine Training name, logo and colours belong to Highland Canine Training, LLC and are included only so
the skill can make Highland videos. The font is Raleway (SIL Open Font License, renamed HK9 Sans as the licence
requires; see `motion/fonts/`).
