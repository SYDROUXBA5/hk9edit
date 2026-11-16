# The house style

Built on the HK9 referral edit the client signed off (a 92 s K-9 handler referral, vertical and horizontal), with
the Highland graphics added. Reproduce its feel; the numbers are starting points that worked, not laws.

## Shape (no voice-over: footage, natural sound, on-screen text, music)

### Social hook edit (Reels, TikTok, Shorts)

| part | length | what happens |
|---|---|---|
| hook | 2-3 s | a short bold line over the best action (the find, the bite, the recall), words landing in rhythm |
| the work | 8-20 s | the training itself, quick cuts (1.5-3 s), captions telling what we see |
| the result | 3-8 s | the strongest moment, held a little longer; the music's lift |
| close | 2-4 s | reward, dog and handler |
| end card | 4 s | over the last shot: logo, LEARN MORE, highlandcanine.com (automatic) |

20-45 s in all. No logo sting at the start.

### Regular edit (YouTube, website)

| part | length | what happens |
|---|---|---|
| cold open | 3-6 s | the biggest moment with its natural sound; the music's impact lands on it |
| logo sting | 3 s | the Highland logo opens straight over the action (automatic; keep footage under it) |
| the work | 15-50 s | parts with a title each ("THE SEARCH"), shots 2-4 s, cards where they help (steps, stat) |
| the result | 5-10 s | the strongest moment |
| close + end card | 3 s + 4 s | reward; the end card plays over the last shot |

30-90 s in all. Captions only if asked.

Cuts fall in steady steps (multiples of 0.5 s) so the music meets them. Interview edits (a real person talking,
only on request) follow references/interview.md and the approved referral's shape: cold open, logo sting, the
speaker's lines over action b-roll, closing on camera.

## Picture

- Every shot is ACTION matched to the line: searching, alerting, biting, trailing, driving forward. Rejected by the
  client: set-up moments (harnessing the dog) and frames where the subject has left (an empty car panel).
- Shots 2-7 s (social: 1.2-3 s), hard cuts. A spoken list gets a three-shot montage (~0.85 s each).
- Camera on every shot, smoothed (~0.18 s gaussian on the path):
  - follow the subject: `keys` at least every 0.5 s while it moves; the dog's head never touches the crop edge
  - slow push-in: zoom 1.0 -> 1.07-1.20 over the shot
  - punch on cuts into action: 0.04-0.08 extra zoom settling in 0.1 s; whip blur ("i") on the 2-3 hardest cuts
    (social: more of both)
- Any clip shape works: 16:9 or vertical phone clips, either format out. A vertical clip in a 16:9 film either crops
  around the subject (`fit="cover"`, the default: about a third of the height shows) or sits whole over a blurred,
  darkened copy of itself (`fit="contain"`).
- Talking head: measure x with headpos.py (people stand off-centre and drift), cy ~0.36, zoom 1.15 -> 1.25 in 9:16;
  pulled back by 0.15 in 16:9 automatically.
- A filler cut on camera: split the shot at the cut and jump to a tighter framing (zoom about 1.38-1.40).
- Colour: phone HDR (HLG, PQ) is converted to standard video with a LUT fitted to Apple's own rendering, so the
  footage looks like it does on the phone and the brand colours are exact. Output is Rec.709 (SDR).

## Sound

| layer | level | notes |
|---|---|---|
| music | leads: the whole mix is brought to -14 LUFS (social) / -16 LUFS (regular), peaks under -1 dBTP | composed to the cut by music.py after the cut is approved; a hit on every cut |
| shots' own sound | about 8 dB under the music (each shot levelled to about -26 dBFS, boost capped at +12 dB) | `SHOT_SOUND` (+3 = louder), per shot `sound=` (None mutes chatter) |
| natural-sound moments | as set in `nat()` | the bark, "Good!", the bite: tight windows |
| transitions | about 8 dB under full scale at the loudest hit | whoosh into cards, impact on the sting, cards and end card, riser into the lift |

Interview edits: voice -16 LUFS regular / -14 social, denoised; music 15 dB under the speech while someone talks,
5 dB more on words, 3 dB under it where nobody speaks (details in references/interview.md).

## Delivery

`<OUTPUT>_vertical.mp4` (1080x1920) and/or `<OUTPUT>_horizontal.mp4` (1920x1080): same cut, identical sound,
30 fps, H.264, Rec.709, AAC 192k. Drafts are `_preview.mp4` (half size); before music the full-size files end in
`_nomusic.mp4`.
