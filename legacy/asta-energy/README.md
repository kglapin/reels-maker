# ASTA Energy video project — production files

## Folder layout
- `scripts/` — Python render scripts and montage-generation scripts.
- `assets/commons/` — downloaded external stock footage used by the subsidy promo.
- `assets/stock_credits.txt` — required attribution and program-source notes.
- `references/` — snapshot of the ASTA financing page used to check the claims.
- `work/subsidy_ad/` — intermediate shot renders, title cards, and concatenated media.
- `../render/` — final MP4 renders only.

Original source clips, SVG logo, and audio supplied by the client remain in the project root.

## Latest render
`../render/asta_dotacje_magazyny_energii_30s_external.mp4`
- Portrait 1080 × 1920, 29.72 seconds.
- Built only from external stock (Wikimedia Commons: CC0, public domain, CC BY) — no ASTA archive footage.
- Typography is rendered in PIL with measured baselines, letter-spaced kickers, a green accent bar and gradient scrims instead of solid boxes.
- Polish promotional cards based on the ASTA page; the maximum-support claim carries an on-screen disclaimer.
- Music supplied by the client; 1.2 s fade-out at the end.
- Attribution for every external clip: `assets/stock_credits.txt`.

## Re-render
Run `python3 scripts/create_subsidy_ad_external.py` (subsidy promo, external footage) or
`python3 scripts/make_dynamic_montage.py`, `make_vamos.py`, `make_vamos_from_start.py` (music montages).
The scripts read source video/audio from the parent project folder, write intermediates under
`work/` and final MP4s to `../render/`.

Before publishing, re-check the NFOŚiGW programme dates, amounts, and conditions against the current official rules. The ASTA page snapshot is dated 22 October 2026.
