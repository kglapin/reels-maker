# Nowicki KIA Kalisz — social video brand guidelines

Owner-supplied brand for short vertical (9:16) social video made from the
dealership's own footage. This file documents the caption and overlay rules
used by every project under `projects/`.

## Palette

| Role | Value | Use |
|---|---|---|
| Primary / accent | `#BB162B` (KIA red) | Accent rule, highlighted words |
| Background | `#05141F` (midnight black) | Caption backdrop, end cards |
| Text | `#FFFFFF` (white) | Captions, subtitles |
| Neutral | `#8A8F94` | Secondary body text |

## Typography

- Family: **KiaDesignK** (operator-supplied, licensed locally under
  `imports/fonts/` — never commit the TTF files, they are licensed assets).
- Captions: Bold, white, lower third, soft dark backdrop for legibility over
  bright window footage.
- Keep Polish diacritics intact (ą, ć, ę, ł, ń, ó, ś, ź, ż).

## Captions / subtitles (mandatory on dialogue)

- Every spoken line gets a burned-in caption; one caption per speech unit.
- **Karaoke emphasis**: the word currently being spoken turns bright white
  while not-yet-spoken words stay muted grey (per-frame overlay rendered from
  `KiaDesignK-Bold`; implemented by `projects/_build_killer3_captions.py`
  because the local FFmpeg builds ship without libass/drawtext).
- Position: as close to the vertical centre as possible, never covering a
  speaker's face (per-scene y offsets measured from QA frames).
- Short lines: max ~42 characters per caption; split long sentences at
  natural breath points; never mid-word.
- No emoji, no ALL CAPS shouting; sentence case with proper punctuation.
- Meme-style stage labels (e.g. `wchodzi kierownik`) use the same caption
  style, lowercase, centred.
- Scene transitions between films use a white dip: fade-to-white on the
  outro of the outgoing clip and fade-from-white on the incoming clip,
  which must already be in visible camera motion at its trimmed start.

## Footage rules

- Client media stays in `imports/` (git-ignored quarantine). Nothing client
  related is committed to the public repository.
- Punch-in crops on the speaker's face are only added while he is talking;
  hold the wider framing during reaction shots.
- No new logos or titles over finished promo footage that already carries
  burned-in graphics (`source_is_prebranded` strict gate).
- The dealership's own licensed font (KiaDesignK) is used for all overlays.

## Production notes (lessons from PITBULL reel, 2026-10-30)

Reference implementation: `projects/_pitbull_build_media.py`,
`_pitbull_build_audio.py`, `_pitbull_captions_table.py`,
`_build_pitbull_captions.py`, `_generate_pitbull_manifest.py`; output
`renders/kia-nowicki/kia-nowicki-pitbull-reel.mp4` (67.27 s, 30 fps).

### Captions

- Keep captions near the vertical centre (y≈920–950 on 1080×1920) from ~10 s
  onward; the desk intro reads fine at y≈1050. Never cover a face — on these
  salon shots faces end at y≈630–665, so 920+ is safe.
- Punch-in 3 (price line) uses y=1150 so the caption clears the windshield
  `109 900` tag.
- Owner rule: only the swear word becomes `^#%@$@^`; names and all other words
  stay untouched (e.g. capitalised `Wąsik`). Do not replace neighbouring words.
- Quiet/swallowed swears are missed by Whisper (a muffled one at 15.96–16.36 s
  in the PITBULL dialogue). Check short-time RMS next to suspicious gaps and
  confirm with the owner; do not rely on the transcript alone.

### Audio

- Censor beep: 1 kHz sine, exactly over the swear window (+~40 ms margin),
  dialogue silenced underneath, mixed on the music track only; the rest of the
  sentence stays audible. Build windows from the original dialogue every time
  (`_pitbull_build_audio.py`) instead of editing an already-masked file.
- The `music` track must be at least as long as the video
  (`Music segment is shorter than the requested video`): pad the dialogue with
  silence (`apad`, then trim `-t`) to the full reel length.
- `apad` cannot be combined with `-c:a copy`; a corrupted AAC padded WAV breaks
  the final encoder — re-encode padded VO as clean AAC.

### Endcard (drone + teleadresowa)

- Scheme: 1.1 s dip-to-white from the master tail, then the drone with a short
  fade-from-white. Trim the first ~1 s of the drone so camera motion toward the
  building is visible immediately; 0.3 s fade is enough for the dip.
- The teleadresowa VO starts **together with the drone cut**
  (`voiceover.offset_seconds` = drone start), not on the white dip.
- `nowicki-kalisz-radio-dogrywka-teleadresowa.wav` has speech from 0.00 s
  (not ~0.6 s), so drone captions must follow its real word onsets:
  Nowicki 0.00, zaprasza 0.44, Kalisz 1.22, ulica 1.76,
  Stanczukowskiego 2.10, `18.` 2.84.

### Pipeline gotchas

- The caption burner appends `_cap` to the target name: point captions at the
  clean source (`pitbull_punch1_table.mp4`), never at an already-burned file,
  or you get `_cap_cap` doubles.
- Snap scene boundaries/durations to whole frames (1/30 s) so karaoke times
  stay aligned after manifest quantisation.
- Punch-in template: 720×1280 crop (1.5×) scaled back to 1080×1920, centred on
  the speaker while he talks.
- Burning PIL overlays for a ~60 s reel takes ~2 min — run it in the background
  and always finish with storyboard review on the final MP4.

## Delivery gates (unchanged, per repo AGENTS.md)

- Human review on an actual device with sound (`docs/REVIEW_RUBRIC.md`) before
  publishing; automated QA never certifies the creative.
