---
name: hk9edit
description: Edits Highland Canine Training footage (an interview or someone talking to camera, plus action b-roll of the dogs) into a finished branded video with the Highland motion graphics, vertical 9:16, horizontal 16:9 or both. It first asks the format, whether the edit needs a social-media hook (big opening line, captions, fast cuts) or is a regular edit (cold open, logo sting, clean), the length and who picks the answers. It cuts the interviewer out, keeps the strongest lines, covers each with matching action b-roll, removes "uh"/"um", cleans the background noise, adds the logo sting, name tags, quote and steps cards, captions and the end card in the Highland colours, and renders a quick preview for review. Once the person is happy with the cut it asks for a music style, offers the styles that suit this edit, and composes background music to the finished edit (bars land on the cuts, hits on the graphics, quiet under the voice), then renders the final files. Use it whenever someone wants a Highland video, reel, testimonial, referral, student story, trainer interview or social post made from their own footage, or asks to add the Highland graphics, captions or music to an edit, even if they never say "skill" or "hk9edit". Works on Windows and Mac.
---

# HK9 edit: Highland branded video from interview + b-roll footage

You are making the kind of film the HK9 referral clients approved: the person speaks, the viewer watches the dog (or
the work) do exactly what is being described, and the Highland graphics frame it. The cut follows the house style in
`references/style.md` (read it before choosing shots); the graphics are in `references/graphics.md`; the music in
`references/music.md`.

The whole edit lives in one Python "edit file" (copy `assets/edit_template.py`). `scripts/build.py` renders it.
Every revision is cheap: change a number, run `--dry` (seconds), render a `--preview`, check.

Commands below say `python`. On a Mac use `python3`. `S` means this skill's `scripts/` folder.

## 1. First, ask (before touching the footage)

Ask these in one go: with the AskUserQuestion tool when you have it (recommended option first), otherwise as a
short numbered list. Skip any the request already answers.

1. **Format**: "Which format?"
   - Both vertical and horizontal (Recommended): same cut, identical sound
   - Vertical 9:16 only: Reels, TikTok, Shorts
   - Horizontal 16:9 only: YouTube, website, a screen
2. **Edit type**: "Social-media hook or regular edit?"
   - Social hook (Recommended for Reels/TikTok/Shorts): the strongest line as big type over the best action in the
     first 2 s, captions throughout, quick cuts, 30-60 s, logo only at the end
   - Regular edit (Recommended for YouTube/website/referrals): action cold open, logo sting, name tag, cards where
     they help, no captions, 60-105 s
3. **Length**: "How long?"
   - Social: about 45 s (Recommended) / about 30 s / about 60 s
   - Regular: about 90 s (Recommended) / about 60 s / up to 1:45
   (Ask after question 2 when you cannot ask both at once, or offer "Short (30-45 s)", "Medium (about 60 s)",
   "Long (about 90 s)".)
4. **Answers**: "Who picks the lines?"
   - You pick the strongest (Recommended)
   - I'll choose: after transcribing, show the answers as a short numbered list (one line each, with times)

Also needed, usually in the request already: the footage folder (ask in plain words if missing) and the speaker's
name and role for the name tag (ask; never guess a name, rank or agency). Everything else is house style; do not
ask about it. Do NOT ask about music yet: music comes after the cut is approved (section 5).

## 2. Setup (once per computer)

`python S/setup_check.py` checks ffmpeg, Python packages, Whisper and its model, and Edge/Chrome, and draws one test
graphic. If something is missing, tell the user exactly what to install from `README.md` (it has the Windows
commands) instead of improvising. Never install anything without saying so.

Work in a folder next to the footage (e.g. `<footage>/../_edit/`). Never write into or modify the source clips.
Delegate bulk mechanical reading (long transcripts, many contact sheets) to a cheaper sub-agent if you have one,
and keep the judgement calls (which answer, which shot, which graphic) yourself.

## 3. Build the cut (the HK9 way)

1. **Inventory.** `python S/inventory.py FOOTAGE OUT` lists every clip (length, played size, HDR, rotation) and
   writes contact sheets. Look at them; note what each b-roll clip shows and when. Phone clips are often vertical
   (rotation -90): that is fine, the build frames any shape.
2. **Transcript and voices.** `python S/transcribe.py INTERVIEW OUT --words` gives the lines with source times and a
   words file (set `WORDS` to it: captions and the hook use it). `python S/speakers.py INTERVIEW map`, then
   `... runs <Hz>` separates the interviewer from the speaker by pitch and level. Never use the questions.
3. **Choose the lines** (or let the user choose). Regular: who they are (on camera) -> why Highland / this dog ->
   the dog -> the training -> the first real result (the strongest proof line) -> the recommendation, closing on
   camera. Social: the hook line first (the single strongest, most surprising sentence, 2-3 s), then who they are,
   the proof, one useful detail, the close; drop everything else. Put every in/out point in silence: read the
   level (`python S/fillers.py formants CLIP A-B`), never Whisper's word times (they drift 0.2-0.5 s).
4. **Fillers.** `fillers.py scan` / `fillers.py check` (method in its docstring). Real ones go in `CUTS` or move a
   piece edge. A filler cut on camera is hidden by splitting the shot and punching in.
5. **Opening.** Regular: `COLD` = 4-8 s of natural-sound action (the send, the bite, the find) with `hit` on the
   impact; the logo sting follows by itself (`LOGO_STING`, 3 s). Social: the first section is the hook line, and
   `HOOK = dict(lines=[...])` puts it on screen as big type (`*word*` or `*several words*` = emphasis in light blue);
   use the speaker's own words in spoken order so each word lands as it is said.
6. **Match action b-roll to every line**: literal where possible, the subject (usually the dog's head) inside the
   crop for the whole shot, 2-7 s shots (social: 1.2-3 s, more punch-ins and whips), a quick three-shot montage for
   a spoken list, each moment used once. Never set-up moments (harnessing) or frames the subject has left.
7. **Frame every shot.** `FOOTAGE=... python S/frames.py grid OUT.jpg CLIP:START:END:STEP ...` gives source frames
   with a 0.1 grid: write `keys` (cx, cy of the subject). Talking head: `python S/headpos.py INTERVIEW A-B`.
   `fit="contain"` shows a whole clip over a blurred copy of itself (a vertical clip in a 16:9 film, when the
   crop would lose the action).
8. **Natural sound.** `nat()`: a few tight windows (barks, the decoy's shout) at -13/-14 dB under the voice; transcribe
   each window to be sure nobody else talks in it.
9. **Graphics** (`graphics(e)` in the edit file; catalogue and rules in `references/graphics.md`). Automatic: logo
   sting (regular), end card, hook (social), captions (social). Add by hand: a name tag on the first on-camera line
   (both types), a quote card on the strongest proof line (regular, at most one), a steps card when the speaker lists
   steps, a stat card for a number they say, a section title where the story turns. Under a full-screen card put an
   `e.B(...)` black shot. Words on graphics come from the interview or the user: never invent a claim, number or
   name; Highland's own facts (programmes, phone, dates) are in `motion/src/copy.js`.

## 4. Check, preview, review

- `python S/build.py edit.py --dry` prints every shot (time, clip, line), the graphics, the caption chunks and
  warnings. Fix every warning (sync of on-camera shots, cuts landing on a sound, length off target, overlapping
  cards) and re-run until it reads right.
- Captions: read the chunk list against what was said. Fix misheard words with `CAPTION_FIXES = {"dental": "fentanyl"}`
  (a word or phrase -> its replacement). Names and K-9 terms are where Whisper slips.
- `python S/build.py edit.py --preview` renders a quick half-size draft (`<OUTPUT>_<format>_preview.mp4`), no music.
  Pull frames (`python S/frames.py strip OUT.jpg VIDEO t1 t2 ...`) and look: subject in frame in every shot (both
  formats), graphics readable and inside the safe area, captions correct.
- Send the preview to the user and ask for changes. Repeat until they say it is right. Re-render only what changed
  (the build reuses every shot and graphic that did not change).

## 5. Music (only after the user approves the cut)

Ask for the style with AskUserQuestion: offer the 3-4 styles from `python S/music.py styles` that suit THIS edit,
best first, each with one line on why (e.g. police K9 detection: "Driving tactical (Recommended)", "Cinematic pulse";
a student success story: "Uplifting modern (Recommended)", "Warm and gentle"; a social hook: add "Modern groove").
How to choose is in `references/music.md`. Then set `MUSIC_STYLE`, `ENERGY` per section (0-3) and `LIFT` (the proof
section) in the edit file and render the finals: `python S/build.py edit.py` (full size, both formats as chosen).
The music is composed to the cut: the tempo bends a few percent so each section start, card and the end card land
on a downbeat, transitions get whooshes and hits, and it ducks under the voice.

A different style or level later is quick: change `MUSIC_STYLE` (or `MUSIC_UNDER_VOICE`, `MUSIC_ALONE`, `ENERGY`) and
run `python S/build.py edit.py --audio` (sound only, picture untouched, seconds).

## 6. Report

`python S/qa.py <OUTPUT>_vertical.mp4 WORK` prints length, loudness (target -16 LUFS regular, -14 social), the
transcript and filler candidates. Report: the file paths, length against what they asked for, the shot list (time,
what we see, the line), the graphics used, the music style, and what you could not confirm by ear (splices, music
level, any remaining background sound, misheard caption words). Never claim you listened.

## Revisions

- Confirm which file the user means before editing (a screenshot alone does not say which version).
- "Change this shot": find it in the `--dry` timeline, pick an unused action moment that fits the line, measure it.
- "Background noise": `DENOISE` in the edit (method in `references/lessons.md`); never gate the pauses.
- "Make the text bigger / a different colour": the graphics are in `motion/src/scenes.js`; keep the house rules
  (text on a light-blue fill is white; logo transparent, never on a white box).
- Re-render only the versions asked for, under the same names unless told otherwise; sources stay untouched.

## Files

| file | what it is |
|---|---|
| `scripts/build.py` | renders an edit file: voice, denoise, natural sound, music, picture, graphics, captions; `--dry`, `--preview`, `--audio` |
| `scripts/gfx.py` | draws the graphics in headless Edge/Chrome; `sheet` (contact sheet), `scene` (one graphic as its own video), `list` |
| `scripts/music.py` | the music styles and the composer; `styles`, `demo` |
| `scripts/setup_check.py` | checks the computer has everything |
| `scripts/inventory.py`, `transcribe.py`, `speakers.py`, `fillers.py`, `frames.py`, `headpos.py`, `denoise.py`, `qa.py` | the HK9 interview tools |
| `motion/` | the Highland graphics (canvas code, Raleway font, transparent logo) |
| `assets/edit_template.py` | the edit file to copy and fill in |
| `references/style.md`, `graphics.md`, `music.md`, `lessons.md` | the look and sound with numbers, the graphics catalogue, the music guide, what went wrong before |
