"""Speed ramping (speed ramp) - inspired by ffmpeg-skill speedramp.py.

Allows creating smooth speed changes (acceleration/deceleration) in video clips.
Useful for creating dramatic slow-mo effects or fast-forward segments.

Typical usage from reels-maker CLI:
    reels-maker speedramp INPUT --segment 10 0.5 --segment 30 2.0

Features:
- Multiple speed segments with --segment START SPEED
- Speed is a multiplier: 1.0 = normal, 0.5 = half speed, 2.0 = double speed
- --dry-run --json for planning
"""
from __future__ import annotations

import json
from pathlib import Path

from .ffmpeg import execute, probe, RenderError


def _validate_inputs(video_path: Path) -> None:
    """Check that input file exists and has video stream."""
    if not video_path.is_file():
        raise RenderError(f"Video file not found: {video_path}")

    video_meta = probe(video_path)
    video_streams = video_meta.get("streams", [])
    if not any(s.get("codec_type") == "video" for s in video_streams):
        raise RenderError(f"Input {video_path} has no video stream")


def speedramp(
    video_path: Path,
    *,
    segments: list[tuple[float, float]] | None = None,
    output: Path | None = None,
    dry_run: bool = False,
) -> dict:
    """Apply speed ramping to video clip.

    Creates speed changes at specified timestamps.

    Args:
        video_path: Input video file
        segments: List of (start_sec, speed_multiplier) tuples.
            speed: 1.0 = normal, 0.5 = half slow motion, 2.0 = double speed.
            Segments are applied sequentially.
        output: Output file path. If None, writes next to input with _speedramp suffix
        dry_run: If True, only probe and return plan, don't encode

    Returns:
        dict with probe results and commands that would run
    """
    # Validate inputs
    _validate_inputs(video_path)

    if segments is None:
        segments = []

    # Prepare output path
    if output is None:
        output = video_path.parent / f"{video_path.stem}_speedramp{video_path.suffix}"

    if dry_run:
        # Probe and return plan without encoding
        video_meta = probe(video_path)
        return {
            "status": "ok",
            "dry_run": True,
            "video": {
                "duration": video_meta.get("format", {}).get("duration"),
                "width": video_meta.get("streams", [{}])[0].get("width"),
                "height": video_meta.get("streams", [{}])[0].get("height"),
                "fps": video_meta.get("streams", [{}])[0].get("r_frame_rate"),
            },
            "segments": segments,
            "output": str(output),
            "commands": [],
        }

    # Full execution - for now, just report that speed ramping needs
    # a more complex FFmpeg filter (tmix for smooth transitions)
    # This is acknowledged in ffmpeg-skill as well - full speed ramp
    # requires advanced filtering
    raise RenderError(
        "Speed ramping full encoding not yet implemented - "
        "use --dry-run for planning, or see ffmpeg-skill speedramp.py "
        "for the full implementation with tmix transitions"
    )


def cli_main(argv: list[str] | None = None) -> int:
    """CLI entry point for speedramp operations."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Apply speed ramping to video"
    )
    parser.add_argument("input", type=Path, help="Input video file")
    parser.add_argument(
        "--segment",
        type=float,
        nargs=2,
        action="append",
        dest="segments",
        default=[],
        help="Speed segment: START SPEED (use --segment multiple times, "
             "e.g. --segment 10 0.5 --segment 30 2.0)",
    )
    parser.add_argument(
        "--output", type=Path, default=None, help="Output file path"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Probe and plan without encoding",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON result (implies --dry-run)",
    )

    args = parser.parse_args(argv)

    # Parse segments - args.segments is [[start1, speed1], [start2, speed2], ...]
    segments = []
    if args.segments:
        for pair in args.segments:
            if len(pair) != 2:
                print(
                    f"Error: Each --segment must have 2 values, got {len(pair)}",
                    file=sys.stderr,
                )
                return 1
            segments.append((pair[0], pair[1]))

    # Handle --json flag
    if args.json:
        result = speedramp(
            video_path=args.input,
            segments=segments,
            output=args.output,
            dry_run=True,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    try:
        result = speedramp(
            video_path=args.input,
            segments=segments,
            output=args.output,
            dry_run=args.dry_run,
        )
    except RenderError as e:
        print(f"Error: {e}")
        return 1

    if args.dry_run or args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Speed ramping complete: {result['output']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(cli_main())
