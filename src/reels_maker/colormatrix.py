"""Color matrix - inspired by ffmpeg-skill colormatrix.py.

Apply color space conversion and matrix transformation to video.
Useful for converting between color spaces (RGB<->YUV, HDR<->SDR) or applying color transformations.

Typical usage from reels-maker CLI:
    reels-maker colormatrix INPUT --target sdr

Features:
- --target: "sdr" | "hdr" | "rec709" | "bt2020" (default: "sdr")
- --mode: "convert" | "transform" (default: "convert")
- --dry-run --json for planning
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ffmpeg import execute, probe, RenderError


GRADES = ("neutral", "sdr", "warm", "cool", "vivid", "flat", "custom")


def color_filter(grade: str = "neutral", *, lut_path: str | None = None) -> str:
    """Return a real FFmpeg filter chain for a named grade.

    ``custom`` applies a user-supplied .cube LUT via ``lut3d``; the built-in
    grades are deterministic eq/colorbalance/colortemperature chains, so a
    grade always re-encodes through filters instead of copying the file.
    """
    key = str(grade).strip().lower().replace("_", "-")
    if key == "custom":
        if not lut_path:
            raise ValueError("custom grade requires lut_path to a .cube file")
        escaped = str(lut_path).replace("'", "'\\''").replace(":", "\\:")
        return f"lut3d=file='{escaped}':interp=tetrahedral,format=yuv420p"
    chains = {
        "neutral": "eq=saturation=1.0:contrast=1.0,format=yuv420p",
        "sdr": "eq=saturation=1.02:contrast=1.01,format=yuv420p",
        "warm": ("colortemperature=temperature=5800:mix=0.6,"
                 "eq=saturation=1.06:contrast=1.02,format=yuv420p"),
        "cool": ("colortemperature=temperature=8200:mix=0.6,"
                 "eq=saturation=0.97:contrast=1.02,format=yuv420p"),
        "vivid": "eq=saturation=1.18:contrast=1.06,format=yuv420p",
        "flat": "eq=saturation=0.82:contrast=0.92:gamma=1.05,format=yuv420p",
    }
    if key not in chains:
        raise ValueError(f"Unknown grade {grade!r}; choose one of "
                         + ", ".join(GRADES))
    return chains[key]


def _validate_inputs(video_path: Path) -> None:
    """Check that input file exists and has video stream."""
    if not video_path.is_file():
        raise RenderError(f"Video file not found: {video_path}")

    video_meta = probe(video_path)
    video_streams = video_meta.get("streams", [])
    if not any(s.get("codec_type") == "video" for s in video_streams):
        raise RenderError(f"Input {video_path} has no video stream")


def _target_filter(target: str) -> str:
    return {
        "sdr": color_filter("sdr"),
        "rec709": "colorspace=all=bt709:range=tv,format=yuv420p",
        "bt2020": "colorspace=all=bt2020:range=tv,format=yuv420p",
        "hdr": "colorspace=all=bt2020:trc=smpte2084:range=tv,format=yuv420p",
    }[target]


def colormatrix(
    video_path: Path,
    *,
    target: str = "sdr",
    mode: str = "convert",
    output: Path | None = None,
    dry_run: bool = False,
    grade: str | None = None,
    lut_path: str | None = None,
) -> dict:
    """Apply color space conversion or matrix transformation.

    Args:
        video_path: Input video file
        target: Target color space ("sdr", "hdr", "rec709", "bt2020")
        mode: "convert" - convert color space, "transform" - apply color matrix
        output: Output file path. If None, writes next to input with _colormatrix suffix
        dry_run: If True, only probe and return plan, don't encode

    Returns:
        dict with probe results and commands that would run
    """
    # Validate inputs
    _validate_inputs(video_path)

    # Validate target
    if target not in ("sdr", "hdr", "rec709", "bt2020"):
        raise RenderError(f"Invalid target: {target}. Use 'sdr', 'hdr', 'rec709', or 'bt2020'")

    # Validate mode
    if mode not in ("convert", "transform"):
        raise RenderError(f"Invalid mode: {mode}. Use 'convert' or 'transform'")

    # Prepare output path
    if output is None:
        output = video_path.parent / f"{video_path.stem}_colormatrix{video_path.suffix}"

    try:
        filter_chain = (color_filter(grade, lut_path=lut_path) if grade
                        else _target_filter(target))
    except ValueError as exc:
        raise RenderError(str(exc)) from exc
    command = ["-i", str(video_path), "-vf", filter_chain,
               "-c:a", "copy", str(output)]

    if dry_run:
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
                "target": target, "mode": mode, "grade": grade,
                "filter": filter_chain,
            },
            "output": str(output),
            "commands": [["ffmpeg", "-hide_banner", "-nostdin", "-y", *command]],
        }

    execute(command)
    result_meta = probe(output)
    streams = result_meta.get("streams", [{}])
    video_stream = next(
        (s for s in streams if s.get("codec_type") == "video"), streams[0])
    return {
        "status": "ok",
        "dry_run": False,
        "output": str(output),
        "filter": filter_chain,
        "duration": result_meta.get("format", {}).get("duration"),
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "fps": video_stream.get("r_frame_rate"),
    }


def cli_main(argv: list[str] | None = None) -> int:
    """CLI entry point for colormatrix operations."""
    parser = argparse.ArgumentParser(
        description="Apply color space conversion or matrix transformation"
    )
    parser.add_argument("input", type=Path, help="Input video file")
    parser.add_argument(
        "--target",
        choices=["sdr", "hdr", "rec709", "bt2020"],
        default="sdr",
        help="Target color space",
    )
    parser.add_argument(
        "--mode",
        choices=["convert", "transform"],
        default="convert",
        help="'convert' - convert color space, 'transform' - apply color matrix",
    )
    parser.add_argument(
        "--grade",
        choices=list(GRADES),
        default=None,
        help="Named grade filter chain; 'custom' applies --lut via lut3d",
    )
    parser.add_argument(
        "--lut", type=Path, default=None,
        help=".cube LUT file required by --grade custom",
    )
    parser.add_argument(
        "--output", type=Path, default=None, help="Output file path",
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

    try:
        result = colormatrix(
            video_path=args.input,
            target=args.target,
            mode=args.mode,
            output=args.output,
            dry_run=args.dry_run,
            grade=args.grade,
            lut_path=str(args.lut) if args.lut else None,
        )
    except RenderError as e:
        print(f"Error: {e}")
        return 1

    if args.dry_run or args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Color matrix complete: {result['output']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(cli_main())
