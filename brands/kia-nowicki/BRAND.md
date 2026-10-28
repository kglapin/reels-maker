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

- Every spoken line gets a burned-in caption; one line per scene segment.
- Short lines: max ~42 characters per caption; split long sentences at
  natural breath points; never mid-word.
- Position `lower`, theme `dark`, backdrop `soft`.
- No emoji, no ALL CAPS shouting; sentence case with proper punctuation.
- Never cover the speaker's face: captions live in the lower safe area.

## Footage rules

- Client media stays in `imports/` (git-ignored quarantine). Nothing client
  related is committed to the public repository.
- Punch-in crops on the speaker's face are only added while he is talking;
  hold the wider framing during reaction shots.
- No new logos or titles over finished promo footage that already carries
  burned-in graphics (`source_is_prebranded` strict gate).
- The dealership's own licensed font (KiaDesignK) is used for all overlays.

## Delivery gates (unchanged, per repo AGENTS.md)

- Human review on an actual device with sound (`docs/REVIEW_RUBRIC.md`) before
  publishing; automated QA never certifies the creative.
