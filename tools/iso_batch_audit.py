#!/usr/bin/env python3
"""Batch audit for every registry prop: painter vs depth render + pixel check.

For each ``props_<batch>.PROPS`` entry this renders the gallery frame twice —
once with the painter backend and once with the opt-in depth buffer
(``projection._USE_DEPTH`` toggled in-process) — then reports:

- ``pixel``: tools.iso_prop_critique verdict (cropped/floater/fill)
- ``diff``: fraction of pixels differing >40 between painter and depth —
  large values mean painter-order bugs the depth buffer would fix (or
  intentional overlays it must not touch)
- ``depth_only``: props that crash or misrender only under depth mode

Usage::

    .venv/bin/python tools/iso_batch_audit.py [--depth] [--out DIR] [--json]

``--depth`` also saves the depth-mode PNG next to the painter one under
``--out`` (default ``renders/asta-energy/prop-audit/``). Writes
``batch-audit.json`` next to the images. Exit 0 always — this is a report
tool, not a gate; use iso_layer_audit for the hard gate.
"""
from __future__ import annotations

import argparse
import importlib
import json
import pathlib
import sys
import time

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))

from PIL import Image  # noqa: E402

from reels_maker.iso import projection  # noqa: E402
from reels_maker.iso.projection import DEFAULT_PALETTE  # noqa: E402
from tools.iso_gallery2 import paint_prop  # noqa: E402
from tools.iso_prop_critique import critique  # noqa: E402

BATCH_MODULES = [
    "props_buildings", "props_electro", "props_extra", "props_farm",
    "props_heat_a", "props_heat_b", "props_home2", "props_hvac2",
    "props_icons", "props_industry", "props_interior", "props_nature",
    "props_pv2", "props_roof", "props_small", "props_storage2",
    "props_street2", "props_tools",
]


def render(spec, P):
    return paint_prop(spec, True, P).convert("RGB")


def diff_frac(a: Image.Image, b: Image.Image) -> float:
    import numpy as np
    aa = np.asarray(a, dtype=np.int16)
    bb = np.asarray(b, dtype=np.int16)
    d = np.abs(aa - bb).max(axis=2)
    return float((d > 40).mean())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--depth", action="store_true",
                    help="save depth-mode PNGs too")
    ap.add_argument("--out", default="renders/asta-energy/prop-audit")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    out_dir = _ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    P = dict(DEFAULT_PALETTE)
    results = []
    t0 = time.time()
    for mod_name in BATCH_MODULES:
        module = importlib.import_module(f"reels_maker.iso.{mod_name}")
        for prop, spec in getattr(module, "PROPS", {}).items():
            label = f"{mod_name}.{prop}"
            row = {"prop": label, "k": spec.get("k")}
            try:
                projection._USE_DEPTH = False
                painter = render(spec, P)
                plate = paint_prop(spec, False, P).convert("RGB")
                row["pixel"] = critique(painter, plate)["ok"]
                painter.save(out_dir / f"{label}.png")
                projection._USE_DEPTH = True
                try:
                    depth = render(spec, P)
                    row["diff"] = round(diff_frac(painter, depth), 4)
                    if args.depth:
                        depth.save(out_dir / f"{label}~depth.png")
                except Exception as exc:  # noqa: BLE001
                    row["depth_error"] = f"{type(exc).__name__}: {exc}"
                finally:
                    projection._USE_DEPTH = False
            except Exception as exc:  # noqa: BLE001
                row["error"] = f"{type(exc).__name__}: {exc}"
            results.append(row)
            flag = "" if row.get("pixel") and "error" not in row else "  <-- FLAG"
            print(f"{label:44s} diff={row.get('diff','-'):>6} "
                  f"pixel={row.get('pixel','-')}{flag}", flush=True)

    summary = {
        "props": len(results),
        "elapsed_s": round(time.time() - t0, 1),
        "pixel_fail": [r["prop"] for r in results if not r.get("pixel")],
        "errors": [r["prop"] for r in results if "error" in r],
        "depth_errors": [r["prop"] for r in results
                         if "depth_error" in r],
        "top_diff": sorted(
            (r for r in results if "diff" in r),
            key=lambda r: -r["diff"])[:20],
        "results": results,
    }
    (out_dir / "batch-audit.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k != "results"},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
