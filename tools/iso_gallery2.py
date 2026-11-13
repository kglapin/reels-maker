#!/usr/bin/env python3
"""Registry-driven prop gallery renderer (batch props live here, not /tmp).

Usage::

    .venv/bin/python tools/iso_gallery2.py props_heat_a.manifold 17-rozdzielacz

Each ``src/reels_maker/iso/props_<batch>.py`` module owns a ``PROPS`` dict::

    PROPS = {"manifold": {"fn": manifold, "focus": (0.0, 0.15, 0.45),
                          "k": 550, "plinth": (0.0, 0.15, 0.55, 0.34),
                          "brief": "brass heating manifold with ..."}, ...}

Builders take ``(q, cx, cy, P)`` with all coordinates relative to the
placement center, mid-tone flat palette, overlapped (never exact-touch)
joints, NO contact shadows (owner rule), no text decals. Gallery calls
``fn(q, 0.0, 0.15, P)``. Prints the render PNG, the clean plate PNG and
the pixel pre-check verdict (paths first for scripting).
"""
from __future__ import annotations

import importlib
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, _ROOT)

from reels_maker.iso.film import focus
from reels_maker.iso.projection import Canvas, DEFAULT_PALETTE
from tools.iso_prop_critique import critique


def paint_prop(spec, with_prop: bool, P) -> "Image.Image":
    """Gallery paint path shared by the render and its clean plate."""
    k, origin = focus(spec["focus"], spec["k"])
    q = Canvas(P["bg"], k, origin)
    if with_prop:
        spec["fn"](q, 0.0, 0.15, P)
    img = q.im
    return img.resize((768, round(768 * img.height / img.width)))



def main() -> int:
    if len(sys.argv) != 3 or "." not in sys.argv[1]:
        print("usage: iso_gallery2.py props_<batch>.<prop> <NN-title>")
        return 2
    module_name, prop = sys.argv[1].split(".", 1)
    title = sys.argv[2]
    try:
        module = importlib.import_module(f"reels_maker.iso.{module_name}")
    except ImportError as exc:
        print(f"no such batch module: {module_name} ({exc})")
        return 2
    spec = getattr(module, "PROPS", {}).get(prop)
    if spec is None:
        print(f"no such prop: {prop} in {module_name}")
        return 2
    from PIL import Image

    P = dict(DEFAULT_PALETTE)
    out = f"renders/asta-energy/prop-galeria/{title}.png"
    plate_path = f"/tmp/plate-{title}.png"

    from functools import partial
    paint = partial(paint_prop, spec, P=P)

    paint(True).save(out)
    paint(False).save(plate_path)
    with Image.open(out) as im, Image.open(plate_path) as plate:
        report = critique(im, plate)
    print(out)
    print(plate_path)
    print(json.dumps({"pixel_ok": report["ok"],
                      "issues": [(i["code"], i.get("severity"))
                                 for i in report["issues"]],
                      "fill": report["metrics"]["fill"]}))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
