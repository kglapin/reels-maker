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

## Icons are a separate asset choice

Built-in vector icon primitives remain an offline fallback. To use upstream
SVG packs, scenes already support `icon_library` / `icon_assets` with pinned
Lucide, Heroicons, Tabler, Phosphor and Material Symbols variants. See
[`ICON_LIBRARIES.md`](ICON_LIBRARIES.md) for setup, cache, pinning and licenses.
They are opt-in because they require CairoSVG and the first uncached icon may
need network access; do not silently fetch/commit licensed assets or assume the
pack license approves a brand/trademark use.
