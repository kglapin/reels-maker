"""Editorial quality checks: detect generic AI-generated motion-design tropes.

These are warnings, not automatic aesthetic judgments. Specific branded
campaigns can intentionally opt into these treatments.
"""
from __future__ import annotations


def audit_editorial_style(scene: dict) -> list[dict]:
    issues = []
    def warn(code, message):
        issues.append({"code": code, "message": message})
    if scene.get("decor") is True:
        warn("ornamental_decor", "Decorative bars, blobs and dots are enabled; remove unless they communicate meaning.")
    background = scene.get("background") or {}
    if isinstance(background, dict) and background.get("kind") == "gradient":
        warn("generic_gradient", "Gradient background: verify it serves the brand and composition.")
    if scene.get("icon_assets") and len(scene["icon_assets"]) > 3:
        warn("icon_overload", "More than three free-floating icons; simplify the composition.")
    headline = scene.get("headline") or {}
    if isinstance(headline, dict):
        runs = headline.get("runs") or []
        if len(runs) >= 5:
            warn("fragmented_typography", "Headline uses too many styled runs; restore clear typographic hierarchy.")
        accent_count = sum(1 for run in runs if isinstance(run, dict)
                           and run.get("color") == "accent")
        if accent_count > 2:
            warn("excessive_accent", "Too many accent-colored text fragments; emphasize one main idea.")
    transition = scene.get("transition_out") or {}
    if isinstance(transition, dict) and transition.get("type") in (
            "pixel-dissolve", "spin-zoom", "stripe-reveal"):
        warn("novelty_transition", "Decorative transition may distract from the narrative; review frame by frame.")
    return issues
