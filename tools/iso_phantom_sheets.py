"""Contact sheets of phantom-cap flags: fresh render + zoomed crop of each
flagged call's screen bbox, 20 cells per sheet. Triage evidence.

Usage: .venv/bin/python tools/iso_phantom_sheets.py
Reads flags from /tmp/phantom_audit.json, writes /tmp/phantom-NN.png.
"""
import importlib
import sys

sys.path.insert(0, "src")
sys.path.insert(0, ".")

from PIL import Image, ImageDraw  # noqa: E402

from reels_maker.iso.film import focus  # noqa: E402
from reels_maker.iso.projection import Canvas, DEFAULT_PALETTE  # noqa: E402
import tools.iso_layer_audit as A  # noqa: E402


def painters():
    """label -> (real_paint_fn, audit_paint_fn)."""
    out = {}
    for name, fn_name, pos, kwargs, focus_pt, k in A.LEGACY:
        out[name] = (
            lambda P, n=name, f=fn_name, p=pos, kw=kwargs, fp=focus_pt,
            kk=k: _paint_legacy_real(n, f, p, kw, fp, kk, P),
            lambda n=name, f=fn_name, p=pos, kw=kwargs, fp=focus_pt,
            kk=k: A._paint_legacy(n, f, p, kw, fp, kk))
    for module_name in A.BATCH_MODULES:
        try:
            module = importlib.import_module(f"reels_maker.iso.{module_name}")
        except ImportError:
            continue
        for prop, spec in getattr(module, "PROPS", {}).items():
            label = f"{module_name}.{prop}"
            out[label] = (
                lambda P, s=spec: _paint_reg_real(s, P),
                lambda m=module_name, p=prop,
                s=spec: A._paint_registry(m, p, s))
    return out


def _paint_legacy_real(name, fn_name, pos, kwargs, focus_pt, k, P):
    import reels_maker.iso.world as W  # noqa: E402
    fn = getattr(W, fn_name)
    kk, origin = focus(focus_pt, k)
    q = Canvas(P["bg"], kk, origin)
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


def _paint_reg_real(spec, P):
    kk, origin = focus(spec["focus"], spec["k"])
    q = Canvas(P["bg"], kk, origin)
    spec["fn"](q, 0.0, 0.15, P)
    return q


def _live_audit(pts):
    """Run the audit inline on the same painters (rule 16: no stale
    /tmp JSON handoff — evidence must match current code)."""
    reports = []
    for label, (_real_fn, audit_fn) in pts.items():
        try:
            rep = A.audit_one(label, audit_fn)
        except Exception as exc:  # noqa: BLE001
            print("audit fail", label, str(exc)[:100])
            continue
        reports.append(rep)
    return {"reports": reports}


def main():
    pts = painters()
    report = _live_audit(pts)
    P = dict(DEFAULT_PALETTE)
    cells = []
    missing = []
    for r in report["reports"]:
        flags = [e for e in r.get("errors", []) if e["code"] == "phantom-cap"]
        if not flags or r["prop"] not in pts:
            if flags:
                missing.append(r["prop"])
            continue
        real_fn, audit_fn = pts[r["prop"]]
        try:
            q_real = real_fn(P)
            q_rec = audit_fn()
        except Exception as exc:  # noqa: BLE001
            print("paint fail", r["prop"], str(exc)[:120])
            continue
        img = q_real.im
        for e in flags:
            try:
                b = A._bbox(q_rec, q_rec.calls[e["calls"][1]])
            except Exception as exc:  # noqa: BLE001
                print("bbox fail", r["prop"], e["calls"], str(exc)[:80])
                continue
            x0, y0, x1, y1 = [int(v) for v in b]
            pad = 90
            crop = img.crop((max(0, x0 - pad), max(0, y0 - pad),
                             min(img.width, x1 + pad),
                             min(img.height, y1 + pad)))
            sc = 500 / max(1, crop.width)
            crop = crop.resize((max(1, int(crop.width * sc)),
                                max(1, int(crop.height * sc))),
                               Image.LANCZOS)
            cells.append((r["prop"], e["calls"], e["detail"][:70], crop))
    print("cells:", len(cells), "| missing painters:", missing)
    TH = 250
    COLS = 5
    for s in range(0, len(cells), 20):
        chunk = cells[s:s + 20]
        rows = (len(chunk) + COLS - 1) // COLS
        sheet = Image.new("RGB", (COLS * TH, rows * (TH + 30)), (20, 30, 25))
        d = ImageDraw.Draw(sheet)
        for j, (prop, calls, detail, crop) in enumerate(chunk):
            c = crop.copy()
            c.thumbnail((TH, TH))
            x, y = (j % COLS) * TH, (j // COLS) * (TH + 30)
            sheet.paste(c, (x, y))
            d.text((x + 2, y + TH + 2), f"{prop} {calls}", fill=(255, 255, 0))
            d.text((x + 2, y + TH + 14), detail[:52], fill=(180, 220, 180))
        out = f"/tmp/phantom-{s // 20:02d}.png"
        sheet.save(out)
        print("wrote", out)


if __name__ == "__main__":
    main()
