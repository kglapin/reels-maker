# Renderer extension spec: horizontal cylinders + bevels

## Problem (owner verdict 2026-11-12)

Props stay blocky: every tube must stand vertical (`_cylinder` builds
only Z-axis staves), every edge is perfectly sharp (`q.box` paints flat
faces). Independent reviewers repeatedly flag: square nozzle caps,
slab chains, pointed dome apex, voxel staircase on round parts.
No amount of small-box detail fixes a missing primitive.

## Scope (additive only — zero impact on existing renders)

1. **`_hcylinder_x` / `_hcylinder_y`** in `src/reels_maker/iso/world.py`:
   same stave loop as `_cylinder` with axis permuted (X: quads span
   x0..x1 at (y,z) circle; Y: quads span y0..y1 at (x,z) circle),
   same `rim=` / `top_ring=` semantics renamed to `cap0=` / `cap1=`
   (flat sealing discs at both ends, painted by the caller FIRST when
   buried — playbook rule 14 applies unchanged), end faces via the
   existing `q.disc_x` / `q.disc_y`. ~50 lines + docstrings.
2. **`q.box_beveled(a, b, bevel, ...)`** in
   `src/reels_maker/iso/projection.py`: 3 visible faces + 3 edge
   strips (top+X, top+Y, X+Y arrises), painted far→near in call order.
   ~70 lines. Adopted ONLY by explicitly rewritten builders.
3. Tests: `tests/test_iso_cylinder_caps.py`-style contracts —
   flag semantics, no-ellipse guarantees, plus an audit-level
   exact-touch run over every adopter (existing
   `test_iso_layer_audit.py` covers them automatically once registered
   in `BATCH_MODULES`).

## Cost estimate

- `_hcylinder_x/y` + unit tests: ~0.5 day. Risk: low (mirrors proven
  code; painter order is the caller's responsibility, same as today).
- `box_beveled` + unit tests: ~1 day. Risk: medium (edge-strip order
  vs adjacent faces needs per-prop verification: pixel + audit + gate).
- Rollout (opt-in per prop, each with pixel + audit + ensemble gate):
  ~15 min/prop. Suggested first adopters: hydrant side nozzles
  (round caps), extinguisher valve, kiosk counter rail, gutter runs,
  ladder rungs — the exact spots reviewers flagged.
- Film goldens: untouched (additive; existing builders unchanged) —
  verified by running `test_studio_golden` + `test_golden_frames`
  after the merge (they pass today after the circulator/thermostat/
  radiator fixes).

## Explicitly out of scope

No depth-buffer rewrite, no subdivision/lathe, no PBR materials —
those would change every pixel in the repo. Bevels stay subtle
(1–3% of part size); hero roundness comes from the new cylinders.
