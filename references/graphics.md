# The Highland graphics

All graphics are code in `motion/src/scenes.js`, drawn for 9:16 or 16:9 by headless Edge/Chrome. See them all:
`python scripts/gfx.py sheet sheet.jpg` (add `--horizontal`). One on its own as a video:
`python scripts/gfx.py scene quote out.mp4 --params "{\"text\": \"...\"}"` (`--alpha` for a transparent .mov).

## House rules (from the client)

- Colours from highlandcanine.com: navy `#00102e` (fields), slate `#233452`, sky `#16a5e2` (accents, boxes), deep blue
  `#0480b7`; amber `#f4ab12` from the logo, on one element per graphic only.
- Text on a sky (light-blue) fill is always WHITE: name-tag role strip, programme highlight, LEARN MORE button, AFTER
  tag, caption word box.
- The logo is transparent with white lettering. The logo sting and the end card draw straight over the footage (no
  navy field, no box): soft shadows and a faint dark falloff keep them readable. Never on a white box.
- No paw prints, bones, cartoon dogs or other literal dog props.
- Type: Raleway (lining figures). Motion: "mark, then reward": a move snaps to a hard stop, holds 4 frames while a
  white dash fires on the left rail, then the next element eases in.
- Words: from the interview (quotes are the speaker's exact words) or from the user. Highland's own facts (site
  lines, programmes, phone, start dates) are in `motion/src/copy.js` with their source. Never invent a claim, number,
  name or rank; ask.

## Catalogue

Use as `e.G("<id>", start, seconds, **words)` in `graphics(e)`. A card covers the whole frame (put `e.B(...)` black
under it); an overlay sits on the footage. A card shorter than its base length plays its animation faster.

| id | kind | base | words (keyword arguments) | when |
|---|---|---|---|---|
| `logo-sting` | overlay | 3 s | `tagline=[...]` (no website line: the end card has it) | automatic after the cold open (regular); keep footage under it |
| `end-card` | overlay | 4 s | `cta`, `url` (set via `END_CARD_WORDS`; no phone or handle unless `phone=` / `handle=` are given) | automatic at the end, over the last shot (runs to `e.TOTAL`) |
| `lower-third` | overlay | 4 s | `name`, `role` | the first on-camera line; 4-5 s |
| `title` | overlay | 2.5 s | `eyebrow`, `text` | where the story turns ("HANDLER SCHOOL"); top left |
| `quote` | card | 7 s | `text`, `highlight` (last N words in sky), `by`, `src` | the strongest proof line, while it is spoken; at most one |
| `steps` | card | 10 s | `eyebrow`, `title=[...]`, `steps=[2-4 lines]`, `times=[s from card start, one per step]` | they list steps; `times` makes each land as said |
| `stat` | card | 6 s | `value` (whole number), `suffix`, `big`, `sub`, `note` | a number they say (or a Highland fact from copy.js) |
| `kinetic` | card | 6 s | `words=[{s, key, under}]` (key = sky, under = amber underline) | a short statement between sections |
| `programs` | card | 10 s | `eyebrow`, `title=[...]`, `list=[up to 8]` | promos; defaults to Highland's service lines |
| `dates` | card | 6 s | `eyebrow`, `title=[...]`, `label`, `months=[0-11]`, `place` | course start dates (from copy.js / the user) |
| `before-after` | card | 8 s | `title`, `a`, `b`; picture: `e.SPLIT(...)` under it | behaviour change shown side by side / top and bottom |
| `hook` | overlay | auto | `HOOK = dict(lines=[...], dur=2.6)` in the edit | social edits, over the first shots |
| `captions` | overlay | auto | `CAPTIONS` + `CAPTION_TEXT` lines (footage-only) or the speech (`CAPTION_FIXES`, interview) | when they said yes to captions |

Placement notes:
- 9:16 keeps text clear of the top 250 px and bottom 400 px (app buttons). Captions sit above the name tag.
- In 16:9 the captions lift above a name tag while it is on screen.
- Captions are hidden under the hook and full-screen cards (the card carries the words).
- Two cards back to back read as a slideshow: keep footage between cards.
