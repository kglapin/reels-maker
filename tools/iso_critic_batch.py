#!/usr/bin/env python3
"""Batch LLM-critic sweep over every registry prop render.

Reads the painter PNGs produced by tools/iso_batch_audit.py
(renders/asta-energy/prop-audit/<batch>.<prop>.png), sends each to the
vision critic with its PROPS brief, and writes critic-results.json with
verdict/score/issues per prop. Concurrency via --jobs.

Usage::

    .venv/bin/python tools/iso_critic_batch.py [--jobs 6] [--provider nvidia]
"""
from __future__ import annotations

import argparse
import importlib
import json
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))

from tools.iso_prop_critic_llm import critique  # noqa: E402

BATCH_MODULES = [
    "props_buildings", "props_electro", "props_extra", "props_farm",
    "props_heat_a", "props_heat_b", "props_home2", "props_hvac2",
    "props_icons", "props_industry", "props_interior", "props_nature",
    "props_pv2", "props_roof", "props_small", "props_storage2",
    "props_street2", "props_tools",
]


def one(job):
    label, img, brief, provider = job
    try:
        r = critique(str(img), brief, provider=provider)
        return label, {"verdict": r.get("verdict"),
                       "score": r.get("score"),
                       "issues": r.get("issues"),
                       "summary": r.get("summary")}
    except Exception as exc:  # noqa: BLE001
        return label, {"error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--provider", default="nvidia")
    ap.add_argument("--audit-dir",
                    default="renders/asta-energy/prop-audit")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    audit = _ROOT / args.audit_dir
    jobs = []
    for mod_name in BATCH_MODULES:
        module = importlib.import_module(f"reels_maker.iso.{mod_name}")
        for prop, spec in getattr(module, "PROPS", {}).items():
            label = f"{mod_name}.{prop}"
            img = audit / f"{label}.png"
            if not img.is_file():
                continue
            jobs.append((label, img, spec.get("brief", ""), args.provider))

    results = {}
    done = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = [ex.submit(one, j) for j in jobs]
        for f in as_completed(futs):
            label, r = f.result()
            results[label] = r
            done += 1
            mark = "OK " if r.get("verdict") == "pass" else "!!!"
            print(f"[{done}/{len(jobs)}] {mark} {label} "
                  f"score={r.get('score')} "
                  f"issues={len(r.get('issues') or [])}", flush=True)

    out = _ROOT / (args.out or f"{args.audit_dir}/critic-results.json")
    fails = {k: v for k, v in results.items()
             if v.get("verdict") != "pass" or "error" in v}
    out.write_text(json.dumps({"results": results, "fails": fails},
                              ensure_ascii=False, indent=1))
    print(f"\n{len(results)} critiqued, {len(fails)} non-pass -> {out}")
    for k in sorted(fails):
        print(" FAIL", k, json.dumps(fails[k], ensure_ascii=False)[:300])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
