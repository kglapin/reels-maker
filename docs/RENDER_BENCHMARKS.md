# Renderer benchmarks

Run the synthetic benchmark from the repository root after installing the
project and ensuring FFmpeg/FFprobe are available:

```sh
.venv/bin/python tools/benchmark_renderers.py --runs 3
.venv/bin/python tools/benchmark_renderers.py --profile final --runs 1
.venv/bin/python tools/benchmark_renderers.py --runs 5 --output .cache/reels-maker/benchmark-preview.json
```

The benchmark covers three routes: classic rendering with legacy title cards,
classic rendering with Studio title overlays, and full Studio scenes including a
vector chart and a time-varying video layer. It generates its video and audio
fixtures locally, so it does not need brand assets, Git LFS media, network
access, or provider credentials.

The default `preview` fixture is 360×640 at 20 fps; `--profile final` uses
1080×1920 at 30 fps. Both use synthetic moving images and generated audio, not
licensed or client footage. A final-profile run is more demanding and is useful
for detecting resolution-dependent costs.

For every route it records cold and warm wall time, renderer stage timings, cache
hits/misses, and a warm/cold speedup estimate. It also checks MP4 dimensions,
frame rate, frame count, video/audio codecs, export-quality status, and exact
decoded-frame hashes between cold and warm outputs. Timing is reported rather
than used as a pass/fail threshold because shared CI machine load varies.

Compare reports only when the machine, Python version, FFmpeg build, fixture,
and run count match. This is a synthetic baseline for renderer code paths; it is
not a substitute for an opt-in benchmark with representative production footage.
The latter remains separate because it requires owner-approved real media.

## Local final-profile stress smoke (2026-10-26)

On macOS 15.7.7 ARM64, Python 3.13.0 and FFmpeg 8.0.1,
`--profile final --runs 1` produced exact cold/warm decoded-frame hash parity
for all three routes at 1080×1920/30 fps. For the 3-second synthetic Studio
route (chart + video layer), cold render took 12.47 s and warm render 0.314 s;
the cold report attributed 10.75 s to frame rendering, 0.234 s to video decode
and 0.244 s to audio mux. This is a single-machine smoke measurement, not a
performance promise or a quality sign-off. Use `--runs 3` or more for a stable
comparison on the same environment.

The region-local supersampled transform path reduced the same pre-optimization
synthetic cold Studio measurement from 20.12 s to 12.47 s (about 38%). Decoded
MP4 frame hashes remain exact between cold and warm cache runs; the new
full-canvas-vs-local-layer parity test also checks pixel identity for scaled,
rotated text and vector nodes.

## Parallel jobs and hardware encode A/B (2026-11)

Measured locally (macOS, Python 3.13, FFmpeg 8.0.1) on a synthetic
360×640/20 fps Studio fixture with four scenes (statement, amount, cta,
checklist), cache disabled, supersample 1, 74 frames per render:

| Variant | Wall time |
|---|---:|
| `libx264`, `jobs=1` | 0.55 s |
| `libx264`, `jobs=4` | 0.27 s |
| `h264_videotoolbox`, `jobs=2` | 0.63 s |

Parallel scene encodes scale with scene count on this fixture (about 2× at
four jobs), which is why `studio-render` now defaults to `--jobs 2`.
Hardware encode was slower at preview size: frame rasterisation in Pillow,
not H.264 encoding, dominates there. Treat hardware encoders
(`export.codec`, or the render farm's `use_hardware_encoder=True`) as an
opt-in for encode-heavy finals, and re-measure on a representative manifest
before adopting them; these are single-run local numbers, not promises.

A related correctness constraint: the x264 thread count is intentionally
not tied to `--jobs`. Varying `-threads` between serial and parallel
renders changed decoded pixels and broke the parallel/serial frame-parity
test, so encoder settings stay constant and only scene concurrency varies.

## Scene-renderer reuse paths (2026-11)

`SceneRenderer` now reuses raster work at several levels, all verified
pixel-identical against the uncached paths:

- `BuiltScene.at()` memoizes settled subtrees: once every track on a top-level
  node has ended (and the subtree has no video/sequence/mesh3d or negative
  text), it is sampled once and shared by later frames instead of deep-copying
  and re-interpolating the whole graph per frame.
- `RenderOptions.reuse_node_sprites` rasterizes a settled node into a tile once
  and alpha-composites it on later frames (two sightings required, so
  one-off samples never pay the tile cost).
- `_draw_local_layer` renders transformed leaves **and tile-safe groups**
  (static leaf descendants only — no clip, reveal, media, shadows on rounds,
  animated descendants, or negative text) into a padded local tile instead of
  allocating and BICUBIC-resampling a full supersampled canvas.
- `_draw_negative_text` restricts glyph-mask inversion to the union ink
  bounding box rather than three full-canvas passes; measured ~11% faster on a
  720×1280 photo scene with negative headline at supersample 1
  (17.9 → 15.8 ms/frame).
- Per-render stat caching avoids repeated `path.stat()` calls for sequence
  frames, photo backgrounds and stills; image caches are bounded by decoded
  bytes (256/512 MB budgets) instead of entry counts.
- `render_studio(..., jobs=N)` / `studio-render --jobs N` encodes independent
  scene segments concurrently; each worker gets its own `SceneRenderer` with
  cache budgets scaled by `min(1, 4/jobs)` to bound memory.

Pixel-parity coverage lives in `tests/test_render_performance.py`
(`SettledFrameReuseTests`, `NodeSpriteReuseTests`, `LocalLayerParityTests`,
`GroupLocalLayerTests`, `NegativeTextCropTests`) and the exact-pixel golden
strips under `tests/fixtures/studio-golden/`.
