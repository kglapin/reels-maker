# Data Motion & Infographics Engine — Professional Specification

**Status: PLANNED expansion, not implemented in full.** Date: 2026-10-23. Companion to [PRO_MOTION_ROADMAP_2026.md](PRO_MOTION_ROADMAP_2026.md).

## 1. Business objective

Create reliable, high-end moving data stories for social video from factual numeric and tabular data. LLM supplies narrative questions and semantic intents. A Data Director chooses an appropriate visualization, Data Validator verifies the source and value rules, layout/animation engines render it across 9:16, 4:5, 1:1 and 16:9 formats; visual QA confirms mobile readability and semantic fidelity.

Sample scenarios: PV generation vs self-consumption, hourly heatmap of consumption, before/after bills, advertising campaign leads and CPL, CAC evolution, ROAS, conversion funnel, rankings by location, financial cash flow, comparisons of offers and process performance.

Today the source contains `build_bars`, `build_donut`, `build_stats`, and number/counter motion; these are **foundational limited layouts**. A full table renderer, automatic chart inference, data lineage, animated reshaping, data morphing, font-safe number motion and responsive progressive disclosure are **not yet equivalent fully implemented capabilities**. Never advertise them as available before tests.

## 2. Data integrity is a hard invariant

- Data is immutable: each animated output frame derives from validated typed source and declared transforms; animation interpolation must never alter the final reported observation.
- Validate: source URL/file/title, import time, measurement period/timezone, data type, actual sample size/denominator, base year, currency, unit, missing/null, negative and zero, duplications, outliers, sorting and normalization, rounding, percentage sum, aggregation type, uncertainty when known.
- No arbitrary fabricated bars, comparisons or text. Do not infer causation from correlation or infer missing numbers from screen height or design metadata.
- For columns, bars and areas using length/area to represent a magnitude, appropriate proportional encoding and zero baseline are default. Lines representing change over time can use a nonzero axis only when it is clear and not misleading; keep truthful labels.
- Direct labels should show final exact rounded values and units. Counters interpolate visual numbers but converge precisely to the validated source values and never present intermediate frames as measured history.
- Preserve totals when transitioning table <-> chart, or pivoting categories; reject transitions that silently lose categories.
- Highlight denominator, category granularity, chart units, source and reference date. If numbers are estimates, mark them as estimates.
- Render percentages with explicit rounding policy and check data-bound percentages at final state.
- Preserve units and locales: Polish decimal comma, thousands spaces, PLN, zł, kWh, kWp, t CO2, %, p.p.; distinguish percentages from percentage-point changes.
- No invented business outcomes, unverified client ROAS/CAC, fictitious precise energy returns or graphs falsely implying source credibility.

## 3. Visualization selection: question before chart type

Use editorial intent, dimensionality and domain. Categories follow FT Visual Vocabulary:

| Insight | Default forms | Alternatives | Notes |
|---|---|---|---|
| Magnitude / ranking | sorted horizontal bar | lollipop, dot plot | readable long labels, zero baseline for bar |
| Change over time | line chart | small multiples, columns | highlight changes/time endpoints |
| Deviation from target | diverging bar | bullet, slope | clear reference line |
| Part-to-whole | 100% stacked bar | donut for few sectors | avoid excessive tiny slices |
| Flow / conversion | funnel | Sankey for branching | preserve totals and missing branches |
| Distribution | histogram | dot/box | explain binning and spread |
| Correlation | scatterplot | bubble | no automatic causal claims |
| Matrix / time x category | heatmap | small multiples | clear continuous/discrete legends |
| Financial bridge | waterfall | running total line | signed values and cumulative audit |
| Multiple exact metrics | table | KPI cards, ranked comparison | table is best when exact lookup matters |
| Geographic differences | dot/bar by location | map when geospatial pattern relevant | appropriate rates for choropleths |
| Relationships / systems | flow, network diagram | annotated process | data versus illustrative diagram must be distinguished |

Chart selection requires an explainable record: audience question, chosen marks/encodings, rejected candidates, precision needs, source, domain and expected reading time.

## 4. Animated data grammar — real mechanisms, not identical fades

### 4.1 Bars and columns
- Axis and baseline first, then bar growth tied to validated value.
- Stagger categories by meaning, not automatically every bar.
- Sort/re-sort with stable object identity and smooth vertical reordering.
- Emphasize selected bar by color/opacity/callout, never misstate values by distortion.
- Stacked/100%-stacked bars animate portions while conserving totals.

### 4.2 Lines and time series
- Draw-on via actual data points and line interpolation; preserve plotted geometry.
- Callout events and annotate peaks/troughs.
- Optional cursor or vertical tracker reveals exact historical sample at real timestamps.
- Animated comparison years/series with matching time scales; never fabricate in-between historical points unless visibly marked as mathematical interpolation.
- Reveal axis units/times and stable reading hold.

### 4.3 Donut, pie and proportions
- Segment sweep starts from mathematically correct angular extent; labels track sectors without overlaps.
- Center value and total communicate real part-to-whole.
- Limit segments; prefer stacked bars for many categories; do not use perspective/3D pie distortion.
- Ensure value proportions sum with an explicit rounding strategy.

### 4.4 KPI, counters and financial metrics
- Number ticker, digit-place choreography, count-up / count-down, rolling counter, delta reveal and before/after substitution.
- Correct units, p.p. versus %, currency, date period and source.
- Never count through physically nonsensical states if numerical sequence could be mistaken for source observations; visual-only counter marked as reveal.
- Strong hold after number settles.

### 4.5 Tables / matrices (first-class objects)
- Typed table with column metadata, header groups, keys, sort, number format and semantic highlight.
- Auto-fit columns based on accurate font bounds and priority. Freeze/stick key dimensions logically in video; for a complex table use **progressive disclosure**, not tiny unreadable cells.
- Distinct effects: row reveal, column reveal, cell value-change, sort/reorder with stable ID, cross-highlight row/column, transform selected row into KPI or bar, filter categories, morph table -> chart -> table.
- Large tables: show only 3–7 semantically important rows per screen (calibrate to typography and duration); paginate/split into multiple beats preserving headers, scale and context. Original full data remains available as a report/CSV and is not dropped from source.
- Grid lines minimal, zebra pattern optional and subtle. Prefer right-aligned numeric values with tabular numerals; units consistently in heading.
- Never animate sort by replacing numbers independently of category identity; row objects must persist across state changes.
- Table row-to-chart morph maintains category/value mapping and signed values.

### 4.6 Advanced
- Waterfall: build up/down from signed deltas with cumulative total check.
- Heatmap: reveal cells/row groups, stable legend and accessible perceptual color scale; show min/max and selective detail.
- Sankey: preserve flow conservation and label main pathways, show animated directional tracers without implying false dynamics.
- Scatter / bubble: preserve quantitative axes, rank by visual salience rather than arbitrary movement.
- Small multiples and dashboards: KPI reveal -> one main chart -> focused detail -> summary; never cram an entire desktop dashboard into a 9:16 frame.
- Animated maps only when rates, administrative boundaries and geography are accurate.
- Energy-specific diagrams: generation -> self-consumption -> storage -> grid; distinguish measured / estimated / simulation values and never depict physically impossible flows.

## 5. Data Motion DSL: semantic descriptions, not manual drawing

Creative Spec v2 must accept reusable data references and visualization intent:

```json
{
  "data_sources": [
    {"id":"energy-2026","kind":"csv","path":"assets/energy-2026.csv","timezone":"Europe/Warsaw"}
  ],
  "shots": [{
    "id":"consumption-trend",
    "intent":"explain_growth",
    "headline":"Zużycie energii",
    "data_visualization":{
      "source":"energy-2026",
      "question":"How did consumption change by month?",
      "form":"auto",
      "dimensions":{"x":"month","y":"kwh"},
      "units":{"y":"kWh"},
      "focus":{"highlight":"last_observation"},
      "motion":{"family":"progressive_line_reveal","after_camera_arrival":true},
      "footnote":"Dane za 2026"
    }
  }]
}
```

This is a **proposed future schema**, not currently supported by the Creative Spec v1 compiler. Requirements: strict JSON Schema, version migration, explainable plan, internal typed source references, no arbitrary Python execution or expressions from untrusted LLM output.

Interpreted pipeline:

```text
CSV / XLSX / validated JSON / authorized Sheets / API
    -> Data Import + Types + Provenance + Calculation Engine
    -> Data Director: question -> chart/table/layout candidates
    -> Semantic Chart Model: categories / series / axes / values / units
    -> Motion Choreographer with stable IDs
    -> Camera-safe Responsive Scene Graph
    -> Exact Frame Renderer (SVG/vector/raster/video)
    -> Data Integrity + Mobile Legibility QA
    -> MP4 + source ledger / data appendix
```

## 6. Rendering architecture

- Data Viz IR: `DataSource`, `DataFrameSnapshot`, `Field`, `Measure`, `Unit`, `Category`, `Scale`, `Axis`, `Mark`, `Legend`, `Annotation`, `Transition`.
- Static layout first, then animated numeric attributes. Frame `t` maps typed observations to visual primitives; golden frame equals valid terminal observation.
- Scene-wide coordinate transforms apply to entire chart/table groups. Text labels may be selectively camera-facing to remain legible.
- Chart marks have persistent IDs and are animated across sorted, filtered and reformatted states, not regenerated as unrelated objects.
- Where necessary, use segment-based animation: axis appears -> marks build -> callout -> hold -> exit. Avoid simultaneous data motion and camera rotation that prevents reading.
- Native SVG/Pillow/Skia/FFmpeg compositing can render chart primitives; D3/Observable Plot/Vega-Lite are useful references for chart selection/grammar and may be options for authoring, but don't require an always-on browser runtime in a Python renderer.
- Render full 1080x1920 quality and show real-screen previews.
- Precompute label widths and tick locations. Implement min label separation, annotation displacement, clipping masks, line simplification preserving significant events and collision checks.

## 7. Visual/accessibility/mobile rules

- First impression: one claim, one primary chart, one highlighted finding.
- Progressive disclosure: more detail comes after audience knows what to look for.
- Prefer directly labeled elements over distant legends; legend only if needed.
- Numerals must be optically aligned, with consistent format and locale.
- Use color plus labels, position or symbols; don't rely on red/green alone.
- Critical chart marks should meet minimum non-text contrast where applicable, and text labels need text contrast; see WCAG 1.4.11 and 1.4.3.
- Avoid low-contrast hairlines, excessive gridlines, 3D bars/pies, misleading truncation, gratuitous pie slices and overly rapid animations.
- Short social content: visually progressive summaries beat full small-text dashboards.
- Chart hold at the end must accommodate a real reading interval, calculated from chart category and text count, not a fixed 0.6 seconds.
- Camera motion stops before detailed labels enter, unless motion is essential to the story.
- Legends/sources must be visible long enough to establish context; full citations additionally in export metadata/companion text where appropriate.

## 8. Acceptance tests and golden showcase

Required datasets: positive/negative values, nulls, zero, duplicate keys, >100 rows, Polish decimals, nontrivial currency, percentages summing approximately/not exactly 100, denominator changes, unusual category widths, large and small scales, streaming/source changes and inaccurate input examples.

CI requirements:
- Values/totals remain invariant through interpolation, sorting and table/chart morph;
- No negative bar length for positive value, no sign inversion and no phantom point;
- 100% chart labels and key data within viewport/platform safe area at target frames;
- 100% verified unit/currency/percentage/period provenance; source shown or recorded;
- Color contrast checks on marks and text; color-blind-safe alternative encoding;
- Null/missing values visibly handled, not silently zero-filled;
- Mobile reading QA at true preview width and meaningful hold time;
- CI golden videos 9:16, 4:5, 1:1, 16:9 and Polish font regression;
- Video demo categories: marketing CPL by region; monthly revenue; PV/storage power flow; pre/post energy bill; table rank/reorder; table-to-chart morph; heatmap time-of-day; waterfall of costs; multi-year line; funnel conversion;
- Human review of narrative truth, aesthetics, legibility and motion coherence.

## 9. Implementation work packages

**Priority P0 — initial useful professional data clips**
- DM-001: typed data source loader for CSV/JSON/XLSX and authorized connector exports; schema/number/locale/rights provenance.
- DM-002: Data Integrity Validator, calculation ledger, deterministic aggregation, safe rounding and explicit units.
- DM-003: Data Director chart-selection/variant planning based on FT Visual Vocabulary; explainable rationale.
- DM-004: true vector bar/column, line/time-series, ordered ranking, counter and 100% stacked bar; axis/label system.
- DM-005: table scene graph + row IDs, column widths, alignment, right formatting, mobile progressive disclosure.
- DM-006: semantic animation choreography: grow, trace, reorder, comparison, row/cell highlights, number replacement.
- DM-007: camera-safe chart/table placement, real glyph bounding boxes, contrast QA, collision and reading hold tests.
- DM-008: 4 credible example videos with original datasets and signed art-director review.

**Priority P1 — advanced motion storytelling**
- DM-101: table -> chart transformation with shared object IDs and conservation checks.
- DM-102: waterfall, diverging/slope, bullet, heatmap, scatter and funnel.
- DM-103: Sankey/energy flows + animated process paths, total-conserving links.
- DM-104: chart scene morphs preserving marks/scales and staged axis transitions.
- DM-105: domain-aware presets for PV, finances, marketing, operations and sales.
- DM-106: data-aware narration/audio cue planning and camera choreography.
- DM-107: automatic three-way choice of visual storytelling variants; responsive animated layouts.
- DM-108: full regression suite and at least 10 types of approved golden data-motion reels.

**Priority P2 — optional**
- DM-201: scheduled live data snapshots with audit trail and historical comparisons.
- DM-202: advanced statistical/uncertainty animation and geographic maps.
- DM-203: editable dashboard/storyboard GUI; custom data annotations and user-directed focus.
- DM-204: truly spatial 3D data scenes only if they improve comprehension.

Dependencies: MD-201 shared Render Graph, MD-203 exact typography, MD-205 Layout Solver, MD-401 audio, MD-403 social safe-zone profiles, MD-404 QA and repair.

## 10. Verified design references (2026-10-23)

- FT Visual Vocabulary: https://github.com/Financial-Times/chart-doctor/blob/main/visual-vocabulary/README.md
- European Data Portal guide based on FT: https://data.europa.eu/apps/data-visualisation-guide/choosing-charts-the-message
- Datawrapper chart layout, annotations and mobile: https://www.datawrapper.de/academy/customizing-your-bar-chart
- Heer & Robertson, Animated Transitions in Statistical Data Graphics, IEEE TVCG (2007): https://idl.uw.edu/papers/animated-transitions
- WCAG 2.2 graphical objects non-text contrast: https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast
