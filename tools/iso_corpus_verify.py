"""Full-corpus deterministic verification (playbook rules 15-17).

Label-driven: for every gallery prop, paints a FRESH render + plate
from current code, runs the pixel pre-check and the layer audit.
No LLM quota spent (ensemble stays per-change); no filename mapping
needed (paints by label, not by gallery file).

Usage: .venv/bin/python tools/iso_corpus_verify.py
Exit 0 only when every prop has 0 audit errors and pixel ok.
Prints a JSON summary; failures list labels with reasons.
"""
import sys

sys.path.insert(0, "src")
sys.path.insert(0, ".")

from reels_maker.iso.projection import (  # noqa: E402
    DEFAULT_PALETTE, Canvas)
from reels_maker.iso.film import focus  # noqa: E402
import tools.iso_layer_audit as A  # noqa: E402
import tools.iso_phantom_sheets as S  # noqa: E402
from tools.iso_prop_critique import critique as pixel_critique  # noqa: E402


# Documented framing intent, eye-verified 2026-11-12 (gallery PNGs
# read correctly; the rigid "cropped" rule cannot know intent).
# A FIFTH cropper is a real failure — never extend this silently.
KNOWN_CROPPED = {
    "boilerroom": "room interior, walls bleed off-frame by design",
    "battery": "tall cabinet, full-height framing, crown at edge",
    "switchgear": "tall cabinet, full-height framing, crown at edge",
    # PV keeps the custom wide frame AND the bleed exemption: even
    # the approved banner (07-pv.png) bleeds L/R by panoramic intent
    # (owner verdict 2026-11-12); judges are overruled separately.
    "pv": "panoramic strip, panels bleed L/R by design",
}

# Props whose approved form is a non-standard aspect (eye-verified
# against the shipped gallery file). Framed here, not exempted.
CUSTOM_FRAME = {
    "pv": (1152, 312),  # panoramic strip, matches 07-pv.png
}


def _frame(img, label):
    """Gallery-parity framing: standard 768-wide, or the prop's
    approved custom aspect (center-cropped, like the shipped file)."""
    if label in CUSTOM_FRAME:
        w, h = CUSTOM_FRAME[label]
        img = img.resize((w, round(w * img.height / img.width)))
        top = max(0, (img.height - h) // 2)
        return img.crop((0, top, w, top + h))
    return img.resize((768, round(768 * img.height / img.width)))


def _plate_only(label, size):
    """Gallery-convention clean plate: plinth only, no subject."""
    from PIL import Image as _I
    if "." in label:
        import importlib as _il
        module_name, prop = label.split(".", 1)
        spec = _il.import_module(
            f"reels_maker.iso.{module_name}").PROPS[prop]
        k, origin = focus(spec["focus"], spec["k"])
        q = Canvas(DEFAULT_PALETTE["bg"], k, origin)
        return q.im.convert("RGB").resize(size)
    return _I.new("RGB", size, tuple(DEFAULT_PALETTE["bg"][:3]))


def main():
    pts = S.painters()
    P = dict(DEFAULT_PALETTE)
    ok_all, failures, warnings_total = True, {}, 0
    n_pixel_fail, n_warn = 0, 0
    for label, (real_fn, audit_fn) in pts.items():
        try:
            q_rec = audit_fn()
        except Exception as exc:  # noqa: BLE001
            failures[label] = [f"paint error: {exc!r}"[:160]]
            ok_all = False
            continue
        errors, warnings = A.audit_calls(q_rec, q_rec.calls)
        errs = [e for e in errors if e["code"] != "phantom-cap"]
        errs += [e for e in errors if e["code"] == "phantom-cap"]
        try:
            img = real_fn(dict(P)).im.convert("RGB")
            plate_img = _plate_only(label, img.size)
            rep = pixel_critique(_frame(img, label),
                                 _frame(plate_img, label))
        except Exception as exc:  # noqa: BLE001
            failures[label] = [f"render/pixel error: {exc!r}"[:160]]
            ok_all = False
            continue
        reasons = []
        if not rep.get("ok"):
            codes = [i.get("code", "?") for i in rep.get("issues", [])]
            if (set(codes) <= {"cropped"} and label in KNOWN_CROPPED):
                reasons.append("pixel: cropped (KNOWN INTENT: "
                               + KNOWN_CROPPED[label] + ")")
            else:
                reasons.append("pixel: " + ",".join(codes[:4]))
                n_pixel_fail += 1
        if errs:
            reasons += [e["detail"][:100] for e in errs[:4]]
        if warnings:
            n_warn += 1
            warnings_total += len(warnings)
        if reasons:
            failures[label] = reasons
            if errs or (not rep.get("ok")
                        and "KNOWN INTENT" not in ";".join(reasons)):
                ok_all = False
    import json
    print(json.dumps({"props": len(pts),
                      "failed": sorted(failures),
                      "pixel_failures": n_pixel_fail,
                      "props_with_triage_warnings": n_warn,
                      "triage_warnings_total": warnings_total,
                      "detail": failures},
                     ensure_ascii=False, indent=1)[:4000])
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
