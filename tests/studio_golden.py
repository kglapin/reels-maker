"""Golden-frame fixtures for the studio engine (MD-08).

Five representative demo scenes are rendered three times each (entrance,
settled, near-exit) at the preview profile. The three frames are tiled into
one strip PNG per scene and stored under ``tests/fixtures/studio-golden/``.

Run ``python tests/studio_golden.py --write`` to (re)capture fixtures after an
intended visual change — human review the new strips first. Running without
``--write`` verifies and exits 1 on any mismatch. Pixel comparison is exact:
the studio graph is fully deterministic (fixed seeds, no time randomness).

Exact pixels also depend on the rasterizer: Pillow bundles its own FreeType, and
FreeType 2.14 (Pillow 12) anti-aliases glyph edges slightly differently from
2.13 (Pillow 10-11). ``pyproject.toml`` therefore caps Pillow below 12. Raising
that cap requires recapturing these strips and reviewing them, not just
refreshing the files.

QA renders are not creative approval: goldens catch unintended regressions,
and the owner still reviews real renders on a phone.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops

from reels_maker.renderers.scene import RenderOptions, SceneRenderer
from reels_maker.studio import load_studio

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "brands/asta-energy/projects/asta-motion-system-demo.json"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "studio-golden"

# hook, spotlight photo, hero counter, energy-flow, closing CTA.
SAMPLE_SCENES = (0, 1, 2, 8, 12)


def build_demo():
    project = load_studio(DEMO, root=ROOT, profile="preview")
    timeline = project.timeline()
    built = project.build(timeline)
    renderer = SceneRenderer(project.width, project.height, project.tokens,
                             project.fonts, options=RenderOptions(supersample=1))
    return project, built, renderer


def scene_strip(built, renderer, index: int) -> Image.Image:
    scene = built[index]
    duration = scene.duration
    times = (.03, duration * .55, max(.03, duration - .04))
    width, height = renderer.width, renderer.height
    strip = Image.new("RGB", (width * 3, height), "black")
    for position, time in enumerate(times):
        strip.paste(renderer.render(scene, time), (position * width, 0))
    return strip


def collect(write: bool = False, scenes=SAMPLE_SCENES) -> list[tuple[str, str]]:
    """Regenerate every strip and compare against the stored goldens."""
    project, built, renderer = build_demo()
    if write:
        FIXTURES.mkdir(parents=True, exist_ok=True)
    diffs: list[tuple[str, str]] = []
    for index in scenes:
        if index >= len(built):
            diffs.append((f"scene-{index:02d}-strip.png", "missing scene"))
            continue
        strip = scene_strip(built, renderer, index)
        name = f"scene-{index:02d}-strip.png"
        destination = FIXTURES / name
        if write:
            strip.save(destination)
            continue
        if not destination.is_file():
            diffs.append((name, "missing fixture"))
            continue
        with Image.open(destination) as golden:
            if ImageChops.difference(strip, golden.convert("RGB")).getbbox():
                diffs.append((name, "pixels differ"))
    return diffs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true",
                        help="(Re)capture fixtures instead of verifying")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    diffs = collect(write=args.write)
    payload = {
        "fixtures": str(FIXTURES),
        "mode": "write" if args.write else "verify",
        "strips": len(SAMPLE_SCENES),
        "mismatched": diffs,
        "status": "ok" if (args.write or not diffs) else "error",
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if (args.write or not diffs) else 1


if __name__ == "__main__":
    sys.exit(main())
