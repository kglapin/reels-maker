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
