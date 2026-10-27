#!/usr/bin/env python3
"""Render and losslessly concatenate the synthetic five-minute Motion Lab demo.

Each section is rendered by the existing Studio backend. The final assembly
uses the same stream-copy segment-assembly helper as the product renderers.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from reels_maker.ffmpeg import RenderError
from reels_maker.qa.report import audit
from reels_maker.renderers.camera_canvas import CameraCanvasRenderer
from reels_maker.renderers.scene import RenderOptions, SceneRenderer
from reels_maker.renderers.studio import render_studio
from reels_maker.renderers.studio_output import probe_output
from reels_maker.segment_assembly import join_segments
from reels_maker.studio import load_studio


ROOT = Path(__file__).resolve().parents[1]
BRAND_ROOT = ROOT / "brands" / "motion-lab"
PROJECTS = BRAND_ROOT / "projects"
OUTPUT_DIR = ROOT / "renders" / "motion-lab"
MANIFESTS = (
    PROJECTS / "studio-showcase-280s.json",
    PROJECTS / "camera-canvas-showcase-20s.json",
)
EXPECTED_WIDTH, EXPECTED_HEIGHT, EXPECTED_FPS = 720, 1280, 30
EXPECTED_FRAMES = 300 * EXPECTED_FPS


def render_demo(output: Path = OUTPUT_DIR / "motion-lab-showcase-5m.mp4") -> dict:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    segment_dir = output.parent / "segments"
    segment_dir.mkdir(parents=True, exist_ok=True)
    segment_reports = []
    segments = []
    for manifest in MANIFESTS:
        project = load_studio(manifest, root=ROOT, profile="review")
        timeline = project.timeline()
        built = project.build(timeline)
        if any("camera_canvas" in scene for scene in project.scenes):
            qa_renderer = CameraCanvasRenderer(project)
        else:
            qa_renderer = SceneRenderer(
                project.width, project.height, project.tokens, project.fonts,
                options=RenderOptions(supersample=1))
        qa = audit(project, built, timeline, renderer=qa_renderer,
                   samples_per_scene=6, strict=True)
        if not qa["ok"]:
            errors = [issue for issue in qa["issues"]
                      if issue["severity"] == "error"]
            raise RenderError(
                f"Strict QA blocked {manifest.name}: {errors[:10]}")
        segment = segment_dir / f"{project.name}.mp4"
        report = render_studio(
            project, output=segment, profile="review", supersample=1)
        if report.get("export_quality", {}).get("status") != "pass":
            raise RenderError(
                f"Export quality verification failed: {manifest.name}")
        segments.append(segment)
        segment_reports.append({
            "manifest": str(manifest.relative_to(ROOT)),
            "segment": str(segment),
            "duration_seconds": timeline.duration,
            "frames": timeline.total_frames,
            "qa_errors": qa["summary"]["errors"],
            "qa_warnings": qa["summary"]["warnings"],
            "render_seconds": report["render_seconds"],
            "cache_hits": report["cache_hits"],
            "cache_misses": report["cache_misses"],
        })
    with tempfile.TemporaryDirectory(prefix="motion-lab-demo-join-",
                                     dir=output.parent) as temp:
        scratch = Path(temp)
        join_segments(segments, output, scratch, max_frames=EXPECTED_FRAMES)

    probe = probe_output(output)
    actual = (probe["width"], probe["height"],
              float(probe["fps"].split("/")[0]) /
              float(probe["fps"].split("/")[1]), probe["frames"])
    expected = (EXPECTED_WIDTH, EXPECTED_HEIGHT,
                float(EXPECTED_FPS), EXPECTED_FRAMES)
    if actual != expected:
        raise RenderError(f"Final demo output metadata mismatch: {actual} != {expected}")
    return {
        "schema_version": 1,
        "status": "ok",
        "ok": True,
        "output": str(output),
        "duration_seconds": probe["duration"],
        "frames": probe["frames"],
        "width": probe["width"],
        "height": probe["height"],
        "fps": probe["fps"],
        "video_codec": probe["codec"],
        "audio_streams": probe["audio_streams"],
        "synthetic_media_only": True,
        "human_review_required": True,
        "segments": segment_reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=OUTPUT_DIR / "motion-lab-showcase-5m.mp4")
    args = parser.parse_args()
    report = render_demo(args.output)
    sidecar = args.output.with_suffix(".report.json")
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
