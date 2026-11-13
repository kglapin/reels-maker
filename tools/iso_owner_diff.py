#!/usr/bin/env python3
"""Owner-map diff: which draw call owns each pixel in painter vs depth mode.

Usage: iso_owner_diff.py props_batch.prop

Renders the prop gallery frame in depth mode while stamping, per pixel,
the index of the last depth-winning call. Then diffs against the painter
render and reports which depth-owner calls cover the differing pixels —
i.e. which element depth considers frontmost where painter disagrees.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "src")
sys.path.insert(0, ".")

import numpy as np

from reels_maker.iso import projection
from reels_maker.iso.projection import Canvas, DEFAULT_PALETTE
from reels_maker.iso.film import focus


def main():
    label = sys.argv[1]
    mod_name, prop = label.split(".", 1)
    import importlib
    module = importlib.import_module(f"reels_maker.iso.{mod_name}")
    spec = module.PROPS[prop]
    P = dict(DEFAULT_PALETTE)

    # Painter render
    projection._USE_DEPTH = False
    k, origin = focus(spec["focus"], spec["k"])
    qp = Canvas(P["bg"], k, origin)
    spec["fn"](qp, 0.0, 0.15, P)
    pan = np.asarray(qp.im.convert("RGB")).astype(np.int16)

    # Depth render with owner stamping
    projection._USE_DEPTH = True
    qd = Canvas(P["bg"], k, origin)
    owner = np.full((1500, 1840), -1, dtype=np.int32)
    dep_calls = []
    orig_zc = qd._z_composite

    def zc_spy(mask, dmap, col, opaque, box):
        idx = len(dep_calls)
        dep_calls.append({"col": tuple(col), "opaque": opaque, "box": box})
        x0, y0, x1, y1 = box
        zb = qd._zbuf[y0:y1, x0:x1]
        if opaque:
            vis = (mask > 0.0) & (dmap >= zb - 1e-3)
        else:
            vis = mask > 0.0
        sub = owner[y0:y1, x0:x1]
        sub[vis & (mask > 0.05)] = idx
        return orig_zc(mask, dmap, col, opaque, box)

    qd._z_composite = zc_spy
    spec["fn"](qd, 0.0, 0.15, P)
    dep = np.asarray(qd.im.convert("RGB")).astype(np.int16)
    projection._USE_DEPTH = False

    d = np.abs(pan - dep).max(axis=2)
    mask = d > 40
    n = int(mask.sum())
    print(f"{label}: diff px {n}")
    if not n:
        return
    ys, xs = np.where(mask)
    own = owner[ys, xs]
    vals, counts = np.unique(own[own >= 0], return_counts=True)
    order = np.argsort(-counts)
    for i in order[:12]:
        idx = int(vals[i])
        c = dep_calls[idx]
        print(f"  owner call {idx}: {int(counts[i])} px  "
              f"col={c['col']} opaque={c['opaque']} box={c['box']}")
    un = int((own < 0).sum())
    if un:
        print(f"  unowned (grad/decal/line-painter): {un} px")
    print("  diff bbox x", int(xs.min()), int(xs.max()),
          "y", int(ys.min()), int(ys.max()))


if __name__ == "__main__":
    main()
