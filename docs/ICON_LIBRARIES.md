# Icon libraries — Lucide / Heroicons

Native studio scenes can use real, upstream SVG icon assets instead of
custom-drawn primitive icons. Both packs are version-pinned; source files are
cached persistently and rasterizations are memoized during export.

## Installation

```bash
pip install -e '.[icons]'
```

No JavaScript runtime is needed. Python downloads original icons from their
upstream GitHub release only when absent in the local cache
(`~/.cache/reels-maker/icon-libraries/`). Cached SVGs render offline.

## Replace hand-drawn icons in built-in scene compositions

```json
{
  "composition": "energy",
  "duration": 3.0,
  "headline": "Lorem ipsum",
  "icon_library": "lucide",
  "icon_style": "outline",
  "icon_names": {
    "sun": "sun",
    "house": "house",
    "battery": "battery-charging",
    "arrow": "arrow-right"
  }
}
```

The `amount` / `hero-number` component uses `battery`. The
`checklist` component uses `check`; `energy` uses `sun`, `house`,
`battery` and `arrow`. To use Heroicons instead:

```json
{"icon_library":"heroicons","icon_style":"solid",
 "icon_names":{"battery":"battery-100","arrow":"arrow-right"}}
```

Without `icon_library`, legacy primitive icons remain unchanged.

## Add arbitrary positioned icons

Any scene may include an `icon_assets` array. Positions are relative to
video dimensions (x and y in 0–1), and size is a fraction of video width:

```json
{
  "composition": "statement",
  "duration": 3.0,
  "headline": "Lorem ipsum",
  "icon_assets": [
    {"library":"lucide","name":"sparkles","x":0.5,"y":0.28,
     "size":0.17,"color":"accent"},
    {"library":"heroicons","name":"bolt","style":"solid",
     "x":0.24,"y":0.72,"size":0.12,"color":"#FFFFFF"}
  ]
}
```

Each node participates in the same scene graph and render path as other
elements. The icon cache does not need an internet connection after its first
download. To pre-provision a closed build, run a scene inspection or test render
once on a networked machine and preserve the icon cache in the build image.

## Safety and reproducibility

- Fixed Lucide release: `0.468.0` (ISC).
- Fixed Heroicons release: `v2.2.0` (MIT).
- Lowercase icon slugs only; paths and arbitrary remote URLs are forbidden.
- SVG parsing refuses scripts, styles, external references and XML entities.
- Only approved geometric SVG elements are passed to CairoSVG.
- Unknown names and unavailable icon downloads fail visibly (no silent fake icon).
- Icons do not change the former built-in visual presets unless opted in.
- Keep upstream license notices when redistributing SVG sources:
  [Lucide](https://github.com/lucide-icons/lucide/blob/main/LICENSE),
  [Heroicons](https://github.com/tailwindlabs/heroicons/blob/master/LICENSE).
