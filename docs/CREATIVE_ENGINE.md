# Reels Maker Creative Engine v1

**Status (2026-10-23): implemented in the main backend with an end-to-end Studio MP4 CI test.** This is a structured interpreter/scene director, not an embedded language model or an autonomous visual art director.

## Why this exists

Creative requests should specify *intent* rather than Pillow calls, easing functions or scene-graph coordinates. An LLM can read the live capability registry and emit a Creative Spec JSON. The Creative Engine validates it, chooses only implemented techniques, produces an executable Studio manifest and renders a real MP4.

```text
User brief (natural language)
       |
LLM with capability registry + JSON Schema
       |
Creative Spec v1  (versioned, structured intent)
       |
validator -> Scene Director -> candidate ranking -> compiler
       |
Studio manifest (camera_canvas OR conventional Studio)
       |
preflight + photo / timing / safe-area heuristics
       |
existing Studio renderer -> H.264 MP4 -> sampled contact sheet
       |
LLM reads report and suggests JSON Patch edits; repeat only as necessary
```

## Public CLI contract

```bash
reels-maker creative-capabilities --json
reels-maker creative-schema --json
reels-maker creative-validate examples/creative-engine-editorial-demo.json --json
reels-maker creative-compile examples/creative-engine-editorial-demo.json --json
reels-maker creative-render examples/creative-engine-editorial-demo.json \
  --output renders/creative-demo.mp4 --storyboard renders/creative-storyboard.png --json
```

Compiling writes a Studio JSON and a companion `.creative-report.json` file. It does **not** render; rendering performs the compile, QA and MP4 encode. CLI exits nonzero for invalid schemes, missing media, unsupported effects and blocking QA errors. Add `--strict` to refuse warnings as well as errors.

To edit a scene without hand-editing renderer files:

```json
[
  {"op":"replace", "path":"/shots/@workspace/headline", "value":"ZMIANA PERSPEKTYWY"},
  {"op":"add", "path":"/shots/@workspace/camera", "value":{"angle":115,"zoom":1.05}}
]
```

```bash
reels-maker creative-edit creative-spec.json edits.json \
  --output creative-spec-v2.json --json
reels-maker creative-render creative-spec-v2.json \
  --output renders/demo-v2.mp4 --json
```

The edit command applies operations to a **new** file, validates the complete result atomically, and does not overwrite the source. Paths can use zero-based array indices or stable shot IDs with `@shot-id`. Use `--force` only to intentionally replace an already existing output.

## Recommended LLM system instructions

> You are a Creative Spec author for Reels Maker. You receive a user's narrative brief, a machine-readable capabilities object and the JSON Schema for Creative Spec v1. Create **only a Creative Spec JSON object**, never Python code, direct video frames, an unsupported animation name or arbitrary backend configuration. Break the brief into meaningful scenes; retain text accuracy and user-supplied names/data. Prefer short, readable headlines and use different motion mechanisms when semantically appropriate. Select `camera_canvas` when the user wants one persistent world with camera pans, arbitrary angular stops and typography arriving after camera settle. Select `studio` for traditional independent shot compositions and object-driven transitions. Preserve the user's brand/palette. Reference only real local media paths returned from catalog or supplied by the user; never invent stock/photo file paths or claim licensing. Use `layout: auto` and `typography.family: auto` when uncertain, so the director can select implemented capabilities. Respect camera-safe margins and give each headline a sufficient hold interval. Emit a complete valid JSON object matching the published schema; do not include commentary within JSON.

The model is responsible for understanding the creative brief. The backend is responsible for deterministic compilation and technical validation; there is **no automatic LLM inference inside Reels Maker** in this version.

## Creative Spec structure

```json
{
  "creative_schema_version": 1,
  "name": "architektura-w-ruchu",
  "mode": "camera_canvas",
  "style": "editorial-premium",
  "video": {"width": 540, "height": 960, "fps": 24},
  "shots": [
    {
      "id": "intro",
      "intent": "opening",
      "headline": "NOWA PERSPEKTYWA",
      "subtitle": "Wspólne płótno, różne kadry.",
      "duration": 3.0,
      "asset": "assets/budynek.jpg",
      "layout": "auto",
      "typography": {"family": "auto"}
    },
    {
      "id": "transition",
      "intent": "reveal",
      "headline": "ZMIANA KĄTA",
      "subtitle": "Tekst pojawia się po zatrzymaniu kamery.",
      "duration": 3.2,
      "asset": "assets/biuro.jpg",
      "camera": {"angle": 76, "move_duration": 1.0},
      "layout": "auto",
      "typography": {"family": "auto"}
    }
  ]
}
```

Example filenames are illustrative only. Use actual accessible media before compiling.

## Machine-facing interface

- `creative-capabilities`: supported modes, families, transitions, layouts and clear limitations (not aspirational promises).
- `creative-schema`: versioned JSON Schema with field types, limits and enumerations. It is not the sole authority for mode-specific rules.
- `creative-validate`: strict procedural schema, asset existence and geometry/timing heuristics.
- `creative-compile`: deterministic director + Studio-compatible manifest + reasons for each decision.
- `creative-render`: Studio render and optional MP4-derived storyboard.
- `creative-edit`: validated, versioned, atomic JSON Patch subset (add, replace, remove).

The compiler rejects unsupported animation families rather than silently substituting simple fades for requested sophisticated effects.

## Director selection

For each shot, the director selects among multiple implemented layout candidates and records its reason. Ranking prioritizes hierarchy, legibility, subject retention, balance, continuity and brand. Typography selection uses semantic intent as the starting point and avoids repeating the same motion family in adjacent scenes, unless an explicit choice overrides it.

The selection criteria are **deterministic heuristics**, not machine learning or a claim that the winner is visually superior. An editor should inspect rendered MP4s to evaluate motion quality, emotional impact and narrative.

## New Camera Canvas mode

Media is mounted in persistent world coordinates. Camera stops have independent `x`, `y`, `angle`, `zoom` and easing duration. The director proposes irregular centers and angles; explicitly authored values take priority. The scene's typography is shown only after the camera settles. Its currently implemented families are:

- `fade`
- `slide-up`
- `mask-rise`
- `scale-focus`

The screen-space typography remains camera-facing at each settled stop, and earlier type remains mounted on the persistent world. This is not a precomputed slideshow rotation. Additional per-letter morphs, advanced motion blur, image-subject saliency masks and 3D camera trajectories remain future development.

## QA and regression

Creative QA checks file existence, image decodability, minimum photographic resolution, scene reading hold, excessive camera turn, zoom-based clipping risk, world memory budget, long headlines and animation repetition. Invalid Creative Specs cannot compile. CI runs unit tests for validator/compiler/editor, camera-canvas render tests and an actual MP4 with a contact sheet. Tests check H.264 video size and frame count.

**These checks do not guarantee world-class art direction.** Visual review of entry/mid-travel/settled frames remains required. Future improvements: real glyph-bound checks at all interpolated camera stops, saliency-aware photo cropping, candidates evaluated using actual rendered frames, automatic repair loops, audio-aware beat planning, and optional connected LLM orchestration.

## Existing Studio compatibility

New work should be authored through Creative Spec v1; legacy hand-authored Studio manifests are only an internal compilation target. Older public project formats are not a design constraint. Avoid deleting user-owned projects, media or previously approved deliveries unless they are known to be obsolete.

## References

- Source: `src/reels_maker/creative/`
- CLI: `src/reels_maker/cli.py`
- Tests: `tests/test_creative_engine.py`
- Demo: `examples/creative-engine-editorial-demo.json`
- CI: `.github/workflows/creative-engine-integration.yml`
- Camera backend: `src/reels_maker/renderers/camera_canvas.py`
