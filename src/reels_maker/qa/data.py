"""Data checks for Studio QA."""
from __future__ import annotations

import math

from ..textkit.typesetter import TextBlock
from .models import Issue



def _data_checks(built) -> list[Issue]:
    issues = []
    scene = built.scene
    meta = built.meta
    if meta.get("component") == "breakdown":
        items = meta.get("items") or []
        total = float(meta.get("total", 0))
        if items and abs(sum(float(item["value"]) for item in items) - total) > .01:
            issues.append(Issue(
                "declared_data_mismatch", "error",
                "Breakdown items do not sum to the declared total.",
                built.index + 1, None, [],
                "Correct the manifest values before rendering."))
    if meta.get("component") == "timeline" and scene.get("budget_consumption_shown"):
        issues.append(Issue(
            "unverified_data_visualisation", "error",
            "The scene claims budget consumption without verified data.",
            built.index + 1, None, [],
            "Remove the consumption bar or provide an audited data source."))
    for key in ("value", "total", "percent"):
        if key in meta:
            value = meta[key]
            if isinstance(value, (int, float)) and not math.isfinite(float(value)):
                issues.append(Issue(
                    "invalid_number", "error", f"{key} is not a finite number.",
                    built.index + 1, None, [], "Fix the manifest value."))
    if meta.get("component") in (
        "table", "line_chart", "bars", "stacked_bars_100",
        "waterfall", "diverging_bar", "bullet", "heatmap",
        "scatter", "funnel", "sankey",
    ):
        issues.extend(audit_data_scene(built))
    return issues


def audit_data_scene(built, *, min_mobile_px: int = 11) -> list[Issue]:
    """Mobile legibility, non-truncation and reading-hold QA for charts and tables (DM-007)."""
    issues: list[Issue] = []
    scale = min(built.context.width, built.context.height) / 1080.0
    min_px = max(9.0, min_mobile_px * scale)
    for root in built.nodes:
        for node in root.flatten():
            block = node.props.get("block")
            if isinstance(block, TextBlock):
                if block.truncated:
                    issues.append(Issue(
                        "data_label_truncated",
                        "error",
                        f"Data scene element {node.role!r} truncated its text.",
                        built.index + 1,
                        None,
                        [node.role],
                        "Widen column, paginate rows or shorten label copy.",
                    ))
                if block.style.size < min_px - 1e-6:
                    issues.append(Issue(
                        "mobile_text_too_small",
                        "error",
                        f"Data scene text {node.role!r} is {block.style.size:.1f}px (< {min_px:.1f}px mobile floor).",
                        built.index + 1,
                        None,
                        [node.role],
                        "Reduce row/column count or increase text size for mobile legibility.",
                    ))
    # Verify minimum reading hold for data visualizations
    entries = getattr(built.choreography, "entries", {}) or {}
    latest_settle = max(
        (float(e.onset) + float(e.duration) for e in entries.values()),
        default=0.0,
    )
    hold_window = float(built.duration) - latest_settle
    if hold_window < 0.55:
        issues.append(Issue(
            "data_reading_hold_short",
            "warning",
            f"Data visualization hold window is {hold_window:.2f}s (< 0.55s).",
            built.index + 1,
            None,
            [],
            "Extend scene duration or shorten entrance stagger so viewers can read the data.",
        ))
    return issues
