"""Extract temporary stills from the two reviewed CC0 carousel demo clips."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "photo-carousel-preview-assets"
SOURCES = [
    ("brands/asta-energy/media/stock/agrivoltaics_heggelbach_01.webm",
     "farm-01-1.jpg", 1.0),
    ("brands/asta-energy/media/stock/agrivoltaics_heggelbach_01.webm",
     "farm-01-3.jpg", 3.0),
    ("brands/asta-energy/media/stock/agrivoltaics_heggelbach_05.webm",
     "farm-05-1.jpg", 1.0),
    ("brands/asta-energy/media/stock/agrivoltaics_heggelbach_05.webm",
     "farm-05-2.jpg", 2.0),
    ("brands/asta-energy/media/stock/agrivoltaics_heggelbach_05.webm",
     "farm-05-4.jpg", 4.0),
]
ATTRIBUTIONS = """Temporary stills for the photo-carousel test preview.
Source clips remain in the repository. Generated stills are ignored by git.

1. “Agrivoltaics pilot plant at Heggelbach Farm in Germany 01” — Fraunhofer ISE — CC0 1.0
   https://commons.wikimedia.org/wiki/File:Agrivoltaics_pilot_plant_at_Heggelbach_Farm_in_Germany_01.webm
2. “Agrivoltaics pilot plant at Heggelbach Farm in Germany 05” — Fraunhofer ISE — CC0 1.0
   https://commons.wikimedia.org/wiki/File:Agrivoltaics_pilot_plant_at_Heggelbach_Farm_in_Germany_05.webm

The CC0 clips are used here only to demonstrate the carousel motion. See
brands/asta-energy/licensing/stock_credits.txt for the repository's source record.
"""


def main() -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg must be available on PATH")
    OUT.mkdir(parents=True, exist_ok=True)
    for relative, name, timestamp in SOURCES:
        source = ROOT / relative
        if not source.is_file() or source.stat().st_size < 1000:
            raise SystemExit(f"Missing Git LFS footage: {source}")
        subprocess.run([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-ss", str(timestamp), "-i", str(source), "-frames:v", "1",
            "-vf", "scale=720:1080:force_original_aspect_ratio=increase,crop=720:1080",
            "-q:v", "2", str(OUT / name),
        ], check=True)
    (OUT / "CREDITS.txt").write_text(ATTRIBUTIONS, encoding="utf-8")
    print(json.dumps({"assets": len(SOURCES), "directory": str(OUT),
                      "credits": str(OUT / "CREDITS.txt")}, indent=2))


if __name__ == "__main__":
    main()
