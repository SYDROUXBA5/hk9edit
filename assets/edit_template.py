"""EDIT FILE: the whole film as data. Copy this next to the footage (or anywhere), fill it in, then:
    python <skill>/scripts/build.py edit.py --dry        # timeline, graphics, captions, warnings (seconds; after every change)
    python <skill>/scripts/build.py edit.py --preview    # quick half-size draft to review (no music yet)
    python <skill>/scripts/build.py edit.py              # full-size finals (once the cut is approved and MUSIC_STYLE is set)
    python <skill>/scripts/build.py edit.py --audio      # sound only (a new MUSIC_STYLE or level), picture kept

Times are in seconds. "Source" times are positions inside a clip; "output" times are positions in the film.
Every number below is a placeholder showing the shape; replace all of them with measured values.
On a Mac use python3.
"""

# ---------------------------------------------------------------- FILES
FOOTAGE = r"C:\path\to\footage"       # folder holding the interview and the b-roll (only read, never written)
OUT_DIR = FOOTAGE                     # where the videos go
OUTPUT = "Highland_Lastname_Topic"    # -> Highland_Lastname_Topic_vertical.mp4 / _horizontal.mp4
INTERVIEW = "IMG_0001"                # the interview clip (file name, stem, or a unique tail such as "0001")
ROOM_TONE = 14.90                     # start of >= 0.6 s in the interview where nobody speaks (fills gaps in the voice)
WORDS = "IMG_0001_words.csv"          # from transcribe.py --words (captions and the hook use it); relative to this file
NOROT = ()                            # clips with a wrong rotation flag (upright only with -noautorotate), e.g. ("0012",)

# ---------------------------------------------------------------- THE USER'S ANSWERS (asked before editing)
FORMATS = ("vertical", "horizontal")  # or ("vertical",) or ("horizontal",)
EDIT_TYPE = "regular"                 # "social": hook + captions + quick cuts | "regular": cold open + logo sting, no captions
TARGET_LENGTH = 90                    # seconds they asked for; --dry warns if it is 10% off
MUSIC_STYLE = None                    # stays None until the cut is approved; then "tactical" / "cinematic" / "uplifting" / "warm" / "groove"

# ---------------------------------------------------------------- OPENING AND ENDING
# Regular: a natural-sound cold open (hit = source time of the impact), then the logo sting (3 s) by itself.
COLD = dict(clip="IMG_0002", cin=5.35, cout=12.45, hit=11.25)    # None = no cold open
# LOGO_STING = True                   # default True for regular, False for social
# Social: the first section is the hook line, shown as big type. *word* or *several words* = emphasis (light blue).
HOOK = None                           # e.g. dict(lines=["First traffic stop,", "she found *fentanyl*."])
# CAPTIONS = True                     # default True for social, False for regular
CAPTION_FIXES = {}                    # misheard words: {"dental": "fentanyl", "k nine": "K-9"}
# END_CARD = True                     # the Highland end card (4 s); END_CARD_WORDS = dict(cta="APPLY NOW") to change its words

# ---------------------------------------------------------------- SOUND
DENOISE = dict(gmin_db=-24.0, beta=1.7)   # background reduction on the interview (~-17 dB); see references/lessons.md
ENERGY = {"intro": 1, "why": 2, "dog": 2, "proof": 3, "rec": 1}   # music per section: 0 pad only ... 3 full
LIFT = "proof"                        # the section that gets the full arrangement and a crash
# MUSIC_UNDER_VOICE = -15.0  MUSIC_ALONE = -3.0  DUCK = 5.0     # music level re the speech (dB), if they ask louder/quieter

# ---------------------------------------------------------------- VOICE: (section, [(piece, source_in, source_out), ...])
# Each piece is one stretch of the interview. Pieces in a section play back to back (20 ms crossfades);
# ("gap", s) inserts silence-with-room-tone. Put every in/out point in measured silence. Never include the interviewer.
SECTIONS = [
    ("intro", [("in1", 5.30, 13.55)]),                                   # name, role, what they do (on camera)
    ("why",   [("w1", 19.61, 23.80), ("w2", 25.27, 27.06)]),             # why Highland / this dog
    ("dog",   [("d1", 144.60, 146.46), ("d2", 147.90, 152.27)]),         # the dog
    ("proof", [("p1", 128.74, 135.50)]),                                 # first real result: the strongest line
    ("rec",   [("r1", 194.00, 201.72)]),                                 # recommendation, on camera
]
CUTS = [                                                                 # fillers inside pieces: (source_in, source_out)
    (7.86, 8.28),
]


# ---------------------------------------------------------------- PICTURE
def shots(e):
    """The shots in order; each starts where the last ended.
      e.S(label, clip, clip_in, OUTPUT end, keys, zk=, punch=, whip=, line=, fit=)
      e.B(label, OUTPUT end)       black, under a full-screen graphic (logo sting, quote card, end card ...)
      e.SPLIT(label, (clip, in, keys), (clip, in, keys), OUTPUT end)   the two windows of a before-after card
    OUTPUT times come from the voice: e.m(piece, source_t), e.start(piece), e.end(piece), e.nxt(section) (start of the
    next section), e.SEC[section], e.STING (start, end), e.VOICE_END, e.PICTURE_END (end card starts), e.TOTAL.
      keys  [(clip_t, cx, cy)] where the SUBJECT is in the clip (0-1); the crop follows it smoothly
      zk    [(clip_t, zoom)] slow push-ins 1.0 -> 1.10-1.20; talking head 1.15 -> 1.25
      punch extra zoom that settles in 0.1 s after the cut (0.04-0.08); whip "i" = motion blur on the first frames
      fit   "cover" (default) or "contain" (the whole clip over a blurred copy, e.g. a vertical clip in 16:9)
    An on-camera shot reads the interview at the same source time as the voice (--dry gives the exact clip_in)."""
    return [
        e.S("COLD  the send, the bite", "IMG_0002", 5.35, e.STING[0],
            [(5.35, .20, .65), (8.4, .44, .60), (10.9, .62, .58)], zk=[(5.35, 1.05), (10.9, 1.18)], line="[natural sound]"),
        e.B("STING logo sting", e.STING[1]),
        e.S("CAM1  on camera", INTERVIEW, 5.30 - 0.35, e.m("in1", 7.86),
            [(5.3, .45, .36)], zk=[(5.3, 1.15), (7.86, 1.19)], punch=.05, line="Name, role."),
        # ... one action shot per line ...
        e.B("QUOTE quote card", e.end("p1") + 0.4, line="the proof line"),
        e.S("CAM2  on camera", INTERVIEW, 194.00, e.VOICE_END, [(194.0, .40, .36)], zk=[(194.0, 1.15), (201.7, 1.26)]),
        e.S("LAST  the dog", "IMG_0004", 11.20, e.PICTURE_END, [(11.2, .47, .45)]),
        e.B("END   end card", e.TOTAL),
    ]


# ---------------------------------------------------------------- GRAPHICS (catalogue: references/graphics.md)
def graphics(e):
    """e.G(scene, OUTPUT start, seconds, **words). The logo sting, hook, captions and end card are added by themselves."""
    return [
        e.G("lower-third", e.start("in1") + 0.3, 4.5, name="First Last", role="Title, Agency"),     # ask the user for both
        e.G("quote", e.m("p1", 131.0), e.end("p1") + 0.4 - e.m("p1", 131.0),
            text="Exact words from the interview.", highlight=3, by="First Last", src="Agency"),
    ]


# ---------------------------------------------------------------- NATURAL SOUND
def nat(e, SH):
    """(clip, source_in, source_out, OUTPUT time, gain dB). SH["B9"]["t0"] = output start of shot B9.
    Keep windows tight around the event and transcribe each one: b-roll audio is full of other people talking."""
    return [
        ("IMG_0002", 5.35, 12.45, 0.0, 0.0),                     # the cold open's own sound
    ]
