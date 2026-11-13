#!/usr/bin/env python3
"""Regenerable prop catalog for ASTA Energy.

Usage::

    .venv/bin/python tools/iso_catalog.py

Rewrites ``brands/asta-energy/PROP-CATALOG.md`` from the live
registry (batch PROPS briefs + legacy builders): no hand-kept
lists, no stale titles.
"""
from __future__ import annotations

import importlib
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, _ROOT)

import tools.iso_layer_audit as A  # noqa: E402


def main() -> int:
    lines = ["# ASTA Energy — katalog elementów izometrycznych",
             "",
             "> Generowany automatycznie z rejestru builderów — nie "
             "edytować ręcznie. Regeneracja: "
             "`.venv/bin/python tools/iso_catalog.py`.",
             ""]
    total = 0
    for module_name in A.BATCH_MODULES:
        try:
            module = importlib.import_module(
                f"reels_maker.iso.{module_name}")
        except ImportError:
            continue
        props = getattr(module, "PROPS", {})
        if not props:
            continue
        lines.append(f"## {module_name} ({len(props)})")
        lines.append("")
        lines.append("| element | brief |")
        lines.append("|---|---|")
        for prop in sorted(props):
            brief = props[prop].get("brief", "")
            lines.append(f"| `{module_name}.{prop}` | {brief} |")
            total += 1
        lines.append("")
    lines.append(f"## Elementy klasyczne ({len(A.LEGACY)})")
    lines.append("")
    lines.append("| element |")
    lines.append("|---|")
    for name, *_ in A.LEGACY:
        lines.append(f"| `{name}` |")
        total += 1
    lines.append("")
    lines.append(f"Razem: **{total} elementów** "
                 f"(rendery: `renders/asta-energy/prop-galeria/`).")
    lines.append("")
    out = os.path.join(_ROOT, "brands", "asta-energy", "PROP-CATALOG.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"wrote {out} ({total} props)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
