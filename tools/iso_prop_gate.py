#!/usr/bin/env python3
"""One-command quality gate for an iso gallery prop or world.

Runs the full loop in order and fails fast::

    .venv/bin/python tools/iso_prop_gate.py render.png \\
        --plate plate.png --brief "what the subject should be" \\
        --ensemble nvidia-direct

Exit code is 0 only when the pixel pre-check AND every LLM judge pass.
NEVER present a prop to the owner without a 0 from this gate in hand.
"""
from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, "tools")

from PIL import Image

from iso_prop_critique import critique as pixel_critique
from iso_prop_critic_llm import critique as llm_critique, merge_verdicts

try:
    from iso_layer_audit import audit_one as _audit_one

    _HAVE_AUDIT = True
except ImportError:
    _HAVE_AUDIT = False


def is_stale_render(src_path, img_path, tol_s=2.0):
    """True when the builder source is newer than the render: the PNG
    predates its own code (playbook rule 17 — the 50-minute-old-render
    trap). Missing files never count as stale (fail-open here; the
    pixel/audit stages own missing-input errors)."""
    import os as _os

    try:
        return (_os.path.getmtime(src_path)
                - _os.path.getmtime(img_path)) > tol_s
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", help="gallery render PNG")
    parser.add_argument("--plate", required=True,
                        help="clean-plate PNG (shell without the subject)")
    parser.add_argument("--brief", required=True,
                        help="what the subject should be")
    parser.add_argument("--provider", default="nvidia")
    parser.add_argument("--ensemble", default="nvidia-direct",
                        help="comma-separated extra judges (fail-closed)")
    parser.add_argument("--audit", default="",
                        help=("layer-audit label for this prop, e.g. "
                              "props_heat_a.manifold or manifold; runs "
                              "the exact-touch scan as third gate"))
    args = parser.parse_args()

    with Image.open(args.image) as im, Image.open(args.plate) as plate:
        pixel = pixel_critique(im, plate)
    print("pixel ok:", pixel["ok"],
          "issues:", [(i["code"], i["severity"]) for i in pixel["issues"]])
    if not pixel["ok"]:
        print("GATE: FAIL (pixel pre-check)")
        return 1
    if args.audit:
        if not _HAVE_AUDIT:
            print("GATE: FAIL (layer audit unavailable)")
            return 1
        from iso_layer_audit import (  # noqa: E402 - optional gate pillar
            BATCH_MODULES,
            LEGACY,
            _paint_legacy,
            _paint_registry,
        )
        import importlib as _il

        painter = None
        src_file = None
        for name, fn_name, pos, kwargs, focus_pt, k in LEGACY:
            if args.audit == name:
                painter = (lambda n=name, f=fn_name, p=pos, kw=kwargs,
                            fp=focus_pt, kk=k:
                           _paint_legacy(n, f, p, kw, fp, kk))
                src_file = "src/reels_maker/iso/world.py"
        if painter is None:
            for module_name in BATCH_MODULES:
                try:
                    module = _il.import_module(
                        f"reels_maker.iso.{module_name}")
                except ImportError:
                    continue
                for prop, spec in getattr(module, "PROPS", {}).items():
                    label = f"{module_name}.{prop}"
                    if args.audit in (prop, label):
                        painter = (lambda m=module_name, p=prop, s=spec:
                                   _paint_registry(m, p, s))
                        src_file = (f"src/reels_maker/iso/"
                                    f"{module_name}.py")
        if painter is None:
            print(f"GATE: FAIL (unknown audit label: {args.audit})")
            return 1
        # Rule 17: refuse a stale render — the builder source moved
        # after the PNG was made (the 50-minute-old-render trap).
        import os as _os
        _root = _os.path.dirname(_os.path.dirname(
            _os.path.abspath(__file__)))
        _src = _os.path.join(_root, src_file)
        if is_stale_render(_src, args.image):
            _gap = (_os.path.getmtime(_src)
                    - _os.path.getmtime(args.image))
            print(f"GATE: FAIL (stale render: {src_file} is "
                  f"{_gap:.0f}s newer than {args.image} — "
                  "re-render first, then gate)")
            return 1
        report = _audit_one(args.audit, painter)
        print(f"layers ok: {not report['errors']} "
              f"errors={len(report['errors'])} "
              f"triage-warnings={len(report.get('warnings', []))}")
        for warn in report.get("warnings", [])[:4]:
            print(" ~", warn["detail"])
        for err in report["errors"][:6]:
            print(" -", err["detail"])
        if report["status"] != "ok" or report["errors"]:
            print("GATE: FAIL (layer audit)")
            return 1

    providers = [args.provider] + [p.strip()
                                   for p in args.ensemble.split(",")
                                   if p.strip()]
    reports = []
    for provider in providers:
        try:
            reports.append((provider, llm_critique(args.image, args.brief,
                                                   provider=provider)))
        except Exception as exc:  # noqa: BLE001 - fail-closed, see below
            reports.append((provider, {"verdict": "error",
                                       "summary": str(exc)[:200]}))
    merged = merge_verdicts(args.image, reports)
    for provider, report in reports:
        print(f"judge {provider}: {report.get('verdict')}"
              f" {report.get('score')}")
    for issue in merged.get("issues", [])[:10]:
        print(" -", issue.get("judge"), issue.get("severity"), "|",
              issue.get("area"), "|", (issue.get("what") or "")[:110])
    print("GATE:", "PASS" if merged["verdict"] == "pass" else "FAIL",
          merged.get("score"), "|", merged.get("summary"))
    return 0 if merged["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
