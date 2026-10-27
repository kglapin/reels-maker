# Icon libraries — pinned SVG packs

Native studio scenes can use real, upstream SVG assets instead of custom-drawn
primitive icons. Source packs are version-pinned; validated SVG files are cached
outside the repository and rasterizations are memoized during export.

## Installation

```bash
pip install -e '.[icons]'
```

cairosvg needs the system cairo library at render time. On Debian/Ubuntu it is
already present; on macOS install it with Homebrew:

```bash
brew install cairo
```

Rasterization auto-detects a Homebrew libcairo under `/opt/homebrew/lib` at
render time by appending it to `DYLD_FALLBACK_LIBRARY_PATH`. The fallback
loader only supplies libraries nothing else resolved, so bundled PIL font
libraries are never substituted. For a non-standard prefix, point
`DYLD_FALLBACK_LIBRARY_PATH` (or the environment) at it before launching.

If cairo still is not found, put only the cairo libraries on the
dynamic-loader path when running tests or renders locally. Pointing
`DYLD_LIBRARY_PATH` at the whole Homebrew `lib/`
directory makes the loader substitute Homebrew's freetype/fontconfig for the
system copies, which changes PIL font antialiasing and desynchronizes the
pixel-exact golden frames:

```bash
mkdir -p ~/.reels-maker/cairo-only
for f in /opt/homebrew/lib/libcairo*.dylib; do ln -sf "$f" ~/.reels-maker/cairo-only/; done
export DYLD_LIBRARY_PATH=~/.reels-maker/cairo-only
```

Without cairo available, the studio engine renders unchanged (icons are
opt-in), and the icon regression test skips itself.

No JavaScript runtime is needed. Python downloads original icons from their
pinned upstream tag/revision only when absent in the local cache
(`~/.cache/reels-maker/icon-libraries/`). Cached SVGs render offline.

## Supported packs and license records

| Pack | Pinned source | License | Styles |
|---|---|---|---|
| Lucide | `0.468.0` | ISC | `outline` |
| Heroicons | `v2.2.0` | MIT | `outline`, `solid` |
| Tabler | `v3.49.0` | MIT | `outline`, `filled` |
| Phosphor | `v2.0.8` | MIT | `thin`, `light`, `regular`, `bold`, `fill`, `duotone` |
| Material Symbols | Google repo commit `10ecc14790612ca8fd164e3f4ffe9c16fc50d5b7` | Apache-2.0 | `outlined`, `rounded`, `sharp` |

`icon_library.LICENSES` exposes each pack's license URL and notice requirement
for provenance/export tooling. A pack license does not grant trademark, brand,
or model/property rights to an individual icon use. When redistributing cached
SVGs, retain the upstream license notice. Tabler `brand-*` and Phosphor/Material
`*-logo*` glyphs are refused by default because the packs' general license does
not settle individual trademark rights. Lucide's notice records the potential
Feather-derived MIT notices as well as the pack-level ISC license.

`studio-render --json` includes a deduplicated `icon_provenance` array with the
pack/version/style, upstream file URL, license URL and cached SVG SHA-256.
`rights_status` remains `unknown` and the report records that item-level
trademark/brand review may still be required; this metadata is not an approval.

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

## Use icons as words in a gravity sequence

The reusable `gravity_words` scene can insert licensed library icons between
words. Each icon is a full sequence beat: it fades in, falls, rebounds under
the same gravity and restitution, and is centered by the same camera follow.
It uses the same `stagger` interval as the text, so every inserted icon shifts
the following words by one beat. Distinct insertion gaps come from the scene
seed and repeat across renders of the same manifest. See
[`MOTION_DESIGN_SYSTEM.md`](MOTION_DESIGN_SYSTEM.md#reusable-gravity-word-sequence-with-camera-follow)
for the complete `word_drop.icons` configuration.

Material Symbols names use the upstream namespace, e.g. `web/home`. Variant
fields are `icon_weight` (100, 200, 300, 400, 500, 600, 700), `icon_fill`
(boolean), `icon_grade` (-25, 0, 200) and `icon_optical_size` (20, 24, 40,
48). Defaults are weight 400, fill false, grade 0 and optical size 24;
unsupported combinations fail instead of choosing a nearby asset.

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

Icon nodes accept a restrained static `rotation` (±35°) or the existing
authored editorial `rotation_motion` choreography (not both). For Material
Symbols, individual `icon_assets` may override `weight`, `fill`, `grade` and
`optical_size`; these options are ignored by no pack silently—unsupported
pack/variant combinations fail with an error.

Each node participates in the same scene graph and render path as other
elements. The icon cache does not need an internet connection after its first
download. To pre-provision a closed build, run a scene inspection or test render
once on a networked machine and preserve the icon cache in the build image.

`icon_library.suggest_icons(query, libraries=..., limit=...)` returns at most
three deterministic candidates for a finite, reviewed semantic vocabulary. An
unknown concept returns an empty list; it does not generate an icon name or
download anything.

## Safety and reproducibility

- Fixed Lucide release: `0.468.0` (ISC).
- Fixed Heroicons release: `v2.2.0` (MIT).
- Fixed Tabler release: `v3.49.0` (MIT).
- Fixed Phosphor release: `v2.0.8` (MIT).
- Fixed Material Symbols source commit: `10ecc14790612ca8fd164e3f4ffe9c16fc50d5b7` (Apache-2.0).
- Lowercase icon slugs only; paths and arbitrary remote URLs are forbidden.
- SVG parsing refuses scripts, styles, external references and XML entities;
  files are capped at 100 KB, 512 elements and 256 paths.
- Only approved geometric SVG elements are passed to CairoSVG.
- Unknown names and unavailable icon downloads fail visibly (no silent fake icon).
- Icons do not change the former built-in visual presets unless opted in.
- Keep upstream license notices when redistributing SVG sources:
  [Lucide](https://github.com/lucide-icons/lucide/blob/main/LICENSE),
  [Heroicons](https://github.com/tailwindlabs/heroicons/blob/master/LICENSE).
