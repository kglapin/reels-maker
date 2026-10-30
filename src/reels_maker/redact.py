"""Privacy censor/delogo - inspired by ffmpeg-skill redact.py.

Removes or censor a specified region of the video (e.g., logos, faces).
Supports delogo mode which is reliably available in FFmpeg.

Typical usage from reels-maker CLI:
    reels-maker redact INPUT --x 100 --y 100 --width 200 --height 200 --mode delogo

Features:
- --x, --y, --width, --height: region to censor
- --mode: delogo (removes/logo replacement) - reliably available
- --dry-run --json for planning
Note: True pixelation requires specific FFmpeg filter versions.
"""
from __future__ import annotations

import argparse
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


def redact(
    video_path: Path,
    *,
    x: float = 0,
    y: float = 0,
    width: float | None = None,
    height: float | None = None,
    mode: str = "delogo",
    output: Path | None = None,
    dry_run: bool = False,
) -> dict:
    """Apply privacy redaction/delogo to a video region.

    Removes or censor a specified rectangular region of the video.
    The 'delogo' mode is reliably available in FFmpeg.

    Args:
        video_path: Input video file
        x: X position (left) of region, 0 = left edge, 1 = right edge (relative)
        y: Y position (top) of region, 0 = top edge, 1 = bottom edge (relative)
        width: Width of region in pixels (or relative if 0-1 range)
        height: Height of region in pixels (or relative if 0-1 range)
        mode: "delogo" - remove/logo replacement (recommended)
        output: Output file path. If None, writes next to input with _redact suffix
        dry_run: If True, only probe and return plan, don't encode

    Returns:
        dict with probe results and commands that would run
    """
    # Validate inputs
    _validate_inputs(video_path)

    # Prepare output path
    if output is None:
        output = video_path.parent / f"{video_path.stem}_redact{video_path.suffix}"

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
            "parameters": {
                "x": x, "y": y, "width": width, "height": height, "mode": mode,
            },
            "output": str(output),
            "commands": [],
        }

    # Build FFmpeg filter complex for region redaction (delogo mode)
    # Get video dimensions for relative positioning
    video_meta = probe(video_path)
    video_width = float(video_meta.get("streams", [{}])[0].get("width", 0))
    video_height = float(video_meta.get("streams", [{}])[0].get("height", 0))

    # Convert relative positions to absolute if needed
    if x > 1:  # absolute position
        left = x
    else:  # relative position (0-1)
        left = x * video_width

    if y > 1:  # absolute position
        top = y
    else:  # relative position
        top = y * video_height

    if width is None or width <= 0:
        width = video_width - left
    if height is None or height <= 0:
        height = video_height - top

    # Build the filter complex for delogo mode
    # The delogo filter removes a rectangular region
    # Options: x, y, w, h, show (no 'mode' option in this FFmpeg version)
    filter_complex = (
        f"[0:v]delogo=x={left}:y={top}:w={width}:h={height}[vcrop];"
        f"[vcrop]format=yuv420p[v]"
    )

    cmd = [
        "-i", str(video_path),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(output),
    ]

    if dry_run:
        return {
            "status": "ok",
            "dry_run": True,
            "output": str(output),
            "filter_complex": filter_complex,
            "parameters": {"x": x, "y": y, "width": width, "height": height, "mode": mode},
        }

    # Execute
    try:
        execute(cmd, quiet=False)
    except RenderError as e:
        # Clean up partial output
        if output.is_file():
            output.unlink()
        raise

    # Return probe of result
    result_meta = probe(output)
    return {
        "status": "ok",
        "dry_run": False,
        "output": str(output),
        "duration": result_meta.get("format", {}).get("duration"),
        "width": result_meta.get("streams", [{}])[0].get("width"),
        "height": result_meta.get("streams", [{}])[0].get("height"),
        "fps": result_meta.get("streams", [{}])[0].get("r_frame_rate"),
    }


def cli_main(argv: list[str] | None = None) -> int:
    """CLI entry point for redact operations."""
    parser = argparse.ArgumentParser(
        description="Apply privacy redaction/delogo to video"
    )
    parser.add_argument("input", type=Path, help="Input video file")
    parser.add_argument("--x", type=float, default=0, help="X position of region (absolute pixels or 0-1 relative)")
    parser.add_argument("--y", type=float, default=0, help="Y position of region (absolute pixels or 0-1 relative)")
    parser.add_argument("--width", type=float, default=None, help="Width of region in pixels")
    parser.add_argument("--height", type=float, default=None, help="Height of region in pixels")
    parser.add_argument(
        "--mode",
        choices=["delogo"],
        default="delogo",
        help="Redaction mode: delogo (removes/logo replacement)",
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

    # Validate required parameters
    if args.width is None:
        print("Error: --width is required", file=sys.stderr)
        return 1
    if args.height is None:
        print("Error: --height is required", file=sys.stderr)
        return 1

    try:
        result = redact(
            video_path=args.input,
            x=args.x,
            y=args.y,
            width=args.width,
            height=args.height,
            mode=args.mode,
            output=args.output,
            dry_run=args.dry_run,
        )
    except RenderError as e:
        print(f"Error: {e}")
        return 1

    if args.dry_run or args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Redaction complete: {result['output']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(cli_main())
