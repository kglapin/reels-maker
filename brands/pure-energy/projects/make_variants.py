#!/usr/bin/env python3
"""Generate 30 visually distinct variants of the Pure Energy BESS reel.

Every variant is a transformed copy of the QA-clean base manifest
``pure-energy-bess-reels.json``. Transforms only move parameters that were
already validated (colours from the checked palette, presets handled by the
pe_editorial builder, scene permutations with equal durations) so variants
stay readable and beat-aligned while looking clearly different.

Usage (repo root):
    .venv/bin/python brands/pure-energy/projects/make_variants.py --write
    .venv/bin/python brands/pure-energy/projects/make_variants.py \
        --render-all --jobs 4 --supersample 1
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BRAND = Path(__file__).resolve().parents[1]
BASE = BRAND / "projects/pure-energy-bess-reels.json"
OUT_DIR = BRAND / "projects/variants"
RENDER_DIR = ROOT / "renders/pure-energy/variants"
TEX = BRAND / "media/textures"
BUILDER = BRAND / "projects/build_bess_reel.py"

PAPER = "media/textures/paper-cream.png"
PAPER_PURPLE = "media/textures/paper-purple.png"
PAPER_INK = "media/textures/paper-ink.png"
PAPER_SOFT = "media/textures/paper-soft.png"
PAPER_WARM = "media/textures/paper-warm.png"
PAPER_GREY = "media/textures/paper-grey.png"

PAPER_SCENES = {0, 1, 5, 7, 8, 9, 10, 12, 13}   # scene indices on paper bg
DARK_SCENES = {3, 6, 11}                        # purple/ink texture scenes
PHOTO_SCENES = {2, 4}                           # full-bleed photo + bands


# ---------------------------------------------------------------- textures
def ensure_textures() -> None:
    """Extra tinted paper canvases (same recipe as the base cream)."""
    needs = {
        PAPER_SOFT: ((245, 241, 250), (120, 105, 160)),
        PAPER_WARM: ((253, 243, 227), (150, 110, 60)),
        PAPER_GREY: ((238, 237, 242), (95, 90, 120)),
    }
    missing = [name for name in needs if not (TEX / Path(name).name).is_file()]
    if not missing:
        return
    import random as _r
    from PIL import Image, ImageDraw, ImageFilter
    _r.seed(9042)
    W, H = 2160, 3840
    for name in missing:
        base, crease = needs[name]
        noise = (Image.effect_noise((96, 96), 64)
                 .resize((W, H), Image.Resampling.BILINEAR)
                 .filter(ImageFilter.GaussianBlur(36)))
        img = Image.new("RGB", (W, H), base)
        px, out = noise.load(), img.load()
        for y in range(H):
            for x in range(W):
                m = (px[x, y] - 128) / 128 * 12
                out[x, y] = tuple(max(0, min(255, int(c + m * f)))
                                  for c, f in zip(base, (1.0, .94, .82)))
        fine = Image.effect_noise((W, H), 24).convert("L")
        img = Image.blend(img, Image.merge("RGB", (fine,) * 3), .05)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        for _ in range(8):
            x0, y0 = _r.uniform(0, W), _r.uniform(0, H)
            ang, ln = _r.uniform(0, math.pi), _r.uniform(W * .3, W * .9)
            pts = [(x0 + math.cos(ang) * ln * i / 13 + _r.uniform(-30, 30),
                    y0 + math.sin(ang) * ln * i / 13 + _r.uniform(-30, 30))
                   for i in range(14)]
            d.line(pts, fill=crease + (14,), width=_r.randint(2, 5))
        img = img.convert("RGBA")
        img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(6)))
        img.convert("RGB").save(TEX / Path(name).name)
        print("texture", name)


# ------------------------------------------------------------- transforms
def _scenes(d):
    return d["scenes"]


def _els(d, i):
    return d["scenes"][i]["elements"]


def _set_paper(d, asset):
    for i in PAPER_SCENES | DARK_SCENES:
        bg = _scenes(d)[i]["background"]
        bg["asset"] = asset
        bg["scrim"] = 0.0


def t_paper(d, name):
    _set_paper(d, name)


def t_dark_reel(d, asset=PAPER_PURPLE):
    """Every flat scene goes dark; light-theme text is re-inked."""
    _set_paper(d, asset)
    remap = {"purple": "white", "amber": "orange", "body": "soft",
             "muted": "line", "ink": "white"}
    for i in PAPER_SCENES | {6}:
        for el in _els(d, i):
            for key in ("color",):
                if el.get(key) in remap:
                    el[key] = remap[el[key]]
            if isinstance(el.get("colors"), list):
                el["colors"] = [remap.get(c, c) for c in el["colors"]]
            for key in ("fill", "num_color", "text_color"):
                if el.get(key) in remap:
                    el[key] = remap[el[key]]
            if el.get("kind") in ("panel", "tag"):
                if el.get("kind") == "panel":
                    el.setdefault("fill", "purple2")
            if el.get("kind") == "photo":
                pass
            if el.get("chips"):
                el["chips"] = {k: ("purple2" if v == "purple" else v)
                               for k, v in el["chips"].items()}
        _scenes(d)[i]["theme"] = "dark"
    # CTA pill stays orange; the phone number keeps ink — white on orange
    # measures only ~2.2:1 and fails the large-text contrast floor.
    for el in _els(d, 13):
        if el.get("role") == "phone":
            el["color"] = "ink"


def t_dark_mixed(d):
    """Only the middle acts go dark — paper bookends, dark core."""
    for i in (5, 10):
        bg = _scenes(d)[i]["background"]
        bg["asset"] = PAPER_PURPLE
        _scenes(d)[i]["theme"] = "dark"
        remap = {"purple": "white", "amber": "orange", "body": "soft",
                 "muted": "line"}
        for el in _els(d, i):
            if el.get("color") in remap:
                el["color"] = remap[el["color"]]
            if isinstance(el.get("colors"), list):
                el["colors"] = [remap.get(c, c) for c in el["colors"]]


def t_mono_purple(d):
    """Every accent collapses to purple/ink — strict duotone look."""
    for i in range(len(_scenes(d))):
        for el in _els(d, i):
            if el.get("color") in ("amber", "orange"):
                el["color"] = "purple" if i not in DARK_SCENES | PHOTO_SCENES \
                    else "white"
            if isinstance(el.get("colors"), list):
                el["colors"] = [
                    "purple" if c in ("amber", "orange")
                    and i not in DARK_SCENES | PHOTO_SCENES else
                    ("white" if c == "orange" else c)
                    for c in el["colors"]]
            for key in ("num_color",):
                if el.get(key) in ("amber", "orange"):
                    el[key] = "purple"
            if el.get("kind") == "band":
                el["fill"] = "purple"
            if el.get("role") == "cta-pill":
                el["fill"] = "purple"
            if el.get("role") == "phone":
                el["color"] = "white"
            if el.get("kind") == "ring":
                el["color"] = "purple"
                for dot in el.get("dots") or []:
                    dot["color"] = "purple"
            if el.get("kind") == "ticks":
                el["color"] = "purple"
            if el.get("kind") == "path" and el.get("color") == "orange":
                el["color"] = "purple"


def t_orange_punch(d):
    """Amber/orange takes over every accent — single-colour energy."""
    for i in range(len(_scenes(d))):
        for el in _els(d, i):
            target = "amber" if i in PAPER_SCENES and i not in DARK_SCENES \
                else "orange"
            if el.get("color") == "purple":
                el["color"] = target
            if isinstance(el.get("colors"), list):
                el["colors"] = [target if c == "purple" else c
                                for c in el["colors"]]
            if el.get("num_color") == "purple":
                el["num_color"] = target
            if el.get("text_color") == "purple":
                el["text_color"] = "purple"   # keep tag labels readable
            if el.get("kind") == "band":
                el["fill"] = "orange"
                el["opacity"] = 0.88
                for el2 in _els(d, i):
                    if el2.get("kind") == "words" and \
                            el2.get("color") in ("white", "orange"):
                        el2["color"] = "ink"
            if el.get("kind") == "ring":
                el["color"] = target
            if el.get("kind") == "ticks":
                el["color"] = "purple"


def t_motion(d, preset):
    for s in _scenes(d):
        for el in s["elements"]:
            if el.get("kind") in ("words", "bigtext") and \
                    el.get("preset", "pop") == "pop":
                el["preset"] = preset


def t_card(d, mode):
    for s in _scenes(d):
        for el in s["elements"]:
            if el.get("kind") != "photo":
                continue
            if mode == "bare":
                el["frame"] = "none"
                el["radius"] = 22
            elif mode == "thick":
                el["pad"] = 34
            elif mode == "tilt":
                el["rotation"] = float(el.get("rotation", 0)) * 2.1
                el["spin"] = 8.0
            elif mode == "level":
                el["rotation"] = 0.0
                el["spin"] = 0.0


def t_band(d, fill, opacity=None, text=None):
    for i in PHOTO_SCENES:
        for el in _els(d, i):
            if el.get("kind") == "band":
                el["fill"] = fill
                if opacity is not None:
                    el["opacity"] = opacity
            if text and el.get("kind") == "words":
                el["color"] = text


def t_transitions(d, seq):
    for i, s in enumerate(_scenes(d)):
        if "transition_out" in s:
            s["transition_out"]["type"] = seq[i % len(seq)]


def t_align_left(d):
    for i in PAPER_SCENES:
        for el in _els(d, i):
            if el.get("kind") == "words" and \
                    el.get("role") not in ("pill",) and \
                    el.get("size", 0) >= 60:
                el["align"] = "left"
                el["x"] = 0.085


def t_hook(d, text, colors=None):
    el = _els(d, 0)[2]
    el["text"] = text
    if colors:
        el["colors"] = colors


def t_reorder(d, order):
    """order maps position -> source index (equal-duration slots only)."""
    movable = [3, 6, 7, 8, 9, 10]
    src = [_scenes(d)[i] for i in movable]
    for pos, idx in zip(movable, order):
        _scenes(d)[pos] = src[movable.index(idx)]


def t_photo_swap(d, mapping):
    for idx, src in mapping.items():
        for el in _els(d, idx):
            if el.get("kind") == "photo":
                el["src"] = src


def t_cta(d, mode):
    els = _els(d, 13)
    if mode == "purple_pill":
        for el in els:
            if el.get("role") == "cta-pill":
                el["fill"] = "purple"
            if el.get("role") == "phone":
                el["color"] = "white"
    elif mode == "text_only":
        els[:] = [el for el in els if el.get("role") != "cta-pill"]
        for el in els:
            if el.get("role") == "phone":
                el["color"] = "purple"
                el["size"] = 76
                el["y"] = 0.66
    elif mode == "site_focus":
        for el in els:
            if el.get("role") == "phone":
                el["size"] = 52
            if el.get("role") == "site":
                el["size"] = 48
                el["color"] = "purple"
                el["uppercase"] = True


def t_stats(d, mode):
    if mode == "minimal":
        _els(d, 5)[:] = [el for el in _els(d, 5)
                         if el.get("role") != "orbit"]
    elif mode == "big":
        for el in _els(d, 5):
            if el.get("role") == "stat":
                el["size"] = 330
    elif mode == "halo_dark":
        _els(d, 6).insert(0, {
            "kind": "ring", "role": "halo", "cx": 0.5, "cy": 0.44,
            "r": 0.34, "width": 6, "color": "purple2", "onset": 1.9,
            "dur": 0.9,
            "dots": [{"angle": -30, "color": "orange", "r": 10,
                      "onset": 2.5}]})


def t_remove_decor(d):
    for s in _scenes(d):
        s["elements"] = [el for el in s["elements"]
                         if el.get("kind") not in ("ring", "ticks", "sweep",
                                                   "path")]


def t_chips_more(d):
    """Highlight the last word of big light-scene lines with ink chips."""
    for i in (0, 1, 10):
        for el in _els(d, i):
            if el.get("kind") == "words" and el.get("size", 0) >= 80:
                words = el["text"].split()
                chips = {str(len(words) - 1): "purple"}
                el["chips"] = chips
                colors = list(el.get("colors") or [el.get("color", "purple")]
                              * len(words))
                colors[-1] = "white"
                el["colors"] = colors


def t_ticks_all(d):
    for i, s in enumerate(_scenes(d)):
        if i in PHOTO_SCENES:
            continue
        photos = [el for el in s["elements"] if el.get("kind") == "photo"]
        for j, ph in enumerate(photos):
            rect = list(ph["rect"])
            rect = [rect[0] - .03, rect[1] - .03,
                    rect[2] + .06, rect[3] + .06]
            s["elements"].insert(-1 if s["elements"] else 0, {
                "kind": "ticks", "role": f"t{j}", "rect": rect,
                "color": "purple" if s.get("theme") == "light" else "orange",
                "thickness": 4, "onset": ph.get("onset", 0) + .25,
                "stagger": .12})


def t_count_color(d, color):
    for el in _els(d, 5):
        if el.get("role") == "stat":
            el["color"] = color


TRANSITION_SETS = {
    "mix_a": ["whip-pan", "diagonal-wipe", "stripe-reveal", "zoom-through",
              "split-slide", "radial-reveal"],
    "mix_b": ["diagonal-wipe", "split-slide", "whip-pan", "stripe-reveal",
              "zoom-through", "diagonal-wipe"],
    "takeover": ["color-takeover"] * 6,
    "whip": ["whip-pan"] * 6,
    "zoom": ["zoom-through", "spin-zoom", "zoom-through", "spin-zoom"],
    "iris": ["iris-close-open", "radial-reveal", "diagonal-wipe",
             "split-slide"],
    "pixel": ["pixel-dissolve", "diagonal-wipe", "stripe-reveal"],
    "cut": None,   # removes transition_out -> hard cuts
}


# --------------------------------------------------------------- variants
# Every entry: slug -> ordered transforms on top of the QA-clean base.
VARIANTS = [
    ("v01-channel",          [("t_paper", PAPER)]),
    ("v02-mono-purple",      [("t_mono_purple",)]),
    ("v03-orange-punch",     [("t_orange_punch",)]),
    ("v04-night-purple",     [("t_dark_reel", PAPER_PURPLE)]),
    ("v05-ink-edition",      [("t_dark_reel", PAPER_INK)]),
    ("v06-soft-lavender",    [("t_paper", PAPER_SOFT)]),
    ("v07-left-editorial",   [("t_align_left",)]),
    ("v08-bare-photos",      [("t_card", "bare")]),
    ("v09-tilted",           [("t_card", "tilt")]),
    ("v10-rise-motion",      [("t_motion", "rise")]),
    ("v11-fade-motion",      [("t_motion", "fade")]),
    ("v12-minimal",          [("t_remove_decor",), ("t_stats", "minimal")]),
    ("v13-bands-orange",     [("t_band", "orange", .9, "ink")]),
    ("v14-bands-ink",        [("t_band", "ink", .88, "white")]),
    ("v15-takeover-cuts",    [("t_transitions", "takeover")]),
    ("v16-zoom-cuts",        [("t_transitions", "zoom")]),
    ("v17-photo-alt",        [("t_photo_swap", {
        0: "media/bess/magazyny-energii-pure-energy.webp",
        1: "media/bess/centrum-handlowe.webp",
        9: "media/bess/bess-kontener-pv.webp"})]),
    ("v18-hook-koniec",      [("t_hook", "KONIEC Z PRZEPŁACANIEM.",
                              ["purple", "purple", "amber"])]),
    ("v19-hook-tani",        [("t_hook", "TANI PRĄD W SZCZYCIE.",
                              ["amber", "purple", "purple", "purple"])]),
    ("v20-reorder-proof",    [("t_reorder", [10, 6, 7, 8, 3, 9])]),
    ("v21-cta-purple",       [("t_cta", "purple_pill")]),
    ("v22-night-ink-bands",  [("t_dark_reel", PAPER_INK),
                              ("t_band", "purple", .92, "white")]),
    ("v23-lavender-left",    [("t_paper", PAPER_SOFT), ("t_align_left",)]),
    ("v24-mono-bare",        [("t_mono_purple",), ("t_card", "bare")]),
    ("v25-dark-orange-band", [("t_dark_reel", PAPER_PURPLE),
                              ("t_band", "orange", .9, "ink")]),
    ("v26-chips",            [("t_chips_more",)]),
    ("v27-stat-big",         [("t_stats", "big"), ("t_count_color", "purple")]),
    ("v28-ticks-everywhere", [("t_ticks_all",)]),
    ("v29-mixed-dark",       [("t_dark_mixed",),
                              ("t_transitions", "iris")]),
    ("v30-cta-text",         [("t_cta", "text_only"),
                              ("t_band", "purple", .95, "orange")]),
]


def build_variant(slug: str, ops: list[tuple]) -> dict:
    d = json.loads(BASE.read_text(encoding="utf-8"))
    d["name"] = f"pure-energy-bess-{slug}"
    for op in ops:
        name, *args = op
        fn = globals()[name]
        if name == "t_transitions":
            fn(d, TRANSITION_SETS[args[0]] if args[0] else [])
        else:
            fn(d, *args)
    return d


def write_variants() -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ensure_textures()
    written = []
    for slug, ops in VARIANTS:
        d = build_variant(slug, ops)
        if d["scenes"] and d["scenes"][0] is None:
            raise ValueError(slug)
        path = OUT_DIR / f"{slug}.json"
        path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        written.append(path)
        print("wrote", path.name)
    return written


def render_all(jobs: int, supersample: int, only: list[str]) -> None:
    manifests = sorted(OUT_DIR.glob("v*.json"))
    if only:
        manifests = [m for m in manifests
                     if any(o in m.name for o in only)]
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    cache = ROOT / ".cache/studio-variants"
    pending = []
    for m in manifests:
        out = RENDER_DIR / f"{m.stem}.mp4"
        if out.is_file() and out.stat().st_size > 0:
            print("skip (exists)", out.name)
            continue
        pending.append((m, out))
    print(f"{len(pending)} renders queued, jobs={jobs}, ss={supersample}")
    running: list[tuple[subprocess.Popen, Path, float]] = []
    failed = []
    while pending or running:
        while pending and len(running) < jobs:
            m, out = pending.pop(0)
            cmd = [str(ROOT / ".venv/bin/python"), str(BUILDER),
                   "--render", "--manifest", str(m), "--output", str(out),
                   "--supersample", str(supersample),
                   "--cache-dir", str(cache)]
            log = open(out.with_suffix(".log"), "w")
            proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT,
                                    cwd=ROOT)
            running.append((proc, out, time.monotonic()))
            print("start", m.stem, flush=True)
        done = [r for r in running if r[0].poll() is not None]
        for proc, out, started in done:
            running.remove((proc, out, started))
            mins = (time.monotonic() - started) / 60
            if proc.returncode == 0 and out.is_file():
                print(f"done  {out.name} in {mins:.1f} min", flush=True)
            else:
                print(f"FAIL  {out.name} (see {out.with_suffix('.log')})",
                      flush=True)
                failed.append(out.name)
        if running:
            time.sleep(5)
    if failed:
        print("FAILED:", ", ".join(failed))
        sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--render-all", action="store_true")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--supersample", type=int, default=1)
    parser.add_argument("--only", nargs="*", default=[])
    args = parser.parse_args()
    if args.write or not args.render_all:
        write_variants()
    if args.render_all:
        render_all(args.jobs, args.supersample, args.only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
