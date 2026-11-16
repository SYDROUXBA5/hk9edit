"""EDIT FILE: the whole film as data (footage-only: no voice-over). Copy this next to the footage, fill it in, then:
    python <skill>/scripts/build.py edit.py --dry        # timeline, graphics, captions, warnings (seconds; after every change)
    python <skill>/scripts/build.py edit.py --preview    # quick half-size draft to review (no music yet)
    python <skill>/scripts/build.py edit.py              # full-size finals (once the cut is approved and MUSIC_STYLE is set)
    python <skill>/scripts/build.py edit.py --audio      # sound only (a new MUSIC_STYLE or level), picture kept

Times are in seconds: "source" times are positions inside a clip, "output" times are positions in the film.
Every number below is a placeholder showing the shape; replace them all. On a Mac use python3.
An interview edit (a real person talking) uses SECTIONS instead of PARTS/LENGTH: see references/interview.md.
"""

# ---------------------------------------------------------------- FILES
FOOTAGE = r"C:\path\to\footage"       # folder holding the clips (only read, never written)
OUT_DIR = FOOTAGE                     # where the videos go
OUTPUT = "Highland_Topic_Date"        # -> Highland_Topic_Date_vertical.mp4 / _horizontal.mp4
NOROT = ()                            # clips with a wrong rotation flag (upright only with -noautorotate), e.g. ("0012",)

# ---------------------------------------------------------------- THE USER'S ANSWERS (asked before editing)
FORMATS = ("vertical", "horizontal")  # or ("vertical",) or ("horizontal",)
EDIT_TYPE = "social"                  # "social": hook + quick cuts | "regular": cold open + logo sting
TARGET_LENGTH = 30                    # seconds they asked for (with the 4 s end card); --dry warns if it is 10% off
MUSIC_STYLE = None                    # stays None until the cut is approved; then "tactical" / "cinematic" / "uplifting" / "warm" / "groove"

# ---------------------------------------------------------------- STORY AND TIMING
LENGTH = 26.0                         # seconds of picture before the end card
PARTS = [("hook", 0.0), ("work", 2.6), ("result", 14.0), ("close", 21.0)]   # each part starts a bar of the music
ENERGY = {"hook": 3, "work": 2, "result": 3, "close": 2}                   # music per part: 0 pad only ... 3 full
LIFT = "result"                       # the part that gets the full arrangement and a crash
HOOK = dict(lines=["Day one to", "*detection-ready*"], dur=2.6)   # social: a bold line over the first shots; None = none
# COLD = dict(clip="IMG_0002", cin=5.3, cout=9.8, hit=8.6)        # regular: natural-sound cold open (hit = the impact)
# LOGO_STING = True                   # default True for regular (3 s, transparent, over the footage), False for social
# END_CARD = True                     # the Highland end card (4 s); END_CARD_WORDS = dict(cta="APPLY NOW") changes its words

# ---------------------------------------------------------------- TEXT ON SCREEN
CAPTIONS = True                       # the user's answer; False = titles and cards only
CAPTION_TEXT = [                      # (output start, end, short line): what we see or the user's facts, never invented
    (3.0, 6.0, "Odor imprint: the first search."),
    (14.2, 17.4, "Her first independent find."),
]

# ---------------------------------------------------------------- SOUND
SHOT_SOUND = 0.0                      # each shot's own sound under the music, dB (None = silent); per shot: S(..., sound=-6)


# ---------------------------------------------------------------- PICTURE
def shots(e):
    """The shots in order; each starts where the last ended (output times in seconds).
      e.S(label, clip, clip_in, OUTPUT end, keys, zk=, punch=, whip=, line=, fit=, sound=)
      e.B(label, OUTPUT end)       black, under a full-screen card (quote, steps, stat ...) and the end card
      e.SPLIT(label, (clip, in, keys), (clip, in, keys), OUTPUT end)   the two windows of a before-after card
    Useful times: e.SEC[part], e.nxt(part) (start of the next part), e.STING (start, end), e.PICTURE_END, e.TOTAL.
      keys  [(clip_t, cx, cy)] where the DOG is in the clip (0-1); the crop follows it smoothly
      zk    [(clip_t, zoom)] slow push-ins 1.0 -> 1.10-1.20
      punch extra zoom that settles in 0.1 s after the cut (0.04-0.08); whip "i" = motion blur on the first frames
      fit   "cover" (default) or "contain" (the whole clip over a blurred copy, e.g. a vertical clip in 16:9)
    Cut in steady steps (multiples of 0.5 s) so the music's beats meet the cuts."""
    return [
        e.S("H1  the find, hook", "IMG_0002", 8.1, 2.6, [(8.1, .50, .60)], zk=[(8.1, 1.10), (10.7, 1.20)], punch=.06),
        e.S("W1  nose down on the boxes", "IMG_0003", 1.5, 4.6, [(1.5, .48, .62)], punch=.05, whip="i"),
        # ... one action shot per beat of the story ...
        e.S("R1  the alert", "IMG_0005", 3.0, e.SEC["result"] + 2.5, [(3.0, .55, .58)], punch=.06),
        e.S("C1  reward, dog and handler", "IMG_0007", 11.2, e.PICTURE_END, [(11.2, .47, .55)], zk=[(11.2, 1.0), (16.2, 1.08)]),
        e.B("END end card", e.TOTAL),
    ]


# ---------------------------------------------------------------- GRAPHICS (catalogue: references/graphics.md)
def graphics(e):
    """e.G(scene, OUTPUT start, seconds, **words). The logo sting, hook, captions and end card are added by themselves."""
    return [
        e.G("title", e.SEC["result"] + 0.05, 2.4, eyebrow="Detection", text="The find"),
    ]


# ---------------------------------------------------------------- NATURAL SOUND (moments to lift above the rest)
def nat(e, SH):
    """(clip, source_in, source_out, OUTPUT time, gain dB). SH["R1"]["t0"] = output start of shot R1.
    Tight windows around the moment (the bark, "Good!"); transcribe one if people may be talking in it."""
    return [
        # ("IMG_0005", 3.4, 4.1, SH["R1"]["t0"] + 0.4, -3.0),
    ]
