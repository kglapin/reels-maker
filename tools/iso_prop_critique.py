#!/usr/bin/env python3
"""Automatic visual critique for iso prop gallery renders.

Run from the repository root after installing the project::

    .venv/bin/python tools/iso_prop_critique.py --help

The critique works on any render callback and needs no human eye. It
catches, in order of importance:

- ``floater`` (error): a disconnected ink component that touches neither
  the main prop nor the ground zone — a part floating in mid-air that the
  painter-order renderer cannot occlude for us;
- ``cropped`` (error): prop ink touching the top/left/right frame edge —
  the close-up cuts the subject (the ground may bleed at the bottom);
- ``framing`` (error): the prop covers far too little (lost in the frame)
  or far too much of the frame;
- ``offcenter`` (warning): the ink centroid sits far from the frame center.

Framing-class failures (crop/fill/center) are fixed automatically by
re-aiming the camera (zoom + recenter loop, bounded iterations).
Structural failures (floaters) cannot be fixed by moving the camera, so
they are reported with bounding boxes for the prop author instead.
"""
from __future__ import annotations

import argparse
import json
from collections import deque

import numpy as np
from PIL import Image

WORK_W = 384
FILL_MIN, FILL_MAX = 0.05, 0.85
EDGE_BAND = 0.015
MIN_COMPONENT = 25
CENTER_TOL = 0.18
MAX_REFRAMES = 5


def _mask(im: Image.Image, plate: Image.Image) -> np.ndarray:
    small = im.convert("RGB").resize((WORK_W, round(WORK_W * im.height / im.width)))
    clean = plate.convert("RGB").resize(small.size)
    arr = np.asarray(small).astype(np.int16)
    ref = np.asarray(clean).astype(np.int16)
    return (np.abs(arr - ref).max(axis=2) > 12), small.size


def _components(mask: np.ndarray) -> list[dict]:
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    found = []
    for y in range(h):
        for x in range(w):
            if not mask[y, x] or seen[y, x]:
                continue
            queue = deque([(y, x)])
            seen[y, x] = True
            count, x0, y0, x1, y1 = 0, x, y, x, y
            while queue:
                cy, cx = queue.popleft()
                count += 1
                x0, y0 = min(x0, cx), min(y0, cy)
                x1, y1 = max(x1, cx), max(y1, cy)
                for ny in (cy - 1, cy, cy + 1):
                    for nx in (cx - 1, cx, cx + 1):
                        if (0 <= ny < h and 0 <= nx < w
                                and mask[ny, nx] and not seen[ny, nx]):
                            seen[ny, nx] = True
                            queue.append((ny, nx))
            if count >= MIN_COMPONENT:
                found.append({"area": count,
                              "bbox": (x0, y0, x1, y1)})
    return found


def critique(image: Image.Image, plate: Image.Image) -> dict:
    """Inspect one prop render against its clean plate.

    ``plate`` is the same scene rendered without the prop (same camera,
    ground and wall). Ink = pixels that differ from the plate, so set
    dressing never counts as prop and the fill/crop/floater checks read
    the subject alone.
    """
    mask, (w, h) = _mask(image, plate)
    ink = int(mask.sum())
    fill = ink / (w * h)
    issues: list[dict] = []
    band = max(1, round(WORK_W * EDGE_BAND))
    edges = []
    if mask[:band, :].sum() > 20:
        edges.append("top")
    if mask[:, :band].sum() > 20:
        edges.append("left")
    if mask[:, -band:].sum() > 20:
        edges.append("right")
    if edges:
        issues.append({"code": "cropped", "severity": "error",
                       "detail": {"edges": edges}})
    parts = sorted(_components(mask), key=lambda p: -p["area"])
    span = 0.0
    if parts:
        x0, y0, x1, y1 = parts[0]["bbox"]
        span = max((x1 - x0) / w, (y1 - y0) / h)
    if not FILL_MIN <= fill <= FILL_MAX:
        if fill < FILL_MIN and span >= 0.35:
            issues.append({"code": "thin-subject", "severity": "warning",
                           "detail": {"fill": round(fill, 4),
                                      "span": round(span, 3)}})
        else:
            issues.append({"code": "framing", "severity": "error",
                           "detail": {"fill": round(fill, 4),
                                      "want": [FILL_MIN, FILL_MAX]}})
    ys, xs = np.nonzero(mask)
    cx = float(xs.mean() / w) if ink else 0.5
    cy = float(ys.mean() / h) if ink else 0.5
    if abs(cx - 0.5) > CENTER_TOL or abs(cy - 0.5) > CENTER_TOL:
        issues.append({"code": "offcenter", "severity": "warning",
                       "detail": {"centroid": [round(cx, 3), round(cy, 3)]}})
    parts = sorted(_components(mask), key=lambda p: -p["area"])
    if parts:
        main = parts[0]["bbox"]
        ground_y = round(h * 0.85)
        for part in parts[1:]:
            x0, y0, x1, y1 = part["bbox"]
            touches_main = not (x1 < main[0] - 2 or x0 > main[2] + 2
                                or y1 < main[1] - 2 or y0 > main[3] + 2)
            touches_ground = y1 >= ground_y
            if not touches_main and not touches_ground:
                issues.append({"code": "floater", "severity": "error",
                               "detail": {"bbox": list(part["bbox"]),
                                          "area": part["area"]}})
    return {"ok": not any(i["severity"] == "error" for i in issues),
            "issues": issues,
            "metrics": {"fill": round(fill, 4),
                        "centroid": [round(cx, 3), round(cy, 3)],
                        "components": len(parts)}}


def autoreframe(paint, plate, *, k: float, origin: tuple[float, float],
                size: tuple[int, int]) -> tuple:
    """Re-render until framing passes; return (image, corrections, report).

    ``paint(k, origin)`` must return a full-size PIL image; ``plate`` is
    the prop-free clean plate (re-aimed alongside by the caller when the
    camera moves). Only camera work (zoom/recenter) is attempted here;
    structural ``floater`` findings are returned for the author.
    """
    corrections: list[str] = []
    w, h = size
    for _ in range(MAX_REFRAMES + 1):
        image = paint(k, origin)
        report = critique(image, plate)
        codes = {i["code"] for i in report["issues"]
                 if i["severity"] == "error"}
        if "floater" in codes:
            codes.discard("floater")
        if not codes & {"cropped", "framing"}:
            break
        fill = report["metrics"]["fill"]
        if "cropped" in codes or fill > FILL_MAX:
            k /= 1.18
            corrections.append(f"zoom-out k={k:.0f}")
        elif fill < FILL_MIN:
            k *= 1.18
            corrections.append(f"zoom-in k={k:.0f}")
        else:
            break
    else:
        image = paint(k, origin)
        report = critique(image, plate)
    cx, cy = report["metrics"]["centroid"]
    if abs(cx - 0.5) > CENTER_TOL / 2 or abs(cy - 0.5) > CENTER_TOL / 2:
        origin = (origin[0] + (0.5 - cx) * w / 2,
                  origin[1] + (0.5 - cy) * h / 2)
        corrections.append("recenter")
        image = paint(k, origin)
        report = critique(image, plate)
    return image, corrections, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", help="render PNG to critique")
    parser.add_argument("--plate", required=True,
                        help="clean-plate PNG (same scene without the prop)")
    args = parser.parse_args()
    with Image.open(args.image) as im, Image.open(args.plate) as plate:
        report = critique(im, plate)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
