# Interview edits (only when the user asks for one)

A real person filmed talking (a client referral, a handler, a student): their own voice carries the story, cut from
the interview, with action b-roll over it. Same graphics, captions question and music. Never a computer voice.

## Extra questions

Ask with the four usual ones (or right after): who picks the lines ("You pick the strongest (Recommended)" / "I'll
choose from a numbered list"), and the speaker's name and role for the name tag (never guess a name, rank or agency).
Lengths: social 30-60 s, regular 60-105 s.

## Steps

1. **Transcript and voices.** `python S/transcribe.py INTERVIEW OUT --words` (lines with source times + a words file:
   set `WORDS` to it). `python S/speakers.py INTERVIEW map`, then `... runs <Hz>`, separates the interviewer from the
   speaker by pitch and level. Never use the questions.
2. **Choose the lines.** Regular: who they are (on camera) -> why Highland / this dog -> the dog -> the training -> the
   first real result (the strongest line) -> the recommendation, closing on camera. Social: the hook line first (the
   single strongest sentence, 2-3 s), who they are, the proof, one detail, the close. Put every in/out point in
   silence: `python S/fillers.py formants CLIP A-B` (30 ms levels), never Whisper's word times.
3. **Fillers.** `fillers.py scan` / `fillers.py check` (method in its docstring) -> `CUTS`. A filler cut on camera is
   hidden by splitting the shot and punching in (zoom +0.2).
4. **Edit file.** As the template, plus:
   ```python
   INTERVIEW = "IMG_0001"               # the interview clip
   ROOM_TONE = 14.90                    # start of >= 0.6 s where nobody speaks (fills gaps in the voice)
   WORDS = "IMG_0001_words.csv"         # from transcribe.py --words
   DENOISE = dict(gmin_db=-24.0, beta=1.7)
   SECTIONS = [("intro", [("in1", 5.30, 13.55)]), ("proof", [("p1", 128.74, 135.50)]), ...]   # instead of PARTS/LENGTH
   CUTS = [(7.86, 8.28)]                # fillers inside pieces
   CAPTION_FIXES = {"dental": "fentanyl"}   # misheard words in the captions (CAPTIONS = True for subtitles of the speech)
   HOOK = dict(lines=["First traffic stop,", "she found *fentanyl*."])   # social: the hook line's own words, in order
   ```
   Shot end times come from the voice: `e.m(piece, source_t)`, `e.start(piece)`, `e.end(piece)`, `e.nxt(section)`,
   `e.VOICE_END`, `e.PICTURE_END`. An on-camera shot reads the interview at the same source time as the voice
   (`--dry` prints the exact clip_in to fix any drift). Measure the talking head with `python S/headpos.py`.
5. **Graphics.** A name tag on the first on-camera line; a quote card on the strongest proof line (regular, at most
   one, the exact words); a steps card when they list steps (`times` = when each is said).
6. **Captions** (if yes): the speaker's words, aligned to the measured speech; read the chunk list in `--dry` and fix
   misheard words with `CAPTION_FIXES`. Hidden under the hook and full-screen cards.
7. **Sound.** Voice denoised and levelled (-16 LUFS regular, -14 social); natural-sound windows at -13/-14 dB under
   it; the music ducks under the voice (`MUSIC_UNDER_VOICE`, `DUCK`) and rises where nobody speaks (`MUSIC_ALONE`).

Everything else (preview, review, music after approval, `--audio`) is as in SKILL.md.
