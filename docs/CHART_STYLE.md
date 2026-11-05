# Studio chart visual system

Studio charts share the scene graph and frame renderer so marks, values and
transitions remain animatable and are checked by the existing geometry/data QA.
They do not embed a browser or introduce a web chart runtime.

## Visual grammar

The reusable implementation is in `src/reels_maker/components/chart_style.py`:

- one theme-aware inset plot card and a fine border;
- subdued grid lines, stronger but accessible axes and labels;
- a restrained categorical palette with the brand accent reserved for focus;
- direct values and rounded, deliberate marks rather than decorative effects.

Current adopters include ranked bars, line charts, 100%-stacked bars,
waterfalls, scatterplots and heatmaps. The design borrows general principles
from mature systems such as Observable Plot, Tremor and Datawrapper; it does
not copy their code, components or exact themes. `shadcn/ui` charts use React
and Recharts, so importing them directly would create a separate rendering path
and break the frame-level animation/QA contract.

New chart families should use the shared card/color/type helpers and keep data
encoding honest: zero baselines for magnitude bars, explicit domains/units,
stable category identities, exact final values, and only purposeful highlights.
Avoid tiny legends, unnecessary axes, gradients that imply another quantity,
3D decoration and invented annotations. Inspect full-resolution stills and
motion strips at phone scale; automated QA is not creative approval.

## Optional Matplotlib engine (`chart_engine: "mpl"`)

Scenes may opt into a raster chart engine backed by Matplotlib
(`pip install .[charts]`). It renders a deterministic PNG frame sequence per
scene (2x supersample, transparent background, content-hashed disk cache) and
injects it as a `sequence` node, so headlines, backgrounds, transitions and
audio stay on the native pipeline. Any failure — missing matplotlib, unknown
type, frame error — falls back to the native builders.

Supported types: `line_chart`, `bars`, `waterfall`, `bullet`, `heatmap`,
`funnel`, `diverging_bar`, `scatter`, `donut`, `stacked_bars_100`.
`table` and `chart_morph` remain native-only. Bump `_ENGINE_VERSION` in
`src/reels_maker/chart_mpl/engine.py` whenever drawer output changes so stale
cached frames are invalidated.

The engine uses the same visual grammar (plot card, muted grid, categorical
series palette, direct values) expressed through shared type-scale constants
(`FS_TICK/FS_LABEL/FS_VALUE/FS_MICRO`) and the Cartesian frame
(`PLOT_L/PLOT_R/PLOT_T/PLOT_B`). Keep new drawers consistent with those
constants; do not introduce per-scene pixel constants.

## Icons are a separate asset choice

Built-in vector icon primitives remain an offline fallback. To use upstream
SVG packs, scenes already support `icon_library` / `icon_assets` with pinned
Lucide, Heroicons, Tabler, Phosphor and Material Symbols variants. See
[`ICON_LIBRARIES.md`](ICON_LIBRARIES.md) for setup, cache, pinning and licenses.
They are opt-in because they require CairoSVG and the first uncached icon may
need network access; do not silently fetch/commit licensed assets or assume the
pack license approves a brand/trademark use.
