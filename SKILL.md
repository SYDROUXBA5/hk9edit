---
name: hk9edit
description: Edits Highland Canine Training dog footage into a finished branded video with the Highland motion graphics, vertical 9:16, horizontal 16:9 or both. No voice-over: the story is told by the action shots, their own natural sound, on-screen text and the Highland graphics, with background music composed to the cuts. It first asks the format, whether the edit needs a social-media hook (big opening line, quick cuts) or is a regular edit (cold open, logo sting), whether captions (short lines of on-screen text) are wanted, and the length. It picks the strongest action moments, frames each on the dog, cuts them in rhythm, adds the logo sting over the action, titles, cards and the end card in the Highland colours, and renders a quick preview for review. Once the person is happy with the cut it asks for a music style, offers the styles that suit this edit, and composes music to the finished edit (bars and hits land on the cuts), then renders the final files. Use it whenever someone wants a Highland video, reel, training montage, student or class video, social post or promo made from their own dog footage, or asks to add the Highland graphics, captions or music to footage, even if they never say "skill" or "hk9edit". Works on Windows and Mac. (Interview edits with a real person talking on camera are available on request.)
---

# HK9 edit: Highland branded video from dog footage

You are making the kind of film the HK9 clients approved, cut the same way: the viewer watches the dog work, in
ACTION shots framed on the dog, with punch-ins on the cuts and a cold open on the biggest moment. There is no
voice-over: the footage, its natural sound, short on-screen text and the Highland graphics carry the story, and the
music is composed to the cut once the cut is approved. Never add a voice-over, a computer voice or narration.

The house style with numbers is in `references/style.md` (read it before choosing shots), the graphics catalogue in
`references/graphics.md`, the music guide in `references/music.md`.

The whole edit lives in one Python "edit file" (copy `assets/edit_template.py`). `scripts/build.py` renders it.
Every revision is cheap: change a number, run `--dry` (seconds), render a `--preview`, check.

Commands below say `python`: on Windows run them with `py` (the Python launcher; a plain `python` can open the
Microsoft Store instead), on a Mac with `python3`. `S` means this skill's `scripts/` folder.

## 1. First, ask (before touching the footage)

Ask these four in one go: with the AskUserQuestion tool when you have it (recommended option first), otherwise as a
short numbered list. Skip any the request already answers.

1. **Format**: "Which format?"
   - Both vertical and horizontal (Recommended): same cut, identical sound
   - Vertical 9:16 only: Reels, TikTok, Shorts
   - Horizontal 16:9 only: YouTube, website, a screen
2. **Edit type**: "Social-media hook or regular edit?"
   - Social hook (Recommended for Reels/TikTok/Shorts): a big bold line over the best action in the first 2 s, quick
     cuts (1.2-3 s), 20-45 s, logo only at the end
   - Regular edit (Recommended for YouTube/website): action cold open, the logo sting over the action, titles and
     cards where they help, 30-90 s
3. **Captions**: "Captions on screen?"
   - Yes (Recommended for social): short lines of text that tell the story ("Nose down, box by box"), with the
     Highland caption style
   - No captions: only the titles and cards
4. **Length**: "How long?"
   - Short, about 20-30 s (Recommended for social)
   - Medium, about 45-60 s (Recommended for regular)
   - Long, about 90 s

Also needed, usually in the request already: the footage folder (ask in plain words if missing), and the facts the
text may state: the dog's name, the programme or class, a result or number they want shown. Never guess a name, a
claim or a number: ask, or leave it out. Highland's own facts (site lines, programmes, phone, start dates) are in
`motion/src/copy.js`. Do NOT ask about music yet: it comes after the cut is approved (section 5).

**Interview edits** (only when the user asks for one: a real person filmed talking, e.g. a client referral): follow
`references/interview.md`. Their voice carries the story and the same graphics and music apply. Still never a
computer voice or narration.

## 2. Setup (once per computer)

`python S/setup_check.py` checks ffmpeg, the Python packages, Whisper (only needed for interview edits) and Edge or
Chrome, and draws one test graphic. If something is missing, tell the user what to install from `README.md` (on
Windows: `install_windows.ps1`) instead of improvising. Never install anything without saying so.

Work in a folder next to the footage (e.g. `<footage>/../_edit/`) or where the user says; the videos land next to
the edit file unless `OUT_DIR` says otherwise. Never write into or modify the source clips.
Delegate bulk mechanical reading (many contact sheets) to a cheaper sub-agent if you have one, and keep the
judgement calls (which moment, which shot, which text) yourself.

## 3. Build the cut

1. **Inventory.** `python S/inventory.py FOOTAGE OUT` lists every clip (length, played size, HDR, rotation) and
   writes contact sheets. Look at them all; write down each ACTION moment (clip, time, what happens): the send, the
   search, the alert, the bite, the find, the recall, the reward. Phone clips are often vertical; the build frames
   any shape.
2. **The story, in parts** (`PARTS = [(name, output start)]`): social: hook -> the work -> the result -> close;
   regular: cold open -> the work -> the result (the strongest moment) -> close. Each part is a few shots on one
   idea. `LENGTH` = seconds of picture before the end card.
3. **Cut in rhythm.** Shot lengths in steady steps (multiples of 0.5 s: social 1.5-3 s, regular 2-4 s), longer on
   the result. The music later bends its tempo so the cuts fall on its beats and adds a hit on every cut.
   The rules from the approved film: ACTION over set-up (never harnessing, never a frame the dog has left), each
   moment used once, the subject inside the crop for the whole shot, a quick three-shot montage for a sequence.
4. **Opening.** Regular: `COLD` = 3-6 s of the biggest moment with its natural sound, `hit` on the impact; the logo
   sting (3 s, transparent, over the action) follows by itself, so keep footage under it. Social:
   `HOOK = dict(lines=[...], dur=2.6)` puts a short bold line over the first shots (`*word*` or `*several words*` =
   emphasis in light blue): a promise or a result ("Day one to *detection-ready*"), true to the footage and the
   user's facts.
5. **Frame every shot.** `FOOTAGE=... python S/frames.py grid OUT.jpg CLIP:START:END:STEP ...` gives the frames as
   they play (vertical clips upright) with a 0.1 grid: write `keys` (cx, cy of the dog). Slow push-ins (`zk`), a punch
   on cuts into action, whip blur on the 2-3 hardest cuts. `hold` (default 0.46) is the screen height where the dog
   is held: lower it (0.38-0.42) when captions would sit on the dog. When both formats are wanted, frame each one:
   a vertical clip fills 9:16 at zoom 1 but is already a 1.78x crop in 16:9, so give the 16:9 its own framing with
   `h=dict(zk=[...], keys=[...], hold=...)` (and `v=dict(...)` for 9:16 only); one render then makes both.
   `fit="contain"` shows a whole clip over a blurred copy of itself (a vertical clip in 16:9 when the crop would lose
   the action).
6. **Sound.** Each shot plays its own natural sound under the music (`SHOT_SOUND`, dB; `sound=None` on a shot mutes
   it, e.g. people chatting). Add tight `nat()` windows for the moments that matter (the bark, "Good!", the bite).
   Listen-free check: `python S/transcribe.py CLIP OUT --range 3.2-5.0 [A-B ...]` runs Whisper on just those windows.
7. **Text and graphics** (`graphics(e)` and `CAPTION_TEXT`; catalogue in `references/graphics.md`):
   - captions (if they said yes): one short line per idea, 2-6 words, while the shot that shows it is on screen,
     `CAPTION_TEXT = [(start, end, "Nose down, box by box.")]`; describe what we see or the user's facts, never a claim
     the footage cannot show
   - a `title` at the start of a part ("THE FIND"), a `steps` card for a sequence, a `stat` card for a number the
     user gives, a `kinetic` statement between parts, a `lower-third` naming the dog or handler (ask the name)
   - full-screen cards hide the footage: put an `e.B(...)` black shot under them and keep footage between cards
   - text height: `CAPTION_Y = {"vertical": 0.72, "horizontal": 0.86}` moves the captions, `HOOK = dict(..., y={...})`
     the hook, when they would cover the dog (fractions of the frame height)

## 4. Check, preview, review

- `python S/build.py edit.py --dry` prints every shot (time, clip, what it shows), the graphics, the captions and
  warnings. Fix every warning and re-run until it reads right.
- `python S/build.py edit.py --preview` renders a quick half-size draft (`<OUTPUT>_<format>_preview.mp4`), no music.
  Pull frames (`python S/frames.py strip OUT.jpg VIDEO t1 t2 ...`) and look: the dog in frame in every shot (both
  formats), text readable and inside the safe area.
- Send the preview to the user and ask for changes. Repeat until they say it is right. Only changed shots and
  graphics are re-rendered.

## 5. Music (only after the user approves the cut)

Ask for the style with AskUserQuestion: offer the 3-4 styles from `python S/music.py styles` that suit THIS edit,
best first, each with one line on why (detection / police K9 / protection: "Driving tactical (Recommended)",
"Cinematic pulse"; students, puppies, success: "Uplifting modern (Recommended)", "Warm and gentle"; social posts:
add "Modern groove"). How to choose is in `references/music.md`. Then set `MUSIC_STYLE`, `ENERGY` per part (0-3) and
`LIFT` (the result) and render the finals: `python S/build.py edit.py` (full size). The music is composed to the cut:
each part, card and the end card starts a bar, the tempo is chosen so the cuts land on its beats, every cut gets a
hit, the logo sting and cards get whooshes and impacts.

A different style or level later takes seconds: change `MUSIC_STYLE` (or `ENERGY`, `SHOT_SOUND`) and run
`python S/build.py edit.py --audio` (sound only, picture untouched).

## 6. Report

`python S/qa.py <OUTPUT>_vertical.mp4 WORK` prints the length and loudness (target -14 LUFS social, -16 regular), and
the build's `music:` line gives the tempo, how many cuts landed on the beat and the music's low/mid balance.
Report: the file paths, the length against what they asked for, the shot list (time, what we see), the text on
screen, the graphics, the music style, and what you could not confirm by ear (music level against the natural
sound, any chatter left in the shots' sound). Never claim you listened.

## Revisions

- Confirm which file the user means before editing (a screenshot alone does not say which version).
- "Change this shot": find it in the `--dry` timeline, pick an unused action moment, measure it, check frames.
- "Bigger text / another colour": the graphics are in `motion/src/scenes.js`; keep the house rules (text on a
  light-blue fill is white; the logo transparent, never on a box).
- Re-render only the versions asked for, under the same names unless told otherwise; sources stay untouched.

## Files

| file | what it is |
|---|---|
| `scripts/build.py` | renders an edit file: picture, graphics, captions, sound, music; `--dry`, `--preview`, `--audio` |
| `scripts/gfx.py` | draws the graphics in headless Edge/Chrome; `sheet` (contact sheet), `scene` (one graphic as a video), `list` |
| `scripts/music.py` | the music styles and the composer; `styles`, `demo` |
| `scripts/setup_check.py` | checks the computer has everything (`install_windows.ps1` sets up Windows) |
| `scripts/inventory.py`, `frames.py`, `transcribe.py`, `qa.py` | clips list and contact sheets, framing grids, transcripts, final checks |
| `scripts/speakers.py`, `fillers.py`, `headpos.py`, `denoise.py` | interview edits only (`references/interview.md`) |
| `motion/` | the Highland graphics (canvas code, font, transparent logo) |
| `assets/edit_template.py` | the edit file to copy and fill in (footage-only; the interview variant is in references/interview.md) |
| `references/` | style, graphics, music, interview edits, lessons |
