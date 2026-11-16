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
2. Open **PowerShell** and run these one at a time:

   ```powershell
   winget install --id Gyan.FFmpeg -e
   winget install --id Python.Python.3.12 -e
   winget install --id Git.Git -e
   ```

   Close PowerShell, open it again, then:

   ```powershell
   py -m pip install numpy scipy pillow
   ```

3. Speech-to-text (Whisper, runs on your PC; nothing is uploaded):
   - Download **whisper-bin-x64.zip** from https://github.com/ggml-org/whisper.cpp/releases (the latest release,
     under "Assets") and unzip it to `C:\whisper`.
   - Tell the skill where it is, and download the English model (about 470 MB):

   ```powershell
   $exe = (Get-ChildItem C:\whisper -Recurse -Filter whisper-cli.exe | Select-Object -First 1).FullName
   [Environment]::SetEnvironmentVariable("WHISPER_CLI", $exe, "User")
   New-Item -ItemType Directory -Force "$env:USERPROFILE\.whisper-models" | Out-Null
   Invoke-WebRequest https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin -OutFile "$env:USERPROFILE\.whisper-models\ggml-small.en.bin"
   ```

4. The skill itself:

   ```powershell
   git clone https://github.com/SYDROUXBA5/hk9edit "$env:USERPROFILE\.claude\skills\hk9edit"
   ```

5. Close and reopen PowerShell, then check everything:

   ```powershell
   py "$env:USERPROFILE\.claude\skills\hk9edit\scripts\setup_check.py"
   ```

   Every line should say OK. The graphics are drawn by Microsoft Edge, which every Windows PC already has
   (Google Chrome works too).

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
