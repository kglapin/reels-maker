#!/usr/bin/env python3
"""Prepare an approved paper-tear capture as chroma-keyed RGBA frames.

The repository never stores third-party footage. This tool keeps the source and
its derivative frames inside the brand's ignored ``imports/`` quarantine, writes
a provenance record next to them, and requires an explicit rights statement
from the operator before any download happens.

Example:
    python tools/prepare_paper_tear_footage.py \
        --brand paper-studio --source-youtube EQNIm_LSbFo \
        --start 3.64 --duration 1.6 \
        --rights-note "Owner confirmed reuse for the paper-tear demo, <date>."

Then point a ``paper_reveal`` scene at ``imports/<name>/keyed``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(command: list[str], *, capture: bool = False) -> str:
    result = subprocess.run(command, check=True, text=True,
                            capture_output=capture)
    return result.stdout if capture else ""


def _download(url: str, target: Path) -> Path:
    existing = target / "source.webm"
    if existing.is_file():
        return existing
    if shutil.which("yt-dlp"):
        tool = ["yt-dlp"]
    else:
        tool = [sys.executable, "-m", "yt_dlp"]
    _run(tool + ["--js-runtimes", "node", "-f", "bv*+ba/b", "--no-playlist",
                 "-o", str(target / "source.%(ext)s"), url])
    downloaded = next(target.glob("source.*"), None)
    if downloaded is None:
        raise SystemExit("Download produced no file; see the yt-dlp output")
    return downloaded


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brand", required=True)
    parser.add_argument("--source-youtube", help="YouTube video id or URL")
    parser.add_argument("--source-file", type=Path,
                        help="Already-downloaded local capture")
    parser.add_argument("--name", default="paper-tear")
    parser.add_argument("--start", type=float, required=True,
                        help="Seconds where the sheet is still closed")
    parser.add_argument("--duration", type=float, default=1.6)
    parser.add_argument("--key-color", default="#3E8102",
                        help="Sampled green screen colour")
    parser.add_argument("--similarity", type=float, default=0.22)
    parser.add_argument("--blend", type=float, default=0.08)
    parser.add_argument("--rights-note", required=True,
                        help="Who authorised reuse of this capture, and when")
    args = parser.parse_args()

    brand_root = (ROOT / "brands" / args.brand).resolve()
    if not brand_root.is_dir():
        raise SystemExit(f"Unknown brand directory: {brand_root}")
    target = (brand_root / "imports" / args.name).resolve()
    if brand_root / "imports" not in target.parents:
        raise SystemExit("Refusing to write outside the brand imports quarantine")
    target.mkdir(parents=True, exist_ok=True)

    if args.source_file:
        source = args.source_file.resolve()
    elif args.source_youtube:
        url = (args.source_youtube if args.source_youtube.startswith("http")
               else f"https://www.youtube.com/watch?v={args.source_youtube}")
        source = _download(url, target)
    else:
        raise SystemExit("Provide --source-youtube or --source-file")

    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    keyed = target / "keyed"
    if keyed.is_dir():
        for stale in keyed.glob("f_*.png"):
            stale.unlink()
    keyed.mkdir(exist_ok=True)
    _run(["ffmpeg", "-v", "error", "-i", str(source), "-ss", str(args.start),
          "-t", str(args.duration), "-vf",
          f"colorkey={args.key_color}:{args.similarity}:{args.blend},format=rgba",
          "-vsync", "0", str(keyed / "f_%04d.png"), "-y"])

    frames = sorted(keyed.glob("f_*.png"))
    if len(frames) < 2:
        raise SystemExit("Keying produced fewer than two frames; check --start")
    provenance = {
        "schema_version": 1,
        "kind": "captured-paper-tear",
        "brand": args.brand,
        "source_url": (f"https://www.youtube.com/watch?v={args.source_youtube}"
                       if args.source_youtube else None),
        "source_file": source.name,
        "source_sha256": digest,
        "keyed_directory": str(keyed.relative_to(ROOT)),
        "frames": len(frames),
        "capture_window": {"start": args.start, "duration": args.duration},
        "chroma_key": {"color": args.key_color,
                       "similarity": args.similarity, "blend": args.blend},
        "rights_note": args.rights_note,
        "recorded": date.today().isoformat(),
        "delivery_ready": False,
        "review_note": ("Quarantine material: keep out of git and out of "
                        "publication until the rights record is reviewed."),
    }
    (target / "provenance.json").write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(json.dumps({"status": "ok", "keyed": str(keyed),
                      "frames": len(frames),
                      "provenance": str(target / "provenance.json")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
