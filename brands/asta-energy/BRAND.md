# ASTA Energy — Brand guidelines

This directory owns the brand identity, reusable media and animation manifests.
Read **brand.json** as the machine-readable source of truth; read this file for
editorial rules before generating an ASTA Energy Reel.

## Visual identity
- Primary color: **#47A013**; use green intentionally, not as heavy gradients.
- Preferred typeface: **Open Sans**. Fallback: DejaVu Sans until a locally
  installed, appropriately licensed Open Sans font path is configured.
- Use `assets/logo.png` for video overlays. `assets/logo.svg` is the original.
- Short headings and restrained typography; keep a clear hierarchy.
- Default vertical 9:16, 1080×1920, with social-platform-safe placement.
  Treat the safe-area values in brand.json as initial guidance, not a substitute
  for platform-specific publishing checks.
- Avoid unnecessary motion, box-heavy layouts, excessive transitions and
  overcomplicated graphics. Keep transitions tied to the story or music.

## Sound and pacing
- Audio is optional: use music, voice-over or SFX only if the project requests it.
- Prioritize speech intelligibility when adding voiceover or sound effects.
- Respect beat-synchronized montage cuts. Verify all sound licenses.

## Reusable assets
- `media/footage/` — original ASTA installation footage.
- `media/stock/` — external stock clips; license and attribution are documented
  in `licensing/stock_credits.txt`.
- `media/audio/` — supplied music, with rights to be verified before publication.
- `media/fx/` — short transition video overlays.
- `assets/` — reusable logo exports.
- `references/` — saved marketing source pages.
- `projects/` — manifests inheriting defaults from `brand.json`.

## Content standards
- Never assume a saved financing programme page is currently accurate.
- Recheck programme eligibility, amounts, deadlines and legal terms before
  publishing marketing claims.
- Avoid adding final rendered videos or temporary outputs to this brand folder.
  Write them to `renders/asta-energy/` and keep them outside normal commits.
- Historical completed videos are in `renders/asta-energy/archive/`.
- Historical work files are preserved in `archives/asta-energy/intermediates/`;
  these are legacy reference assets, not active render inputs.

## Adding another brand
Create `brands/<brand-slug>/brand.json`, `BRAND.md`, optional `assets/`,
`media/`, and `projects/`. The Python engine should never be forked or
copied per brand.
