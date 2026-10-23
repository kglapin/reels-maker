# Reference-derived kinetic motion design roadmap (reels11.py)

This note maps a supplied 394-line, Cairo-per-frame campaign renderer into
reusable, brand-safe engine capabilities. Do not copy the script's absolute
pixel placements, original assets, sound tracks or hardcoded timeline.

## What makes the reference stronger
- `pop(cx,cy,t,t0,dur)`: local entrance curve, scale and group alpha.
- `amountbox` and `fmt`: values count up to a verified target.
- `photo_card`: zoom/pan from explicit keyframed focal regions.
- `donut`: chart data animates, instead of appearing static.
- `wipe`: motivated two-color transition synchronized to a boundary.
- `build_audio`: narrator/music RMS measurement with attack/release ducking.
- `check`: sampled frame-space text bounding boxes and collision checks.

## Implemented in current bounded change
- `reels_maker.kinetics.counter_value`, `ease_out_cubic`,
  `animated_crop`, `format_pln`: deterministic timing primitives.
- `motion.preset=kinetic_rise`: faster vertical text entrance in the native
  FFmpeg renderer, still obeying the existing explicit cue schedule.
- Unit tests for cue onsets, monotonic values, safe crop interpolation and
  invalid numerical inputs.

## Still required before promising reference-level output
1. Connect counters to time-varying rendered layers via a Cairo or Pillow
   layer-stream backend that is reusable for every brand. Provide alpha video
   or a frame cache; avoid re-encoding the entire background per value update.
2. Expose anchored component slots with measured text boxes and spacing,
   preventing overlap by construction. Pixel placement alone is insufficient.
3. Add 2D motion composition for image focal keyframes; verify crop stays
   inside the photograph and is safe at source resolution.
4. Implement chart components (donut, budget bar, EU diagram) with accessible
   labels and editorial rules rather than arbitrary decorative SVG.
5. Sample all animation frames (or representative transition windows), flag
   glyph/object collisions and UI exclusion areas; preserve manual review.
6. Extend visual QA to compare actual 9:16 campaign renders side-by-side
   with the user-approved reference, and review audio timings on recorded words.

The previous weak Reels was created by a separate Pillow script, not the
native repository pipeline. Maintain a single generator rather than another
one-off renderer. Source media must remain license-reviewed and suitable for
a home-storage subsidy campaign; do not represent utility-scale industrial
containers as typical residential batteries.

## Acceptance gates
A) program claims and asset rights verified
B) accurate pronunciation/cue alignment
C) no overlapping bounding boxes or clipped amount
D) full-phone size legibility and useful reading holds
E) no constant/repetitive effects on every scene
F) explicit human creative approval; green CI is not art direction
