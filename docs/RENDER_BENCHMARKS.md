# Renderer benchmarks

Run the synthetic benchmark from the repository root after installing the
project and ensuring FFmpeg/FFprobe are available:

```sh
.venv/bin/python tools/benchmark_renderers.py --runs 3
.venv/bin/python tools/benchmark_renderers.py --runs 5 --output /tmp/reels-render-benchmark.json
```

The benchmark covers three routes: classic rendering with legacy title cards,
classic rendering with Studio title overlays, and full Studio scenes including a
vector chart. It generates its video and audio fixtures locally, so it does not
need brand assets, Git LFS media, network access, or provider credentials.

For every route it records cold and warm wall time, renderer stage timings, cache
hits/misses, and a warm/cold speedup estimate. It also checks MP4 dimensions,
frame rate, frame count, video/audio codecs, export-quality status, and exact
decoded-frame hashes between cold and warm outputs. Timing is reported rather
than used as a pass/fail threshold because shared CI machine load varies.

Compare reports only when the machine, Python version, FFmpeg build, fixture,
and run count match. This is a synthetic baseline for renderer code paths; it is
not a substitute for an opt-in benchmark with representative production footage.
The latter remains separate because it requires owner-approved real media.
