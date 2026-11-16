# Lessons from the first film

Read the section that matches the problem in front of you.

## Voice and the interviewer
- The interviewer held the phone, so she was about 10 dB louder than him and 180-290 Hz against his ~105 Hz. A
  per-frame autocorrelation pitch + level pass (`speakers.py`) finds her exactly. Short high blips inside his phrases
  were his own vowels, a beep or birds; check those with Whisper on the isolated snippet before cutting.
- Place cuts in measured silence. The build prints the level at every piece edge; above about -40 dB means the cut
  lands on a sound. A cut once left half a word audible, and a piece once started on his "uh".
- Whisper word times are 0.2-0.5 s off around pauses, and `-dtw` with a prompt garbled an edited track. Use Whisper
  for words, the level envelope for times. To learn what one short sound is, transcribe just that snippet padded
  with silence: the most reliable test found.

## Fillers
- Whisper drops fillers unless prompted with a filler-heavy prompt; prompted, it also invents them in pauses and at
  splices and mistimes them. Treat its list as candidates, verify each in the source (`fillers.py check`).
- "I'm" and "um" can look alike: in "um" F1 drops straight from ~750 to ~250 (nasal) with F2 flat near 1200; in
  "I'm" F2 rises toward 1800-2000 first. If unsure, cutting it is usually harmless to the sense; Whisper the joined
  phrase to be sure no needed word went with it (a short "the" right after an "uh" nearly went with it).
- On camera a cut shows as a jump: split the shot and punch in at the cut.

## Background noise
- Phone-mic outdoor interview: ambience around -45 dBFS plus a hum line. ffmpeg `afftdn` barely touched it.
- A first fix (notch + afftdn + `agate` expander) sounded WORSE to the client: the gate cut noise 9 dB in the pauses
  but only 0.4 dB under speech, so the background pumped in and out. A pause-only noise metric hid this. Always
  measure the noise under speech as well as in the pauses.
- What works (`denoise.py`): MMSE log-spectral amplitude (Ephraim-Malah) with a decision-directed a-priori SNR, the
  noise profile learned from the interview's own speech-free stretches, a gain floor and no gating, so the
  background drops by the same amount everywhere. gmin -18 dB gives about -14 dB with speech and consonants intact;
  the build uses -24 dB / beta 1.7 (about -17 dB) because the music covers side effects. Deeper gains little: what
  remains is moving sound (birds, rustle). The next step beyond that is an AI voice isolator (ffmpeg `arnndn` with
  an RNNoise model, or an external service): ask the user before downloading or uploading anything.

## Picture
- Measure, never assume: a centred crop put the talking head visibly off-centre, the first thing the client
  noticed. Use `headpos.py` (skin-tone centroid; sunlight skewed it ~0.025 toward the lit side) and check a frame.
- Read b-roll keys off gridded frames, then check frames of the RENDER: with a handheld camera, keys read off the
  source were up to 300 px off in places, and a crop once panned onto an empty door after the dog had left it.
- iPhone clips re-exported with a wrong rotation flag play sideways; read them with `-noautorotate` (`NOROT`).
- 16:9 needs less zoom on the talking head than 9:16: the same push-in cut the top of his head.
- In HLG footage, white graphics/text belong at ~86% (RGB 219) or they glare; this style has none, but keep it in
  mind if a user asks for text.

## Natural sound
- B-roll audio is full of other people: a trainer's comment, praise at the bite, someone talking right after.
  Cut windows tight around the event and transcribe each. A shout or bark from another take of the same scene is
  fine when the clip's own sound is unusable.

## Working with the client
- Confirm which version a note is about before editing; once a fix went into the wrong version.
- They prefer action b-roll over set-up moments, and a clean film over captions and graphics.
- Report what only an ear can judge, plainly, every time.

## Graphics, captions, music (hk9edit)

- Whisper's word times are not caption times: it bunches the first words of a sentence onto one instant and drifts
  0.2-0.5 s. build.py takes the words from Whisper and the timing from the audio: each word goes, in order, to the
  measured speech stretch nearest its Whisper time (a move to the next stretch costs extra unless the previous word
  ends a phrase), and the words of a stretch are spread over it by syllables. Caption chunks are 1-3 words, split by
  a small optimiser (no lone words, no chunk ending on "a"/"the"/"her" when avoidable).
- Headless Chrome keeps Blob uploads in a capped store: after about 280 full-frame PNG Blobs every upload failed with
  "Failed to fetch". Frames go up as data-URL text (garbage-collected) over one keep-alive connection, with retries.
- Film grain baked into PNG frames made every card frame 4.4 MB (1.9 GB per format for 40 s). Grain is now ffmpeg's
  `noise` filter over the card intervals in the last pass; frames are ~0.6 MB and draw 2x faster.
- The HDR LUT is the slow step (~28 ms a frame). Shots render in parallel, each to its own near-lossless file, and are
  cached by recipe, so a revision only re-renders the shots that changed; `--preview` renders half size (a 40 s film
  in both formats: about 1 min; full size about 2-4 min on an Apple-silicon Mac).
- Windows: Python's web server can serve .js as text/plain (registry MIME map), which stops ES modules loading, so
  gfx.py sets the types itself; consoles default to cp1252, so every script prints UTF-8 explicitly; filtergraph
  arguments never contain a drive-letter path (the LUT is read relative to the work folder).
- Music bus balance, measured before release: the pure sub-sine bass sat 10-13 dB over every other layer and would
  vanish on phone speakers; it now carries upper harmonics and sits about 10 dB lower, pads are high-passed at 110 Hz,
  hats/shakers lifted. Check with the band split in references/music.md after changing a style.
