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

## Standard endcard (mandatory for every new film)

All new KIA Nowicki films end with the same **9.1 s endcard**. Do not design a
new outro and do not reintroduce the “Więcej na…” line.

Timeline (absolute output time; `<dip_start>` is where the outgoing film ends):

```
0 .. dip_start                 outgoing captioned film
dip_start .. dip_start + 1.1   1.1 s dip-to-white from its last 1.1 s
dip_start + 1.1 .. dip_start + 9.1  8.0 s dealership drone (fade-from-white 0.30 s)
```

Assets and config:

- `projects/endcard-standard.json` — canonical timings, captions and mix.
- `projects/_build_endcard_standard.py` — rebuilds the reusable assets.
- `imports/footage/endcard-standard-drone_cap.mp4` — 8.0 s captioned drone.
- `imports/audio/endcard-standard-voice.wav` — 7.39 s address + KIA tag.
- `projects/endcard-standard-captions.json` — two caption plates.
- `imports/footage/endcard-standard-full.mp4` — **9.1 s ready-to-append clip**
  (1.1 s white lead-in + captioned drone + standard voiceover).
- `renders/kia-nowicki/endcard-standard.mp4` — same clip as the delivery copy
  for easy access.

Voiceover:

- **„Nowicki zaprasza. Kalisz, ulica Stanczukowskiego 18.”** — hard cut at
  **3.74 s**, immediately after “osiemnaście”, in the natural decay,
  **without any fade**. The “Więcej na…” sentence is never used.
- **0.55 s breath**, then the female **„Kia – movement that inspires”** tag
  from `imports/audio/kia-movement-that-inspires-tag.mp3` (source
  **27.10–30.20 s**, 0.05 s fade-in, 0.20 s fade-out from 2.90 s).
- Mix volume **0.55**; `voiceover.offset_seconds = <dip_start> + 1.4`
  (drone cut + 0.30 s, after the fade-from-white). The tag is a sonic logo
  and is **not captioned**.

Captions:

- Only **„Nowicki zaprasza.”** (0.30–1.48 s local to the drone) and
  **„Kalisz, ulica Stanczukowskiego 18.”** (1.48–4.02 s), 62 px, y=1000.
- No website line. No tag caption.

Per-film dip (built from the outgoing captioned film):

```sh
ffmpeg -ss <dip_start> -t 1.1 -i <film_cap.mp4> \
  -vf "fade=t=out:st=0.08:d=1.02:color=white" -an ...
```

The drone already starts with a 0.30 s fade-from-white, so the dip resolves
into visible camera motion immediately.

### Ready-to-append clip

`renders/kia-nowicki/endcard-standard.mp4` is the whole ending as one file:
**9.1 s**, 1080×1920, 30 fps, with the 1.1 s white lead-in, captioned drone
and standard voiceover. Append it at the end of a film and you are done.
It is intentionally **not loudness-normalised**: it carries the same
voiceover level as the film mix, so do not re-normalise it when appending.

- If the film already fades to white, trim the first 1.1 s and use
  `imports/footage/endcard-standard-drone_cap.mp4` plus
  `imports/audio/endcard-standard-voice.wav` with the manifest recipe above.
- Rebuild everything with
  `python brands/kia-nowicki/projects/_build_endcard_standard.py`.

Manifest recipe:

```json
"scenes": [
  {"file": "<film_cap.mp4>", "start": 0.0, "duration": "<dip_start>"},
  {"file": "<project>_dip.mp4", "start": 0.0, "duration": 1.1},
  {"file": "imports/footage/endcard-standard-drone_cap.mp4",
   "start": 0.0, "duration": 8.0}
],
"voiceover": {
  "file": "imports/audio/endcard-standard-voice.wav",
  "start": 0.0,
  "offset_seconds": "<dip_start + 1.4>",
  "volume": 0.55
}
```

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

Superseded by **“Standard endcard”** above (2026-11-12). The PITBULL-era
scheme (voiceover starting at the drone cut, website line captioned) is
historical only; do not use it for new films.

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

## Production notes — SEN film (2026-11-12)

Reference implementation: `projects/_sen_build_media.py`,
`_sen_build_captions.py`, `_sen_captions_table.py`,
`_generate_sen_manifest.py`; output
`renders/kia-nowicki/kia-nowicki-sen.mp4` (138.43 s, 30 fps, 1080×1920).

### Grade

- Source mixes orange exterior, cool showroom glass, warm wood and a dark car
  interior. Use per-frame highlight white balance + one restrained S-curve,
  not a fixed teal/orange LUT: `colorcorrect=analyze=average:saturation=1.04`,
  `eq=contrast=1.08:brightness=0.004:gamma=1.02`,
  `curves=all='0/0 0.22/0.19 0.5/0.53 0.78/0.82 1/1'`,
  `vibrance=intensity=0.10`, `unsharp=5:5:0.5`.
- The drone is a summer shot; mute green/contrast it slightly and bridge with
  the 1.1 s dip-to-white, otherwise the season mismatch is obvious.

### Captions

- 57 karaoke plates: 55 in the film, 2 on the drone. y=1000 everywhere except
  the 11.7–16.0 s showroom exterior voice-over (y=780, where the walking
  speaker occupies the lower centre).
- Deliberate size hierarchy (owner request): 58 px base dialogue; 62–70 px
  for important information; 76–86 px for punchlines/reveals; and the three
  remaining “Wąsik!” calls escalate 64 → 78 → 92 px with one extra
  exclamation mark each. Stroke, shadow and caption plate scale with the
  type, so the hierarchy stays optical rather than arbitrary.
- Source ASR errors that were corrected: `Brzonka` → `Żonka`, `potawi` →
  `potrafi`, `tą` → `tę`, `G-T-Line` → `GT Line`, `dopięć` → `dopiąć`,
  `kabinetu` → `gabinetu`, `wyzwano` → `wezwano`, `nieże` → `nieźle`,
  `Coś tu narobił` → `Co żeś tu narobił`, `Patrz się` → `Bać się?`.
- Owner decisions: keep the spoken colloquial **„Sportki”** in Polish
  quotation marks (not “Sportage”); punctuation is **„Żonka to potrafi rozbudzić! Ale mi się
  dobrze zaczął dzień.”**; the final quiet “Wąsik.” at 129.04 is removed.
- The “Więcej na…” line is cut from the teleadresowa. The drone endcard
  keeps only “Nowicki zaprasza.” and “Kalisz, ulica Stanczukowskiego 18.”,
  then plays the owner-supplied female **„Kia – movement that inspires”**
  tag (`imports/audio/kia-movement-that-inspires-tag.mp3`, source
  27.10–30.20 s). The tag is a sonic logo and is intentionally not captioned.

### Ending / audio

- The last quiet “Wąsik.” at 129.04–129.80 is intentionally not captioned
  (owner request); the picture fades to white without a caption on the dip.
- Dialogue is denoised and normalised to -14.5 LUFS / -1.4 dBTP. The new
  combined voiceover (`sen_voiceover.wav`) is address 0–3.74 s (hard cut
  right after “osiemnaście”, no fade) + 0.55 s breath + KIA tag
  4.29–7.39 s; it starts 0.30 s after the drone cut
  (offset 130.733) so the first caption is not white-on-white during the
  fade-from-white; volume 0.55.
- This is the canonical **standard endcard** (see the section above). The
  SEN `sen_voiceover.wav` and `drone_sen_cap.mp4` are byte-identical to
  `endcard-standard-voice.wav` and `endcard-standard-drone_cap.mp4`.

## Delivery gates (unchanged, per repo AGENTS.md)

- Human review on an actual device with sound (`docs/REVIEW_RUBRIC.md`) before
  publishing; automated QA never certifies the creative.
