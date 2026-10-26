#!/usr/bin/env python3
"""Repeatable, media-independent benchmarks for both rendering backends.

Run from the repository root after installing the project:
    .venv/bin/python tools/benchmark_renderers.py --runs 3

The benchmark reports timings instead of enforcing a machine-dependent time
threshold. It does enforce output metadata, cache behavior and decoded-frame
parity between cold and warm renders for each route.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from reels_maker.renderers.backend import BackendOptions, render_with_backend
from reels_maker.spec import load_project
from reels_maker.studio import load_studio


def _run(command: list[str], *, text: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, capture_output=True, text=text)


def _create_fixtures(root: Path) -> tuple[Path, Path, Path]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required for renderer benchmarks")
    source = root / "synthetic-source.mp4"
    tone = root / "synthetic-tone.wav"
    _run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=360x640:rate=20",
        "-t", "3", "-an", "-c:v", "libx264", "-preset", "ultrafast",
        "-crf", "22", "-pix_fmt", "yuv420p", str(source),
    ])
    _run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-ac", "2", "-ar", "48000", str(tone),
    ])

    legacy_manifest = root / "legacy-project.json"
    legacy_manifest.write_text(json.dumps({
        "name": "Synthetic renderer benchmark",
        "video": {"width": 360, "height": 640, "fps": 20},
        "scenes": [
            {"file": source.name, "duration": 1.5,
             "title": {"kicker": "BENCH", "headline": "ENERGIA",
                       "body": "Synthetic video title render"}},
            {"file": source.name, "start": 1.5, "duration": 1.5,
             "title": {"headline": "RENDER TEST", "body": "Second scene"}},
        ],
        "music": {"file": tone.name, "volume": 0.1, "fade_out": 0.25},
        "output": "legacy-output.mp4",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    studio_manifest = root / "studio-project.json"
    studio_manifest.write_text(json.dumps({
        "name": "Synthetic Studio benchmark",
        "video": {"width": 360, "height": 640, "fps": 20},
        "export": {"codec": "libx264", "crf": 26, "preset": "ultrafast"},
        "audio": {"music": {"file": tone.name, "volume": 0.1,
                              "fade_out": 0.25, "ducking": "off"}},
        "scenes": [
            {"type": "statement", "duration": 1.0,
             "headline": "SYNTHETIC MOTION", "subtitle": "Studio render"},
            {"type": "amount", "duration": 1.0, "value": 15600,
             "visual": "none", "kicker": "TEST", "subtitle": "SCENE GRAPH"},
            {"type": "line_chart", "duration": 1.0,
             "headline": "DATA MOTION", "x_axis_type": "date",
             "x_axis_label": "Dzień", "y_axis_label": "Energia (kWh)",
             "y_domain": [0, 100],
             "points": [{"label": "2026-01-01", "value": 24},
                        {"label": "2026-01-02", "value": 68},
                        {"label": "2026-01-03", "value": 51}]},
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return legacy_manifest, studio_manifest, source


def _probe(path: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("FFprobe is required for renderer benchmarks")
    result = _run([
        ffprobe, "-v", "error", "-show_entries",
        "stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames",
        "-of", "json", str(path),
    ], text=True)
    return json.loads(result.stdout)


def _decoded_frame_hashes(path: Path) -> list[str]:
    ffmpeg = shutil.which("ffmpeg")
    result = _run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-map", "0:v:0", "-f", "framemd5", "-",
    ], text=True)
    hashes = [line.rsplit(",", 1)[-1].strip()
              for line in result.stdout.splitlines()
              if line and not line.startswith("#")]
    if not hashes:
        raise RuntimeError(f"No decodable video frames found in {path}")
    return hashes


def _validate_output(report: dict[str, Any], path: Path,
                     expected_frames: int) -> dict[str, Any]:
    if not report.get("ok"):
        raise RuntimeError(f"Renderer reported failure: {report}")
    quality = report.get("export_quality", {})
    if quality.get("status") != "pass":
        raise RuntimeError(f"Export quality check failed: {quality}")
    metadata = _probe(path)
    streams = metadata.get("streams", [])
    video = next((stream for stream in streams
                  if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams
                  if stream.get("codec_type") == "audio"), None)
    if video is None:
        raise RuntimeError("Benchmark output has no video stream")
    if (video.get("width"), video.get("height")) != (360, 640):
        raise RuntimeError(f"Unexpected output dimensions: {video}")
    if video.get("r_frame_rate") != "20/1":
        raise RuntimeError(f"Unexpected output frame rate: {video}")
    frame_hashes = _decoded_frame_hashes(path)
    if len(frame_hashes) != expected_frames:
        raise RuntimeError(
            f"Expected {expected_frames} frames, decoded {len(frame_hashes)}")
    if audio is None or audio.get("codec_name") != "aac":
        raise RuntimeError("Benchmark output must contain an AAC audio stream")
    return {"video_codec": video.get("codec_name"),
            "width": video.get("width"), "height": video.get("height"),
            "fps": video.get("r_frame_rate"), "frames": len(frame_hashes),
            "audio_codec": audio.get("codec_name"),
            "decoded_frame_hashes": frame_hashes}


def _median(samples: list[float]) -> float:
    return round(statistics.median(samples), 6)


def _benchmark_case(name: str, backend: str, project: Any, *,
                    cache_dir: Path, output: Path, runs: int,
                    backend_options: dict[str, Any], expected_frames: int) -> dict:
    cold_samples = []
    cold_reports = []
    stable_hashes = None
    for _ in range(runs):
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
        started = time.perf_counter()
        report = render_with_backend(
            backend, project,
            BackendOptions(output=output, cache_dir=cache_dir,
                           **backend_options))
        elapsed = time.perf_counter() - started
        quality = _validate_output(report, output, expected_frames)
        if quality["decoded_frame_hashes"] != stable_hashes and stable_hashes is not None:
            raise RuntimeError(f"Cold output for {name} changed decoded pixels")
        stable_hashes = quality["decoded_frame_hashes"]
        cold_samples.append(elapsed)
        cold_reports.append(report)

    cold_cache_misses = cold_reports[-1].get("cache_misses")
    if not cold_cache_misses:
        raise RuntimeError(f"Cold render for {name} did not encode any scenes")

    warm_samples = []
    warm_reports = []
    for _ in range(runs):
        started = time.perf_counter()
        report = render_with_backend(
            backend, project,
            BackendOptions(output=output, cache_dir=cache_dir,
                           **backend_options))
        elapsed = time.perf_counter() - started
        quality = _validate_output(report, output, expected_frames)
        if quality["decoded_frame_hashes"] != stable_hashes:
            raise RuntimeError(f"Warm output for {name} changed decoded pixels")
        if report.get("cache_misses") != 0:
            raise RuntimeError(f"Warm render for {name} encoded uncached scenes")
        warm_samples.append(elapsed)
        warm_reports.append(report)

    cold_median = _median(cold_samples)
    warm_median = _median(warm_samples)
    return {
        "case": name,
        "backend": backend,
        "runs_per_cache_state": runs,
        "cold_seconds": cold_median,
        "warm_seconds": warm_median,
        "warm_speedup_x": round(cold_median / warm_median, 3)
        if warm_median else None,
        "warm_time_reduction_percent": round(
            (1 - warm_median / cold_median) * 100, 2)
        if cold_median else None,
        "cache_hits_cold": cold_reports[-1].get("cache_hits"),
        "cache_misses_cold": cold_cache_misses,
        "cache_hits_warm": warm_reports[-1].get("cache_hits"),
        "cache_misses_warm": warm_reports[-1].get("cache_misses"),
        "cold_stage_timings_seconds": cold_reports[-1].get("timings_seconds", {}),
        "warm_stage_timings_seconds": warm_reports[-1].get("timings_seconds", {}),
        "output": {key: value for key, value in _validate_output(
            warm_reports[-1], output, expected_frames).items()
            if key != "decoded_frame_hashes"},
        "cold_warm_frame_parity": "exact decoded-frame hash match",
    }


def run_benchmarks(runs: int = 3) -> dict[str, Any]:
    if not 1 <= runs <= 10:
        raise ValueError("--runs must be between 1 and 10")
    with tempfile.TemporaryDirectory(prefix="reels-maker-benchmark-") as temp:
        root = Path(temp)
        legacy_manifest, studio_manifest, _ = _create_fixtures(root)
        legacy_project = load_project(legacy_manifest)
        studio_project = load_studio(studio_manifest, root=root, profile="preview")
        cases = [
            ("classic-legacy-titles", "legacy", legacy_project,
             {"root": root, "title_engine": "legacy"}, 60),
            ("classic-studio-title-overlay", "legacy", legacy_project,
             {"root": root, "title_engine": "studio"}, 60),
            ("studio-scenes-and-chart", "studio", studio_project, {}, 60),
        ]
        results = []
        for name, backend, project, options, expected_frames in cases:
            results.append(_benchmark_case(
                name, backend, project,
                cache_dir=root / "cache" / name,
                output=root / "outputs" / f"{name}.mp4",
                runs=runs, backend_options=options,
                expected_frames=expected_frames))
        ffmpeg = subprocess.run(["ffmpeg", "-version"], check=True,
                                capture_output=True, text=True).stdout.splitlines()[0]
        return {
            "schema_version": 1,
            "kind": "synthetic-renderer-benchmark",
            "environment": {"python": sys.version.split()[0],
                            "platform": platform.platform(),
                            "ffmpeg": ffmpeg},
            "fixture": {"source": "FFmpeg testsrc2 + generated sine tone",
                        "dimensions": "360x640", "fps": 20,
                        "frames_per_case": 60, "duration_seconds": 3.0},
            "cases": results,
            "interpretation": (
                "Use timing values only to compare runs on the same machine "
                "and FFmpeg build. Cold/warm frame parity and export metadata "
                "are enforced; timing thresholds are intentionally not."),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3,
                        help="Independent cold renders and subsequent warm renders (1..10)")
    parser.add_argument("--output", type=Path,
                        help="Optional JSON report path")
    args = parser.parse_args(argv)
    try:
        report = run_benchmarks(args.runs)
        rendered = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
