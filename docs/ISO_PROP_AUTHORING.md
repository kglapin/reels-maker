# Iso prop authoring contract (for humans and LLMs)

How to describe and implement a new isometric prop for `src/reels_maker/iso/`.
This document is the single source of truth an external LLM needs to produce
a builder that passes the quality gates on the first or second attempt.

Read `docs/iso-prop-playbook.md` for the full craft history; this file is the
normative contract. When they disagree, this file wins.

## 1. What a prop is

A prop is a Python function in `src/reels_maker/iso/props_<batch>.py`:

```python
def my_prop(q, cx, cy, P):
    """One-line brief of what the object IS (also used as catalog text)."""
    ...
```

- `q` — `Canvas` drawing surface (see §3).
- `cx, cy` — placement center in world units; the builder works relative to
  it. The gallery calls `fn(q, 0.0, 0.15, P)`.
- `P` — palette dict (`DEFAULT_PALETTE` keys: `bg`, `white`, `mint`, `muted`,
  `gold`, `cool`, `ice`, `amber`, `dark`). Batch modules may define local
  material constants (e.g. `BRASS_F/S/T`) — reuse the batch palette first.

Each batch module ends with a `PROPS` registry entry:

```python
PROPS = {
    "my-prop": {"fn": my_prop, "focus": (0.0, 0.15, 0.45), "k": 550,
                "plinth": (0.0, 0.15, 0.55, 0.34),
                "brief": "what it is, in one line"},
}
```

`focus`/`k`/`plinth` are tuned per prop by rendering the gallery (§7); start
with `k≈400-600`, `focus≈(0.0, 0.15, mid-height)` and adjust.

## 2. Coordinate system and camera contract

- Right-handed world units, roughly meters. Typical prop: 0.3–2.0 units tall,
  footprint ≤ ~1.2×1.2. The camera shows **+X, +Y and +Z faces**; -X/-Y faces
  are never visible — never spend geometry there.
- `z=0` is the ground/plinth plane. Feet and pads start at `z=0`.
- Isometric projection is affine: `u = C·(x−y)`, `v = (x+y)/2 − z`.
  Depth key used by the renderer: **`x + y + z`, larger = nearer**.

## 3. Canvas API (all drawing goes through `q`)

| call | signature | notes |
|---|---|---|
| `q.box` | `(a, b, front, side, top)` | axis-aligned box, a=(x,y,z) min, b=(X,Y,Z) max; per-face flat colors |
| `q.boxg` | `(a, b, c, *rest, dl=0.14)` | gradient box: vertical light falloff + top hairline highlight; `c` is base color |
| `q.poly` | `(pts, c)` | arbitrary world polygon; `c` = (r,g,b) or (r,g,b,a) |
| `q.fp` | `(x, X, y, z, Z, c)` | flat rectangle on the +Y face plane |
| `q.line` | `(pts, c, w=1)` | polyline, `w` in world units |
| `q.dot` | `(p, r, c)` | screen-space disc at world point `p`, radius `r` (×2 px) |
| `q.disc_x` / `q.disc_y` | `(…, r, c, n=36)` | disc in X=const / Y=const plane (gauge faces, wheels) |
| `q.ground_ellipse` | `(cx, cy, rx, ry, c, z, n)` | ellipse on a horizontal plane |
| `q.tube` | `(cx, cy, z0, z1, r)` | **marker only** — declares a vertical tube body for audits; draws nothing |
| helpers in `world.py` | `_cylinder`, `_on_cylinder`, `chamfered_box`, `contact_shadow`, `sheen`, `shade_face`, `decal` | prefer these over hand-rolled equivalents |

`chamfered_box(q, a, b, chamfer, c)` — octagonal footprint with
azimuth-shaded faces and lit top rim. **Default choice for any
manufactured enclosure** (boxes, cases, housings, lids).

`_cylinder(q, cx, cy, z0, z1, r, c_light, c_dark, c_top, n=64, rim=True,
top_ring=True)` — smooth-shaded vertical vessel. `rim=False` when the foot
is buried in a plate; `top_ring=False` when the top is buried in the next
solid (a cap would paint a phantom disc over it).

## 4. Materials and palette

- Mid-tone fills only: every channel ≥ ~60. The scene is dark; pure
  black/white read as holes or glare.
- **Contrast separation**: adjacent parts must differ in tone — pipe vs
  collar vs body need distinct values or the assembly melts into one mass.
- Metal reads via value steps, not texture: light face / mid face / dark
  face triples per material (see `BRASS_F/S/T` pattern).
- Emissive details (LEDs, screens, gauges) may use saturated accents from
  `P` (`mint`, `amber`, `gold`, `cool`) — one accent per prop, not five.
- No text decals. Labels are abstract bars, dashes and dots only.

## 5. Structural rules (hard)

1. **Overlap, never exact-touch.** mating parts overlap ≥ 0.005 world units
   (roots start *inside* the parent, collars straddle seams). Exact
   coplanar faces alias into hairline gaps — the layer audit fails on it.
2. **Nothing floats.** Every part connects to the assembly or to a foot/pad
   on the ground. The pixel floater check fails disconnected ink.
3. **Grounding.** Props end in feet, pads, skirts or a plinth contact —
   never a bare box edge on z=0. Gallery props get NO contact-shadow
   ellipses (owner rule; rooms suppress them too).
4. **Details on visible faces only.** Screen bars, gauges, ports, hinges go
   on +X/+Y faces (the faces the camera sees). Anything on -X/-Y is dead
   geometry.
5. **Roots, not touches.** Stubs/pipes start inside the body they enter;
   they never begin exactly at the surface.
6. One hero element per prop. Secondary parts support it; if a detail
   survives only as slivers it is decoration — shrink the occluder or
   enlarge the part.

## 6. Visibility contract — painter vs depth buffer

Default renderer is **painter's algorithm**: later draw calls win. Correct
order is far → near (smaller `x+y` first, larger last).

`REELS_ISO_DEPTH=1` enables a per-pixel depth buffer: opaque `poly`/`dot`/`line`
calls resolve visibility from world depth, so **call order stops mattering
for opaque geometry** — parts behind walls cannot paint on top, period.
Translucent overlays (alpha < ~250) still composite in call order and never
claim depth — shadows, glass, sheen and light bands keep painter semantics
by design.

Still painter-order regardless of mode:
- `grad_poly` / `boxg` side faces — draw in far→near order.
- `decal` — always composites on top; use only for intentional overlays
  (labels, gauges) and keep it small.

**Authoring rule that never changes:** write geometry as if order doesn't
matter (it mostly doesn't now), but keep the far→near habit — it is the
fallback path and costs nothing.

## 7. Workflow and acceptance gates

```sh
# 1. render the gallery frame + clean plate
.venv/bin/python tools/iso_gallery2.py props_<batch>.<prop> <NN-title>

# 2. pixel pre-check + framing (auto-reframed, must print pixel_ok: true)
# 3. layer audit (exact-touch, buried-detail, inversion)
.venv/bin/python tools/iso_layer_audit.py --prop props_<batch>.<prop>

# 4. LLM vision critique — REQUIRED before showing the owner
.venv/bin/python tools/iso_prop_critic_llm.py \
    renders/asta-energy/prop-galeria/<NN-title>.png \
    --brief "<the one-line brief>" --provider nvidia
```

Acceptance: `pixel_ok: true`, zero audit errors, critic verdict `pass`.
Warnings are review prompts, not failures — but every warning needs a
one-line justification in the commit message.

## 8. Describing a new prop (input format for an LLM)

Give the model this skeleton; it returns a builder function + PROPS entry:

```
PROP SPEC
- name: kebab-case, unique across all props_<batch>.py
- brief: one line, what it IS ("tall slim DHW cylinder with coil ports")
- batch: existing props_<batch>.py to extend, or new batch name
- hero: the single element that must read first
- parts: ordered list of primitives with dims/positions/material roles
- materials: which batch palette constants or new triples to define
- footprint: approx (w, d) and height in world units
- grounding: feet/pads/plinth description
- accent: at most one saturated detail (LED, dial, screen)
```

Rules for the model: translate "real object" knowledge into the primitive
catalog only — no invented APIs, no SVG, no images, no text. If a detail
cannot be built from §3 primitives, simplify it to the closest readable
abstraction (bars, dots, dashes) rather than dropping it silently.

## 9. Anti-patterns (each one has burned us before)

- Buried caps: painting a top disc inside a solid that covers it — use
  `top_ring=False` / `rim=False` on `_cylinder`.
- Seal discs for open tube mouths must be painted BEFORE the covering
  solid and only where the solid covers the center.
- Walls/floors drawn after their contents (in painter mode) — contents
  must come first in code order.
- "Wasted geometry": parts fully hidden behind the hero — delete them,
  they cost render time and confuse audits.
- Exact-size matches: two parts sharing a face plane → guaranteed
  hairline gap. Overlap by ≥0.005 always.
- Per-frame regenerating textures or random layouts — props must be
  deterministic functions of `(q, cx, cy, P)` only.
