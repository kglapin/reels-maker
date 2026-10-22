# Editorial motion design — restrained, hierarchy-first

The primary goal is comprehension, not spectacle. Enter each element only if
there is a communicative reason. Treat FFmpeg `xfade` (shot transitions) and
`motion` (in-shot element animation) as independent timeline systems.

## Preferred patterns

1. **Cut as default:** every shot change is a cut unless its creative brief
   explicitly calls for a transition. Keep meaningful cuts locked to speech,
   action or music; do not randomly cycle through presets.
2. **Typography hierarchy:** sequence an optional kicker, then the headline,
   then supporting detail. Make the headline visually dominant. Let each
   element settle into a fully static, readable state.
3. **Modest stagger:** 2–3 frames between elements at 25–30 FPS is typically
   enough for an intentional cascade; adjust for the actual scene duration.
4. **Natural deceleration:** ease-out on entrance, small distance (roughly
   16–28 px at a 1080px reference width), opacity interpolation, no bouncing.
5. **Speech alignment:** synchronise text reveals to relevant narration rather
   than always beginning at shot start. Explicit timing parameters for spoken
   phrases are a future extension, not something to infer automatically.
6. **Avoid:** glitch and random shake, unsolicited film-burn or colored flashes,
   split-letter effects, spinning titles, stock zoom transitions, overshoot,
   and persistent motion that competes with information.

## Implemented

An opt-in `motion.preset = editorial_reveal` uses locally created separate
RGBA assets for the logo, kicker, accent, headline, body and footer. FFmpeg
composes cropped layers with staggered alpha fade and cubic ease-out y-offset.
`fade_stagger` removes translation. Static cards remain identical when motion
is unspecified. Per-scene duration limits prevent animation from overtaking the
message. Every shot is cacheable independently of shot assembly.

Reference principles:
- [Apple Motion](https://developer.apple.com/design/human-interface-guidelines/motion)
- [Material duration & easing](https://m1.material.io/motion/duration-easing.html)
- [Adobe After Effects — animating text](https://helpx.adobe.com/after-effects/desktop/animating-text/text-animation/animating-text.html)
- [Morningstar Motion Design](https://design.tec7072a.eas.morningstar.com/foundations/motion)
- [Greenhouse Motion Language](https://brand.greenhouse.com/motion-language)

Do not interpret these sources as a frame-by-frame audit of any specific ad.
Creative parity requires comparing actual reference videos and exported frames.

## Editorial quality gate (automated, but not aesthetic certification)

`reels-maker validate <manifest> --syntax-only --strict-quality --json`
returns a machine-readable failure if conservative warnings are present.
The render API emits `quality.status`, `quality.warning_count` and
structured warnings for downstream agents. It checks text reading-time
budget (~19 characters/s), a settled frame hold, too many emphasized runs,
and excessive or repeated transition presets. It never automatically
rewrites the user's story or inserts effects.

**Passing these checks does not certify professional quality.** A real final
review still needs proxy playback on a phone, legible contrast against
footage, deliberate shot choice, narrated audio timing and licensed content.

## Format-independence safety

Never derive typography exclusively from width or assume 9:16. The standard
relative typographic scale uses the *shorter* video dimension. Explicit
project safe areas use exact output pixels; unset margins follow output ratios.
Actual publishing UI varies by platform and is subject to manual review.

## Aligning caption entrances with verified narration times

Animators can now override the default sequential staggering per element using
**scene-local timecodes** in the `motion` object. Two equivalent forms are
supported, but cannot be combined in one scene:

```json
{
  "title": {
    "headline": {"runs": [
      {"text": "WIĘCEJ ", "scale": 0.80},
      {"text": "ENERGII", "scale": 1.30, "color": "accent"},
      {"text": " dla biznesu", "scale": 0.78, "break_before": true}
    ]},
    "body": "Fotowoltaika i magazyny energii"
  },
  "motion": {
    "preset": "rise_soft",
    "duration_frames": 7,
    "stagger_frames": 2,
    "distance_px": 18,
    "cue_seconds": {
      "headline-0": 0.40,
      "headline-1": 1.04,
      "headline-2": 1.60,
      "body": 2.04
    }
  }
}
```

`cue_seconds` uses **seconds from the beginning of that source scene in the
output edit**, snapped to the nearest actual output frame at the video's FPS.
`cue_frames` accepts integer frame offsets instead. Valid semantic roles are
`logo`, `accent`, `kicker`, `headline` (plain title),
`headline-0`, `headline-1` etc. (rich runs), `body`, `footer`. Keys
must target an existing layer; stale/unknown cues, mixed time bases, negative
or nonfinite timestamps, and cues which leave less than 0.55s of settled text
are rejected **before** encoding. Omitted roles retain editorial staggering.

The engine does **not** claim to transcribe speech or detect beats. Map verified
narration timestamps or manually spotted musical accents to these cues; then
inspect the final MP4 with sound. If a dissolve follows, outgoing overlap can
reduce the true reading window: strict-quality lint accounts for that and the
storyboard refuses to label an unfinished reveal as a settled frame.

## Narration, mix and music hierarchy

The renderer now separates `voiceover` from `music`. Avoid mixing voice
into the soundtrack permanently before editing: its natural gaps should
remain visible to the sidechain envelope. A controlled, optional FFmpeg
compressor ducks music when the narrator speaks, with moderate ratio/attack
and gradual release. The AAC export uses a 48kHz mix and a peak limiter.
This is **not** a substitute for a sound engineer's final review: listen for
ducking artifacts, syllables obscured by music, excessive gain and unnatural
silence. The engine does not synthesize voices or automatically align speech.

## Generate a timeline cue sheet before the final audio mix

```sh
reels-maker cue-sheet project.json --json
reels-maker cue-sheet project.json --output renders/qa/narration-cues.json --json
```

This reports scene-local and **absolute final-timeline** frame/time positions
for each text run, accounting for `xfade` overlaps. It includes narrator
`offset_seconds` and marks reveals partially hidden by incoming/outgoing
transitions. It never guesses spoken content or rewrites the narration.
Match the output to the final WAV waveform, then audit in motion on a phone.

## Optional manually verified spoken-word markers (strict sync QA)

To guard against an edit that makes text appear too early or late relative to
the *actual* narrator, add manually spotted word timestamps from the **original
voice recording**. Markers are never guessed by speech recognition:

```json
{
  "voiceover": {
    "file": "media/audio/narrator.wav",
    "start": 0.20,
    "offset_seconds": 0.10,
    "sync_marks": [
      {
        "scene": 2,
        "role": "headline-1",
        "source_seconds": 2.18,
        "tolerance_frames": 2
      }
    ]
  }
}
```

`scene` is 1-based. `source_seconds` points into the original audio file,
**before** `voiceover.start` trims it. The expected final-timeline time is
`source_seconds - voiceover.start + voiceover.offset_seconds`; meanwhile,
the visual text's global frame accounts for all intervening xfade overlaps.
If the absolute difference exceeds `tolerance_frames` (default 2, range
0–6), `cue-sheet` reports `narration_cue_drift`; `--strict-quality`
refuses the campaign before render. Markers pointing outside the final
timeline, to missing text runs, or beyond the WAV source duration also fail
validation. The cue-sheet report now includes `sync_marks`, `delta_frames`,
and `delta_seconds`, making editing decisions auditable.

This checks **declared** manually verified word times against programmed
visual entrances. It does not prove a WAV actually contains that word, or
replace listening to the final file. When narration is retrimmed, re-check
the original source timestamps. Never silently treat unmarked speech as
aligned.
