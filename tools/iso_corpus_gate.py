"""Full-corpus LLM-ensemble gate (owner request 2026-11-12).

For EVERY gallery prop: fresh render + plate from current code,
pixel pre-check, layer audit, then the two-judge vision ensemble
(nvidia via OpenRouter + nvidia-direct via Pi key) with the
one-retry wobble protocol (playbook rule 13).

Usage:
    .venv/bin/python tools/iso_corpus_gate.py [--limit N] [--redo]
Results append incrementally to /tmp/corpus_ensemble.json (resume:
recorded labels are skipped unless --redo). Stops after 5
consecutive provider/infra errors to protect quota.

Quota note: 1 OpenRouter call + 1 direct call per prop.
"""
import json
import os
import sys

sys.path.insert(0, "src")
sys.path.insert(0, ".")
sys.path.insert(0, "tools")

from reels_maker.iso.projection import DEFAULT_PALETTE  # noqa: E402
import tools.iso_layer_audit as A  # noqa: E402
import tools.iso_phantom_sheets as S  # noqa: E402
from tools.iso_corpus_verify import (  # noqa: E402
    KNOWN_CROPPED, _frame, _plate_only)
from tools.iso_prop_critique import critique as pixel_critique  # noqa: E402
from tools.iso_prop_critic_llm import (  # noqa: E402
    critique as llm_critique, merge_verdicts)

OUT = "/tmp/corpus_gate"
RES = "/tmp/corpus_ensemble.json"

# Owner verdicts that overrule the judges (never silent: stored on
# the record with the original issues). An override fires ONLY when
# every issue is framing-related; any other defect still fails.
JUDGE_OVERRIDES = {
    "pv": ("owner verdict 2026-11-12: panoramic edge-bleed is the "
           "approved intent (banner 07-pv.png); crop-criticism "
           "overruled"),
}
_OVERRIDE_KEYWORDS = ("crop", "edge", "cut off", "bleed", "fram")


def _overruled(label, merged):
    note = JUDGE_OVERRIDES.get(label)
    if not note or merged.get("verdict") == "pass":
        return None
    issues = merged.get("issues", [])
    if not issues:
        return None
    texts = " | ".join((i.get("area") or "") + " " + (i.get("what") or "")
                       for i in issues).lower()
    if all(any(k in t.lower() for k in _OVERRIDE_KEYWORDS)
           for t in texts.split(" | ")):
        return note
    return None


LEGACY_BRIEFS = {
    "buffer": "tall white buffer tank with black pipes, gauge and level bar",
    "controller": "wall thermostat controller with glass front and buttons",
    "radiator": "white panel radiator with copper pipes and valves",
    "battery": "tall white battery cabinet with charge bars and display",
    "inverter": "wall inverter box with screen and heatsink fins",
    "pv": "ground-mounted photovoltaic panel array, wide strip",
    "switchgear": "tall grey electrical switchgear cabinet with breakers",
    "capacitors": "capacitor bank with three cylindrical cans on rails",
    "meter": "electricity meter box on wall with dial",
    "vessel": "red expansion vessel tank on legs with gauge",
    "circulator": "circulation pump volute with motor and terminal box",
    "heatpump": "outdoor heat pump unit with fan grille and pipes",
    "compressor": "compressor unit on rails with copper discharge pipe",
    "thermostat": "round wall thermostat dial with display",
    "boilerroom": "boiler room interior with buffer tank and red boiler",
}


def _brief(label):
    if "." in label:
        import importlib as _il
        module_name, prop = label.split(".", 1)
        return _il.import_module(
            f"reels_maker.iso.{module_name}").PROPS[prop]["brief"]
    return LEGACY_BRIEFS[label]


import re as _re

_MISSING_IMG = _re.compile(
    r"render is missing|not provided|no image|only .*reference"
    r"|cannot see|blank image|image not available|not available"
    r" for visual|no .* provided for visual", _re.IGNORECASE)


def _judge(path, brief):
    """(merged, reports); fail-closed on provider errors.

    A 'fail' whose text says the judge never got the image is
    transport noise, not evidence: mark it provider-error so it
    retries and counts toward the infra abort instead of failing
    the prop (optimizer precedent 2026-11-12).
    """
    reports = []
    for provider in ("nvidia", "nvidia-direct"):
        try:
            rep = llm_critique(path, brief, provider=provider)
            blob = json.dumps(rep.get("issues", []) + [rep.get("summary",
                                                               "")],
                              ensure_ascii=False)
            if (rep.get("verdict") == "fail"
                    and _MISSING_IMG.search(blob)):
                rep = {"verdict": "error",
                       "summary": "judge reports missing image: "
                       + blob[:160]}
            reports.append((provider, rep))
        except Exception as exc:  # noqa: BLE001
            reports.append((provider, {"verdict": "error",
                                       "summary": str(exc)[:160]}))
    return merge_verdicts(path, reports), reports


def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]
                if "--limit" in sys.argv else 0)
    redo = "--redo" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    done = {}
    if os.path.exists(RES) and not redo:
        done = json.load(open(RES))
    pts = S.painters()
    labels = [l for l in pts if l not in done]
    if limit:
        labels = labels[:limit]
    print(f"corpus gate: {len(done)} recorded, {len(labels)} to run")
    consec_err = 0
    for n, label in enumerate(labels, 1):
        real_fn, audit_fn = pts[label]
        try:
            brief = _brief(label)
            img = real_fn(dict(DEFAULT_PALETTE)).im.convert("RGB")
            img_s = _frame(img, label)
            plate = _frame(_plate_only(label, img.size), label)
            safe = label.replace(".", "_")
            rp, pp = f"{OUT}/{safe}.png", f"{OUT}/{safe}-plate.png"
            img_s.save(rp)
            plate.save(pp)
            pixel = pixel_critique(img_s, plate)
            q = audit_fn()
            errors, _w = A.audit_calls(q, q.calls)
            pixel_ok = pixel.get("ok")
            if not pixel_ok:
                codes = [i.get("code", "?")
                         for i in pixel.get("issues", [])]
                if (set(codes) <= {"cropped"}
                        and label in KNOWN_CROPPED):
                    pixel_ok = True  # documented framing intent
            if not pixel_ok or errors:
                done[label] = {"verdict": "prefail",
                                "pixel_ok": pixel.get("ok"),
                                "audit_errors": len(errors)}
                print(f"[{n}/{len(labels)}] {label} PREFAIL "
                      f"(pixel ok={pixel.get('ok')} "
                      f"audit={len(errors)})")
                consec_err = 0
            else:
                merged, reports = _judge(rp, brief)
                if (merged.get("verdict") != "pass"
                        and not any(r[1].get("verdict") == "error"
                                    for r in reports)):
                    # Wobble protocol: one retry on identical pixels.
                    merged, reports = _judge(rp, brief)
                prov_err = [r for r in reports
                            if r[1].get("verdict") == "error"]
                if prov_err and merged.get("verdict") != "pass":
                    consec_err += 1
                else:
                    consec_err = 0
                override = _overruled(label, merged)
                done[label] = {
                    "verdict": ("pass-override" if override
                                else merged.get("verdict")),
                    "override": override,
                    "provider_detail": {
                        p: (r.get("summary") or "")[:160]
                        for p, r in reports
                        if r.get("verdict") == "error"},
                    "score": merged.get("score"),
                    "judges": {p: r.get("verdict") for p, r in reports},
                    "issues": [(i.get("judge"), i.get("severity"),
                                (i.get("what") or "")[:80])
                               for i in merged.get("issues", [])[:6]],
                    "summary": (merged.get("summary") or "")[:200]}
                print(f"[{n}/{len(labels)}] {label} "
                      f"{merged.get('verdict')} {merged.get('score')} "
                      f"{done[label]['judges']}")
            json.dump(done, open(RES, "w"), ensure_ascii=False)
            if consec_err >= 5:
                print("ABORT: 5 consecutive provider errors "
                      "(quota/infra) — results kept, resume later")
                return 2
        except KeyboardInterrupt:
            print("interrupted — results kept, resume later")
            json.dump(done, open(RES, "w"), ensure_ascii=False)
            return 3
        except Exception as exc:  # noqa: BLE001
            done[label] = {"verdict": "harness-error",
                           "summary": str(exc)[:160]}
            json.dump(done, open(RES, "w"), ensure_ascii=False)
            print(f"[{n}/{len(labels)}] {label} HARNESS-ERROR {exc}")
    verdicts = {}
    for v in done.values():
        verdicts[v["verdict"]] = verdicts.get(v["verdict"], 0) + 1
    print("CORPUS GATE:", verdicts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
