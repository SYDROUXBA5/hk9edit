# Music

Composed in `scripts/music.py` from the finished cut: synthesised (no samples, nothing licensed, works offline), so
it can be written to the picture instead of laid under it. Ask for it only after the user approves the cut.

## The styles

`python scripts/music.py styles` prints them. To hear one alone: `python scripts/music.py demo uplifting demo.wav`.

| id | name | tempo | suits |
|---|---|---|---|
| `tactical` | Driving tactical | 124 | police K9, detection, protection, bite work: dark, tense, 16th-note bass pulse, taiko drums |
| `cinematic` | Cinematic pulse | 100 | serious testimonials, hard-won results: string ostinato, big drums, weight |
| `uplifting` | Uplifting modern | 116 | students, success stories, family dogs, puppy progress: bright plucks, light four-on-the-floor |
| `warm` | Warm and gentle | 84 | service dogs, behaviour rehab, emotional stories: electric piano, soft pads, no big drums |
| `groove` | Modern groove | 90 | social posts, day-in-the-life, lighter moments: laid-back hip-hop drums, mellow keys |

Offer 3-4 that fit THIS edit, best first, one line each on why. Typical picks:
- police K9 / detection / apprehension: tactical (rec.), cinematic, groove (social)
- handler or student testimonial, school: uplifting (rec.), cinematic, warm
- service dog, rehab, family: warm (rec.), uplifting, cinematic
- social hook of any kind: add groove; tactical or uplifting usually lead

## How it fits the cut

- **Grid.** Anchors: the cold open's hit, the logo sting, the hook's cut, every section start, every card, the end
  card. The tempo stays within 9% of the style's own, bent between anchors so each one starts a bar. Anchors too
  close to fit are dropped (the end card, sting and hook win).
- **Arrangement.** `ENERGY` per section, 0 = pad only, 1 = + melody/bass, 2 = + drums, 3 = everything. `LIFT` names
  the section that gets the full arrangement, a riser and a crash (usually the proof). The music enters with the
  logo sting; a social hook plays at energy 2-3. The last chord rings out under the end card and fades at the end.
- **Transitions** (separate layer): whoosh into each card and the sting, impact on the sting, each card and the end
  card, riser into the lift and into the hook's cut, a soft tick when a name tag or title lands.
- **Levels** (build.py): under the voice `MUSIC_UNDER_VOICE` (-15 dB re the speech level), a further `DUCK` (5 dB) on
  words, `MUSIC_ALONE` (-3 dB) where nobody speaks; the cold open keeps the music lower so the natural sound leads.

## Revisions

| they say | change |
|---|---|
| "another style" | `MUSIC_STYLE`, then `--audio` |
| "music louder / quieter" | `MUSIC_UNDER_VOICE` (+/-3 dB a step) and/or `MUSIC_ALONE` |
| "too busy under him" | lower that section's `ENERGY` |
| "more punch at the result" | `LIFT` on that section, `ENERGY` 3 |
| "a different take of the same style" | `MUSIC_SEED = 2` (changes the random parts: noise, percussion detail) |

Every change: `python scripts/build.py edit.py --audio` (seconds; the picture is kept).

What was measured (I cannot listen): bus balance (low 60-250 Hz and mid 250-2000 Hz within a few dB, highs about
-16 dB), loudness per part, voice-over-music ratio. Say so when reporting.
