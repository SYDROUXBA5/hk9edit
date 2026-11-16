# The house style

Built on the HK9 referral edit the client signed off (a 92 s K-9 handler referral, vertical and horizontal), with
the Highland graphics added. Reproduce its feel; the numbers are starting points that worked, not laws.

## Shape

### Regular edit (YouTube, website, referrals)

| part | length | what happens |
|---|---|---|
| cold open | 4-8 s | natural sound only: the warning, "Go!", the dog running, the bite or the find; the music's impact lands on it |
| logo sting | 3 s | the Highland logo opens on the navy field (automatic) |
| intro, on camera | ~3.5 s | name and role, with the name tag |
| body | ~60-70 s | one action shot per line; sections: why Highland / this dog, the dog, the training, the first real result |
| close, on camera | ~5 s | the recommendation's last lines, to camera |
| end card | 4 s | logo, LEARN MORE, highlandcanine.com, phone and handle (automatic) |

Total 60-105 s plus the end card. A quote card on the strongest proof line, a steps card when they list steps.
No captions (unless the user asks).

### Social hook edit (Reels, TikTok, Shorts)

| part | length | what happens |
|---|---|---|
| hook | 2-3 s | the single strongest sentence, its own voice, as big type over the best action shot; words land as spoken |
| story | 25-50 s | who they are (name tag), the proof, one useful detail, the close; quick cuts |
| end card | 4 s | as above; loops cleanly |

Captions throughout (not over the hook or full-screen cards). 30-60 s in all. No logo sting at the start.

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
| voice | -16 LUFS regular, -14 social; peaks under -1.5 dBFS | denoised (about -17 dB on the background, steady, no gating), 80 Hz high-pass, 20 ms crossfades at every splice, room tone in every gap |
| music | 15 dB under the speech level while someone talks, 5 dB more on words, 3 dB under it where nobody speaks (logo sting, cards, end card) and about 9 dB under it below the cold open | composed to the cut by music.py, after the cut is approved |
| transitions | hits about 9 dB over the speech RMS | whoosh into cards, impact on the sting, cards and end card, riser into the lift |
| natural sound | cold open at 0 dB; under the body at -13/-14 dB | tight windows only (barks, the decoy's shout); transcribed to be sure no one else is talking |

The voice is always on top: about 18 dB over the music while someone speaks (median), worst 5% about 5-6 dB.

## Delivery

`<OUTPUT>_vertical.mp4` (1080x1920) and/or `<OUTPUT>_horizontal.mp4` (1920x1080): same cut, identical sound,
30 fps, H.264, Rec.709, AAC 192k. Drafts are `_preview.mp4` (half size); before music the full-size files end in
`_nomusic.mp4`.
