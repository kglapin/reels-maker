"""Curated craft references for motion direction and conservative preflight QA.

Sources are editorial *inspiration*, never downloadable/copyable render assets.
No model or unverified visual classifier is used. Automated signals cannot
certify premium aesthetics; final MP4/audio/rights review remains human-gated.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
from collections import Counter
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

from .spec import validate_creative_spec


def _check_unique_ids(items, label):
    ids = [entry.get("id") for entry in items]
    if any(not isinstance(item, str) or not item for item in ids):
        raise ValueError(f"{label} must have nonempty string IDs")
    if len(set(ids)) != len(ids):
        raise ValueError(f"{label} contains duplicate IDs")
    return set(ids)


def validate_reference_library(library):
    """Reject malformed, untraceable source or practice records."""
    if not isinstance(library, dict) or library.get("schema_version") != 1:
        raise ValueError("Reference library requires schema_version=1")
    for key in ("sources", "principles", "anti_patterns", "recipes"):
        if not isinstance(library.get(key), list) or not library[key]:
            raise ValueError(f"Reference library requires nonempty {key}")
    sources = _check_unique_ids(library["sources"], "sources")
    for source in library["sources"]:
        if not isinstance(source.get("url"), str) or not source["url"].startswith("https://"):
            raise ValueError("Every source must have an HTTPS citation")
        if not source.get("title") or not source.get("craft"):
            raise ValueError("Every source needs a title and craft takeaway")
    principles = _check_unique_ids(library["principles"], "principles")
    _check_unique_ids(library["anti_patterns"], "anti_patterns")
    _check_unique_ids(library["recipes"], "recipes")
    for rule in library["principles"]:
        if not rule.get("rule") or not set(rule.get("source_ids", [])).issubset(sources):
            raise ValueError(f"Untraceable principle {rule.get('id')}")
        if not rule.get("source_ids"):
            raise ValueError(f"Principle {rule['id']} needs source citations")
    for recipe in library["recipes"]:
        if not recipe.get("sequence") or not set(recipe.get("reference_ids", [])).issubset(sources):
            raise ValueError(f"Invalid recipe {recipe.get('id')}")
    policy = library.get("heuristic_policy", {})
    if not isinstance(policy, dict) or not policy.get("human_gate_dimensions"):
        raise ValueError("Reference library missing human review policy")
    return {"valid": True, "sources": len(sources), "principles": len(principles),
            "anti_patterns": len(library["anti_patterns"]), "recipes": len(library["recipes"])}


@lru_cache(maxsize=1)
def _cached_library():
    path = files("reels_maker.creative").joinpath("reference_data/library.json")
    with path.open("r", encoding="utf-8") as handle:
        library = json.load(handle)
    validate_reference_library(library)
    return library


def load_reference_library():
    """Return a defensive copy; supported in installed wheels and editable mode."""
    return copy.deepcopy(_cached_library())


def _normalise(value):
    return " ".join(str(value).casefold().split())


def _recipe_match(spec, recipes):
    direction = _normalise(spec.get("creative_direction", ""))
    tokens = set(re.findall(r"[\w-]+", direction))
    tokens.update(_normalise(shot.get("intent", "")) for shot in spec["shots"])
    chart_scene = any(shot.get("chart") for shot in spec["shots"])
    scored = []
    for recipe in recipes:
        score = 1 if recipe.get("style") == spec.get("style", "editorial-premium") else 0
        score += sum(2 for term in recipe.get("use_for", []) if term.replace("_", " ") in direction or term in tokens)
        if chart_scene and recipe["id"] == "R03":
            score += 8
        scored.append((score, recipe["id"], recipe))
    return sorted(scored, key=lambda x: (-x[0], x[1]))[0][2]


def reference_guidance(spec):
    """Provide an agent-readable recipe and cited craft rules before authoring."""
    validate_creative_spec(spec)
    library = load_reference_library()
    recipe = _recipe_match(spec, library["recipes"])
    sources = {item["id"]: item for item in library["sources"]}
    return {
        "schema_version": 1,
        "library_updated_on": library["updated_on"],
        "recipe": copy.deepcopy(recipe),
        "source_links": [{"id": sid, "url": sources[sid]["url"]}
                         for sid in recipe["reference_ids"]],
        "principles": copy.deepcopy(library["principles"]),
        "anti_patterns": copy.deepcopy(library["anti_patterns"]),
        "human_review_dimensions": library["heuristic_policy"]["human_gate_dimensions"],
        "note": "This is craft guidance, not a learned aesthetic score or permission to reuse source media.",
    }


def audit_reference_quality(spec, manifest=None):
    """Flag high-signal AI-slop risks without claiming visual inspection.

    Designed for Creative Spec v1. These heuristics are intentionally warnings
    except for literal unfinished placeholders, which are indisputable errors.
    """
    validate_creative_spec(spec)
    library = load_reference_library()
    policy = library["heuristic_policy"]
    shots = spec["shots"]
    issues = []

    def add(severity, code, path, message, rule_ids, suggestion):
        issues.append({"severity": severity, "code": code, "path": path,
                       "message": message, "reference_rules": list(rule_ids),
                       "suggestion": suggestion})

    placeholders = tuple(_normalise(x) for x in policy["forbidden_placeholders"])
    for idx, shot in enumerate(shots):
        path = f"$.shots[{idx}]"
        combined = " ".join(str(shot.get(k, "")) for k in ("headline", "subtitle", "kicker"))
        lowered = _normalise(combined)
        if any(fragment in lowered for fragment in placeholders):
            add("error", "reference_unfinished_placeholder", path,
                "A placeholder appears in the final on-screen copy.", ["P01", "P14"],
                "Replace all dummy copy with approved, factual content.")
        subtitle = str(shot.get("subtitle", ""))
        duration = float(shot.get("duration", 2.8))
        if (len(subtitle) >= policy["minimum_subtitle_length_for_density_test"]
                and len(subtitle) / duration > policy["subtitle_reading_characters_per_second"]):
            add("warning", "reference_dense_subtitle", path + ".subtitle",
                "Subtitle is too dense for the available scene duration (estimated).",
                ["P04", "P05", "A04"], "Split into separate beats or extend the readable hold.")

    if len(shots) >= policy["min_shots_for_rhythm_test"]:
        durations = [float(shot.get("duration", 2.8)) for shot in shots]
        if max(durations) - min(durations) <= policy["equal_duration_tolerance_seconds"]:
            add("warning", "reference_flat_rhythm", "$.shots",
                "All scenes have almost identical durations; inspect repetitive template pacing.",
                ["P03", "A01"], "Vary pacing based on information load and audio cues.")
        if not str(spec.get("creative_direction", "")).strip():
            add("warning", "reference_direction_missing", "$.creative_direction",
                "Multi-shot project lacks an explicit visual and narrative direction.",
                ["P01", "P10"], "Describe concept, core motif, evidence and motion restraint.")
    if len(shots) >= 3:
        headlines = Counter(_normalise(shot["headline"]) for shot in shots)
        if max(headlines.values()) >= 3:
            add("warning", "reference_recycled_headline", "$.shots",
                "Identical headline repeats in three or more scenes.",
                ["P01", "A01"], "Progress the story rather than repeating the same title.")

    cliches = set(policy["marketing_cliches"])
    found = sorted(x for x in cliches
                   if any(x in _normalise(str(shot["headline"]) + " " + str(shot.get("subtitle", "")))
                          for shot in shots))
    if len(found) >= policy["marketing_cliche_threshold"]:
        add("warning", "reference_generic_copy", "$.shots",
            "Multiple generic advertising superlatives; verify that claims have concrete proof.",
            ["P01", "P12", "A02"], "Replace empty adjectives with facts, comparisons or a demonstration.")

    libraries = {_normalise(shot.get("icon_library")) for shot in shots if shot.get("icon_library")}
    if len(libraries) > 1:
        add("warning", "reference_icon_family_mix", "$.shots",
            "Different icon packs used within one video sequence.",
            ["P09", "A06"], "Use a single consistent pack, weight and optical size.")

    asset_counts = Counter(shot["asset"] for shot in shots if shot.get("asset"))
    if any(count > policy["max_same_asset_count"] for count in asset_counts.values()):
        add("warning", "reference_asset_overuse", "$.shots",
            "One still image appears excessively across scenes.",
            ["P06", "A05", "A10"], "Use additional authentic angles or visual proof.")

    manual = ["Review the actual MP4 on a phone with and without sound.",
              "Assess continuity, visual hierarchy, easing, compositing and Polish typography.",
              "Validate music, footage, SVG, trademarks and publication rights.",
              "Check photosensitive flashing in encoded video, including transition flashes.",
              "Ensure every concrete number and marketing claim has evidence."]
    if any(shot.get("chart") for shot in shots):
        add("warning", "reference_chart_source_review", "$.shots",
            "Chart values are specified, but Creative Spec v1 has no provenance field.",
            ["P08", "A07"], "Verify source, period, unit, denominator, transformations and final frames.")
        manual.append("Compare each chart/table state to the immutable source dataset.")

    recipe = _recipe_match(spec, library["recipes"])
    return {
        "schema_version": 1,
        "library_updated_on": library["updated_on"],
        "recommended_recipe_id": recipe["id"],
        "reference_urls": [item["url"] for item in library["sources"]
                           if item["id"] in recipe["reference_ids"]],
        "issues": issues,
        "errors": sum(item["severity"] == "error" for item in issues),
        "warnings": sum(item["severity"] == "warning" for item in issues),
        "human_approval_required": True,
        "manual_checklist": manual,
        "limitations": [
            "This pass does not view actual footage, audio, render or source citations.",
            "It cannot prove aesthetic quality, factual accuracy or WCAG compliance.",
            "The hard rejection applies to unfinished placeholders only; other detections are conservative editorial warnings.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Machine-readable curated motion-design craft reference guide")
    parser.add_argument("--spec", type=Path, help="Creative Spec v1 JSON to match to a recipe")
    parser.add_argument("--audit", action="store_true", help="With --spec, return reference anti-slop preflight")
    args = parser.parse_args(argv)
    if args.audit and args.spec is None:
        parser.error("--audit requires --spec")
    if args.spec:
        with args.spec.open(encoding="utf-8") as handle:
            spec = json.load(handle)
        result = audit_reference_quality(spec) if args.audit else reference_guidance(spec)
    else:
        library = load_reference_library()
        result = {"status": "ok", **validate_reference_library(library), "library": library}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
