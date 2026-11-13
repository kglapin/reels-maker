#!/usr/bin/env python3
"""Layer/perspective audit for every iso prop: catches what the eye misses.

A recording Canvas replays each builder and checks every draw call:

- ``inversion`` (error): a LATER opaque primitive covers much of an
  EARLIER one while sitting FARTHER from the camera (smaller x+y).
  Painter order must run far -> near; anything else reads as floating
  or piercing, no matter what the geometry says.
- ``occlusion`` (warning): a later opaque primitive covers >50% of an
  earlier opaque one at similar depth — the hero may be buried.
- ``exact-touch`` (error): two boxes sharing a face plane exactly —
  aliases into a hairline gap; mating parts must overlap >= 0.005.

Translucent late primitives (glass, sheens) are intentional overdraw
and never flagged. Run from the repository root::

    .venv/bin/python tools/iso_layer_audit.py [--prop props_heat_a.manifold]

Exit code is 0 only with zero errors (warnings never fail the gate).
"""
from __future__ import annotations

import argparse
import importlib
import json
import math
import statistics
import sys

import numpy as np

sys.path.insert(0, "src")

from reels_maker.iso.film import focus
from reels_maker.iso.projection import Canvas, DEFAULT_PALETTE
from reels_maker.iso import world as _world

OVERLAP_ERR = 0.15
OVERLAP_WARN = 0.50
DEPTH_EPS = 0.03


class Rec(Canvas):
    """Canvas that records every draw call with world points + alpha.

    Record-only: nothing is rasterized (orders of magnitude faster than
    rendering); mapping (P/_raw) is inherited exact, stack included."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls: list = []

    def _rec(self, op, pts, c, grow=0.0):
        alpha = c[3] if len(c) > 3 else 255
        self.calls.append({"op": op, "pts": list(pts), "alpha": alpha,
                           "grow": grow})
        return alpha

    def poly(self, ps, c):
        self._rec("poly", ps, self._c(c))

    def line(self, ps, c, w=1):
        self._rec("line", ps, self._c(c), grow=max(1.0, float(w)))

    def dot(self, p, r, c):
        self._rec("dot", [p], self._c(c), grow=float(r) * 2 + 1)

    def box(self, a, b, *args, **kwargs):
        x, y, z = a
        X, Y, Z = b
        cols = [self._c(args[i] if len(args) > i else (0, 0, 0))
                for i in range(3)]
        alpha = min(c[3] if len(c) > 3 else 255 for c in cols)
        self.calls.append({"op": "box",
                           "pts": [(X, y, z), (X, Y, z), (X, Y, Z), (X, y, Z),
                                   (x, Y, z), (x, Y, Z), (x, y, Z), (x, y, z)],
                           "alpha": alpha, "grow": 0.0})

    def fp(self, x, X, y, z, Z, c):
        self._rec("fp", [(x, y, z), (X, y, z), (X, y, Z), (x, y, Z)],
                  self._c(c))

    def disc_x(self, x, cy, cz, r, c, n=36):
        pts = [(x, cy + r * math.cos(i * math.tau / n),
                cz + r * math.sin(i * math.tau / n)) for i in range(n)]
        self._rec("disc", pts, self._c(c))
        self.calls[-1]["axis"] = 0
        self.calls[-1]["center"] = (x, cy, cz)
        self.calls[-1]["r"] = r

    def disc_y(self, cx, y, cz, r, c, n=36):
        pts = [(cx + r * math.cos(i * math.tau / n), y,
                cz + r * math.sin(i * math.tau / n)) for i in range(n)]
        self._rec("disc", pts, self._c(c))
        self.calls[-1]["axis"] = 1
        self.calls[-1]["center"] = (cx, y, cz)
        self.calls[-1]["r"] = r

    def ground_ellipse(self, cx, cy, rx, ry, c, z=-0.125, n=40):
        pts = [(cx + rx * math.cos(i * math.tau / n),
                cy + ry * math.sin(i * math.tau / n), z) for i in range(n)]
        self._rec("gnd", pts, self._c(c))

    def tube(self, cx, cy, z0, z1, r):
        self.calls.append({"op": "tube", "cx": cx, "cy": cy,
                           "z0": z0, "z1": z1, "r": r,
                           "alpha": 255, "grow": 0.0})

    def boxg(self, a, b, c=(200, 205, 195), *rest, dl=0.14):
        x, y, z = a
        X, Y, Z = b
        self.calls.append({"op": "box",
                           "pts": [(X, y, z), (X, Y, z), (X, Y, Z), (X, y, Z),
                                   (x, Y, z), (x, Y, Z), (x, y, Z), (x, y, z)],
                           "alpha": 255, "grow": 0.0})

    def ao(self, cx, cy, r, strength=0.18, z=0.0, squash=0.5):
        self.calls.append({"op": "ao", "pts": [(cx, cy, z)],
                           "alpha": 0, "grow": 0.0})


def _bbox(q, call):
    xs, ys = [], []
    for p in call["pts"]:
        x, y = q.P(p)
        xs.append(x)
        ys.append(y)
    g = call["grow"]
    return (min(xs) - g, min(ys) - g, max(xs) + g, max(ys) + g)


def _depth(call):
    # View ray is (1,1,1): points projecting to the same screen pixel
    # differ along x+y+z, so larger x+y+z is strictly nearer the camera.
    # (x+y alone misreads stacked parts: a valve ABOVE its bar is nearer,
    # not behind it.)
    return sum(p[0] + p[1] + p[2] for p in call["pts"]) / max(1, len(call["pts"]))


def _dense(call):
    """Face-grid samples: corners alone miss overlap bands (a foot box
    standing on a plinth shares no corner with it, yet must compare)."""
    pts = list(call["pts"])
    if call["op"] == "box" and len(call["pts"]) >= 8:
        c = call["pts"]
        faces = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6),
                 (1, 2, 6, 5), (3, 0, 4, 7)]
        for face in faces:
            for a in (0.2, 0.5, 0.8):
                for b in (0.2, 0.5, 0.8):
                    p0, p1, p2, p3 = (c[i] for i in face)
                    pts.append((
                        p0[0] * (1 - a) * (1 - b) + p1[0] * a * (1 - b)
                        + p2[0] * a * b + p3[0] * (1 - a) * b,
                        p0[1] * (1 - a) * (1 - b) + p1[1] * a * (1 - b)
                        + p2[1] * a * b + p3[1] * (1 - a) * b,
                        p0[2] * (1 - a) * (1 - b) + p1[2] * a * (1 - b)
                        + p2[2] * a * b + p3[2] * (1 - a) * b))
    elif call["op"] == "disc" and "axis" in call:
        cx, cy, cz = call["center"]
        rr0 = call["r"]
        for rr in (0.33, 0.66, 1.0):
            for k in range(12):
                ang = k * math.tau / 12
                co, si = math.cos(ang) * rr0 * rr, math.sin(ang) * rr0 * rr
                if call["axis"] == 0:
                    pts.append((cx, cy + co, cz + si))
                else:
                    pts.append((cx + co, cy, cz + si))
        pts.append((cx, cy, cz))
    elif call["op"] == "gnd" and len(call["pts"]) > 4:
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        cz = call["pts"][0][2]
        rx = max(abs(p[0] - cx) for p in pts)
        ry = max(abs(p[1] - cy) for p in pts)
        for fr in (0.33, 0.66):
            for k in range(12):
                ang = k * math.tau / 12
                pts.append((cx + rx * fr * math.cos(ang),
                            cy + ry * fr * math.sin(ang), cz))
        pts.append((cx, cy, cz))
    else:
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        cz = sum(p[2] for p in pts) / len(pts)
        pts.append((cx, cy, cz))
        for A, B in zip(pts, pts[1:]):
            pts.append(((A[0] + B[0]) / 2, (A[1] + B[1]) / 2,
                        (A[2] + B[2]) / 2))
    return pts


def _tube_of(call):
    """World-space tube volume for a recorded tube marker."""
    return {"cx": call["cx"], "cy": call["cy"],
            "z0": call["z0"], "z1": call["z1"], "r": call["r"]}


def _disc_hits_box(disc, box):
    """True when a flat disc (cx, cy, r at height z) overlaps the
    interior of a box volume (strictly inside, any face)."""
    (cx, cy, r, z) = disc
    (x0, y0, z0, x1, y1, z1) = box
    if not (z0 < z < z1):
        # Sitting exactly on a face is the exact-touch check's job.
        return False
    nx = max(x0, min(cx, x1))
    ny = max(y0, min(cy, y1))
    return (cx - nx) ** 2 + (cy - ny) ** 2 < r ** 2


def _disc_hits_tube(disc, tube, own):
    """True when a flat disc overlaps another tube's solid volume
    (the tube's own shell is excluded by the caller)."""
    (cx, cy, r, z) = disc
    if own and abs(cx - tube["cx"]) < 1e-9 and abs(cy - tube["cy"]) < 1e-9:
        return False
    if not (tube["z0"] < z < tube["z1"]):
        return False
    return (cx - tube["cx"]) ** 2 + (cy - tube["cy"]) ** 2 < (
        r + tube["r"]) ** 2


def _screen_samples(q, call, cap=300):
    """Project dense samples to screen: (xy array, depth array)."""
    pts = _dense(call)
    if len(pts) > cap:
        step = len(pts) / cap
        pts = [pts[int(i * step)] for i in range(cap)]
    xy = np.array([[q.P(p)[0], q.P(p)[1]] for p in pts], dtype=float)
    dd = np.array([p[0] + p[1] + p[2] for p in pts], dtype=float)
    return xy, dd


def _matched_depth(q, late, early, radius=8.0, need=5):
    """Median (late - early) depth over screen-matched sample pairs.

    Neighbors in screen space ride nearly the same view ray, so their
    x+y+z difference measures true in-front/behind order. Returns None
    when too few pairs match (no evidence either way)."""
    lxy, ldd = _screen_samples(q, late)
    exy, edd = _screen_samples(q, early)
    if not len(lxy) or not len(exy):
        return None
    d2 = ((lxy[:, None, :] - exy[None, :, :]) ** 2).sum(axis=2)
    best = np.argmin(d2, axis=1)
    dist = np.sqrt(d2[np.arange(len(lxy)), best])
    mask = dist <= radius
    if int(mask.sum()) < need:
        return None
    return float(np.median(ldd[mask] - edd[best[mask]]))


def _world_box(c):
    """World-space (a, b) for box calls; None otherwise."""
    if c["op"] != "box" or len(c["pts"]) < 8:
        return None
    xs = [p[0] for p in c["pts"]]
    ys = [p[1] for p in c["pts"]]
    zs = [p[2] for p in c["pts"]]
    return ((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)))


def audit_calls(q, calls):
    """Return (errors, warnings) over one recorded paint.

    Three deterministic checks — no ray heuristics:
    - ``exact-touch`` (error): a horizontal mating seam where the
      upper bottom meets the lower top exactly. Aliases into hairline
      gaps; mates must overlap >= 0.005. Side-face (X/Y) butt joints
      are NOT checked: every instance found was intentional flush
      joinery (posts on slab edges, rails in walls), and floating
      side attachments are already caught by the floater check.
    - ``buried-detail`` (warning): an opaque primitive covers >= 50%
      of a detail dot's box (hubs, glands, bolts erased by later
      paint — the classic volute-hub-under-pipe bug).
    - ``phantom-cap`` G1/G1b/G3 (warning — collar triage): a buried
      mid-tube cap, a foot rim on a confirmed plate, or an orphan
      disc. Full-corpus zoom review (158 flags, 2026-11-11) showed
      ~95% read as correct hardware — collars ARE the joint
      language (valve bonnets, glands, flanges), translucent covers
      show frames by design, coins/buttons stack by design,
      propeller discs are effects. Visibility is perceptual
      (contrast x isolation x proportion); the eye + LLM ensemble
      decide, the warning only points.
    - ``phantom-cap`` G1c (error): a protruding foot rim haloing
      over the display plinth with AIR beneath the overhang (the
      hay-bale halo). Rims with an opaque support top within 0.04
      below are feet, not halos, and are exempt.
    """
    errors, warnings = [], []
    boxes = [(i, c, _world_box(c)) for i, c in enumerate(calls)
             if c["op"] == "box" and _world_box(c) is not None]
    for ja in range(len(boxes)):
        ij, cj, (aj, bj) = boxes[ja]
        for ka in range(ja):
            ik, ck, (ak, bk) = boxes[ka]
            ox = min(bj[0], bk[0]) - max(aj[0], ak[0])
            oy = min(bj[1], bk[1]) - max(aj[1], ak[1])
            # Visible horizontal seam: upper bottom meets lower top.
            if abs(aj[2] - bk[2]) < 1e-9 and ox > 1e-6 and oy > 1e-6:
                errors.append({"code": "exact-touch", "calls": [ik, ij],
                               "detail": f"calls {ik}/{ij} share z-plane "
                               f"{aj[2]:.3f} over {ox:.3f}x{oy:.3f}"})
    tubes = [(i, c) for i, c in enumerate(calls)
               if c["op"] == "tube"]
    boxes = []
    for i, c in enumerate(calls):
        wb = _world_box(c)
        if wb is not None and c["alpha"] == 255:
            boxes.append((i, wb[0] + wb[1]))
    for ij, cj in [(i, c) for i, c in enumerate(calls)
                   if c["op"] == "gnd" and c["alpha"] == 255]:
        xs = [p[0] for p in cj["pts"]]
        ys = [p[1] for p in cj["pts"]]
        if not xs:
            continue
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        z = cj["pts"][0][2]
        rx = (max(xs) - min(xs)) / 2
        if rx >= 0.35:
            continue  # display stage
        disc = (cx, cy, rx, z)
        own = [t for _, t in tubes
               if abs(cx - t["cx"]) < t["r"] * 0.3 + 1e-9
               and abs(cy - t["cy"]) < t["r"] * 0.3 + 1e-9
               and t["z0"] - 0.02 <= z <= t["z1"] + 0.06
               and rx <= t["r"] * 1.3 + 1e-9]
        plinths = [c for c in calls if c["op"] == "gnd"
                   and (max(p[0] for p in c["pts"]) -
                        min(p[0] for p in c["pts"])) / 2 >= 0.35]
        if own:
            # G1: buried mid-tube cap. The disc belongs to its tube,
            # but when ANOTHER solid both (a) was painted earlier and
            # (b) continues THROUGH the disc plane, the disc paints
            # over a wall that outlives it = classic phantom (holesaw
            # collar, softener rings, hydrant raised caps). Seal discs
            # painted FIRST never match: their cover is later
            # by construction.
            bad = None
            for ik, bb in boxes:
                if ik >= ij:
                    continue
                (x0, y0, z0, x1, y1, z1) = bb
                nx = max(x0, min(cx, x1))
                ny = max(y0, min(cy, y1))
                if (cx - nx) ** 2 + (cy - ny) ** 2 >= rx ** 2:
                    continue
                if z0 + 0.005 < z < z1 - 0.005:
                    bad = ("box", ik)
                    break
            if bad is None:
                own_ids = {id(t) for t in own}
                for ik, tc in tubes:
                    if ik >= ij or id(tc) in own_ids:
                        continue
                    tt = _tube_of(tc)
                    if tt["z0"] + 0.005 < z < tt["z1"] - 0.005 and \
                       (cx - tt["cx"]) ** 2 + (cy - tt["cy"]) ** 2 < \
                       (rx + tt["r"]) ** 2:
                        bad = ("tube", ik)
                        break
            if bad is not None:
                warnings.append({"code": "phantom-cap",
                                 "calls": [bad[1], ij],
                                 "detail": f"call {ij} (cap ellipse) buried "
                                 f"in earlier {bad[0]} {bad[1]}: collar "
                                 "triage (eye decides)"})
                continue
            # G1b: foot rim halo on a flat plate top face just below.
            is_rim = any(abs(z - (t["z0"] + 0.012)) < 0.004
                         for t in own)
            if is_rim and rx >= 0.06:
                for ik, bb in boxes:
                    if ik >= ij:
                        continue
                    (x0, y0, z0, x1, y1, z1) = bb
                    if not (z - 0.015 <= z1 <= z):
                        continue
                    if x0 + 0.01 < cx - rx or cx + rx < x1 - 0.01:
                        continue
                    if y0 + 0.01 < cy - rx or cy + rx < y1 - 0.01:
                        continue
                    warnings.append({"code": "phantom-cap",
                                     "calls": [ik, ij],
                                     "detail": f"call {ij} (foot rim) on "
                                     f"plate top {ik}: foot or halo "
                                     "(eye decides)"})
                    bad = ("box", ik)
                    break
                if bad is not None:
                    continue
            # G1c: foot rim halo on the display plinth. Protruding
            # rims of grounded tubes read as stray discs (hay bale)
            # — but only when AIR sits beneath the overhang. A rim
            # with an opaque support top just below is a foot
            # standing on rails/a frame (compressor, thermo-head),
            # not a halo.
            if is_rim and rx >= 0.12 and plinths:
                tr = max(t["r"] for t in own)
                if rx - tr >= 0.015:
                    supported = False
                    for ik, bb in boxes:
                        if ik >= ij:
                            continue
                        (x0, y0, z0, x1, y1, z1) = bb
                        if z - 0.04 <= z1 <= z - 0.004 and \
                           x0 <= cx <= x1 and y0 <= cy <= y1:
                            supported = True
                            break
                    if not supported:
                        errors.append({"code": "phantom-cap",
                                       "calls": [ij, ij],
                                       "detail": f"call {ij} (foot rim) "
                                       "halos over the plinth: phantom"})
                        continue
            continue
        # G3: unpaired flat ellipse (no tube claims it). Stacked rings
        # sharing a center (washers, coil turns, seat rings, plinth
        # steps) and cap-deco rings over a tube top are exempt;
        # contact-shadow blobs and stray halos are not.
        if rx < 0.10:
            continue
        sibs = [c for c in calls if c["op"] == "gnd"
                and abs(sum(p[0] for p in c["pts"]) / len(c["pts"]) - cx)
                < rx * 0.3 + 1e-9
                and abs(sum(p[1] for p in c["pts"]) / len(c["pts"]) - cy)
                < rx * 0.3 + 1e-9]
        if len(sibs) >= 2 and \
           max(p[2] for s in sibs for p in s["pts"]) - \
           min(p[2] for s in sibs for p in s["pts"]) >= 0.002:
            continue
        deco = False
        for _, tc in tubes:
            if abs(cx - tc["cx"]) < tc["r"] * 0.5 + 1e-9 and \
               abs(cy - tc["cy"]) < tc["r"] * 0.5 + 1e-9 and \
               tc["z1"] <= z <= tc["z1"] + 0.15 and rx <= tc["r"]:
                deco = True
                break
        if not deco:
            warnings.append({"code": "phantom-cap", "calls": [ij, ij],
                             "detail": f"call {ij} (flat ellipse, no "
                             "tube claims it): stray or effect "
                             "(eye decides)"})
    dots = [(i, c) for i, c in enumerate(calls) if c["op"] == "dot"]
    solids = [(i, c, _bbox(q, c)) for i, c in enumerate(calls)
              if c["op"] in ("box", "poly", "disc", "fp")
              and c["alpha"] == 255]
    for ij, cj, bj in solids:
        aw = max(0.0, bj[2] - bj[0])
        ah = max(0.0, bj[3] - bj[1])
        if aw * ah <= 0:
            continue
        for ik, ck in dots:
            if ik >= ij:
                continue
            bk = _bbox(q, ck)
            ix0, iy0 = max(bj[0], bk[0]), max(bj[1], bk[1])
            ix1, iy1 = min(bj[2], bk[2]), min(bj[3], bk[3])
            inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
            area_k = (max(0.0, bk[2] - bk[0])
                      * max(0.0, bk[3] - bk[1]))
            if inter / max(1.0, area_k) >= 0.5:
                warnings.append({"code": "buried-detail", "late": ij,
                                 "early": ik,
                                 "detail": f"call {ij} ({cj['op']}) covers "
                                 f"detail dot of call {ik}"})
    return errors, warnings


LEGACY = [
    ("buffer", "buffer_tank", (), {"level": 0.65}, (0.0, 0.0, 1.02), 255),
    ("controller", "controller", (), {"on": True}, (0.0, 0.05, 1.02), 400),
    ("radiator", "radiator", (), {}, (0.0, 0.1, 0.75), 330),
    ("battery", "battery", (), {"charge": 0.8}, (0.0, 0.0, 0.8), 330),
    ("inverter", "inverter", (), {"on": True}, (0.0, 0.05, 1.0), 330),
    ("pv", "pv_array", (), {"n": 3, "axis": "x", "mount": "ground"},
     (0.0, 0.0, 0.55), 300),
    ("switchgear", "switchgear", (), {}, (0.0, 0.0, 1.0), 300),
    ("capacitors", "capacitor_bank", (), {"n": 3, "axis": "x"},
     (0.0, 0.0, 0.5), 300),
    ("meter", "meter_box", (), {}, (0.0, 0.0, 0.5), 330),
    ("vessel", "expansion_vessel", (), {}, (0.0, 0.0, 0.55), 300),
    ("circulator", "circulator", (0.0, 0.15), {}, (-0.225, 0.15, 0.15), 650),
    ("heatpump", "pump", "HEATPUMP", {}, (0.0, 0.0, 0.45), 360),
    ("compressor", "compressor", (0.0, 0.15), {}, (0.0, 0.15, 0.18), 600),
    ("thermostat", "thermostat", (0.0, 0.15), {}, (0.0, 0.15, 0.42), 480),
    ("boilerroom", "boiler_room", "ROOM", {}, (0.0, 0.2, 0.79), 120),
]

BATCH_MODULES = ["props_heat_a", "props_heat_b", "props_electro",
                 "props_buildings", "props_nature", "props_interior",
                 "props_small", "props_extra", "props_industry",
                 "props_pv2", "props_hvac2", "props_tools", "props_farm",
                 "props_storage2", "props_home2", "props_street2",
                 "props_roof", "props_icons"]


def _paint_legacy(name, fn_name, pos, kwargs, focus_pt, k):
    P = dict(DEFAULT_PALETTE)
    fn = getattr(_world, fn_name)
    kk, origin = focus(focus_pt, k)
    q = Rec(P["bg"], kk, origin)
    if pos == "HEATPUMP":
        fn(q, -0.24, -0.625,
           {"frost": 0.0, "heat": 0.0, "angle": 0.6, "speed": 0.0},
           0.0, P)
    elif pos == "ROOM":
        fn(q, P)
    elif pos:
        fn(q, pos[0], pos[1], P, **kwargs)
    else:
        fn(q, 0.0, 0.0, P, **kwargs)
    return q


def _paint_registry(module_name, prop, spec):
    P = dict(DEFAULT_PALETTE)
    kk, origin = focus(spec["focus"], spec["k"])
    q = Rec(P["bg"], kk, origin)
    spec["fn"](q, 0.0, 0.15, P)
    return q


def audit_one(label, painter):
    """Paint via painter(q) already bound; return the report dict."""
    try:
        q = painter()
    except Exception as exc:  # noqa: BLE001 - one bad prop skips, rest run
        return {"prop": label, "status": "error", "detail": str(exc)[:200],
                "errors": [], "warnings": []}
    errors, warnings = audit_calls(q, q.calls)
    return {"prop": label, "status": "ok", "calls": len(q.calls),
            "errors": errors, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prop", default="",
                        help="only this prop: legacy name or batch.prop")
    args = parser.parse_args()
    targets = []
    for name, fn_name, pos, kwargs, focus_pt, k in LEGACY:
        if args.prop and args.prop != name:
            continue
        targets.append((name, lambda n=name, f=fn_name, p=pos, kw=kwargs,
                        fp=focus_pt, kk=k: _paint_legacy(n, f, p, kw, fp, kk)))
    for module_name in BATCH_MODULES:
        try:
            module = importlib.import_module(f"reels_maker.iso.{module_name}")
        except ImportError:
            continue
        for prop, spec in getattr(module, "PROPS", {}).items():
            label = f"{module_name}.{prop}"
            if args.prop and args.prop not in (prop, label):
                continue
            targets.append((label, lambda m=module_name, p=prop,
                            s=spec: _paint_registry(m, p, s)))
    reports = [audit_one(label, painter) for label, painter in targets]
    n_err = sum(len(r["errors"]) for r in reports)
    n_warn = sum(len(r["warnings"]) for r in reports)
    print(json.dumps({"props": len(reports), "errors": n_err,
                      "warnings": n_warn,
                      "failed": sorted({r["prop"] for r in reports
                                       if r["errors"] or r["status"] == "error"}),
                      "reports": reports}, ensure_ascii=False, indent=1))
    return 0 if n_err == 0 and all(r["status"] == "ok" for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
