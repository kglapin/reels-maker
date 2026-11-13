"""Regression lock for iso layer discipline (see docs/iso-prop-playbook.md).

Fails when ANY registered prop paints an exact-touch mating seam
(upper bottom == lower top): those alias into hairline gaps. Buried
detail dots are reported for triage but never fail the suite: hidden
hardware (rail bolts, concealed fasteners) is legitimately covered.
"""
import sys
import unittest

sys.path.insert(0, "src")
sys.path.insert(0, ".")

from tools.iso_layer_audit import (  # noqa: E402
    BATCH_MODULES,
    LEGACY,
    _paint_legacy,
    _paint_registry,
    audit_calls,
)


def _iter_targets():
    for name, fn_name, pos, kwargs, focus_pt, k in LEGACY:
        yield name, lambda n=name, f=fn_name, p=pos, kw=kwargs, fp=focus_pt, \
            kk=k: _paint_legacy(n, f, p, kw, fp, kk)
    import importlib

    for module_name in BATCH_MODULES:
        try:
            module = importlib.import_module(f"reels_maker.iso.{module_name}")
        except ImportError:
            continue
        for prop, spec in getattr(module, "PROPS", {}).items():
            yield f"{module_name}.{prop}", \
                lambda m=module_name, p=prop, s=spec: _paint_registry(m, p, s)


class LayerAuditTest(unittest.TestCase):
    def test_no_exact_touch_seams(self):
        failures = {}
        for label, painter in _iter_targets():
            try:
                q = painter()
            except Exception as exc:  # noqa: BLE001 - reported, not raised
                failures[label] = [f"paint error: {exc!r}"]
                continue
            errors, _warnings = audit_calls(q, q.calls)
            if errors:
                failures[label] = [e["detail"] for e in errors]
        self.assertEqual(
            failures, {},
            f"{sum(len(v) for v in failures.values())} exact-touch seams "
            "across gallery props; mates must overlap >= 0.005")


if __name__ == "__main__":
    unittest.main()
