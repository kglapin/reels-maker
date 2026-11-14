"""Executable craft recipes. Heuristics never certify visual quality."""
from __future__ import annotations
import copy
import math

SOURCES = {
    "carbon": "https://carbondesignsystem.com/guidelines/motion/overview/",
    "material": "https://m1.material.io/motion/choreography.html",
    "apple": "https://developer.apple.com/design/human-interface-guidelines/motion",
}
RECIPES = {
    "editorial-statement": ("statement", "headline", (), ("apple", "carbon")),
    "photo-proof": ("split-editorial", "visual", ("asset",), ("material", "apple")),
    "metric-proof": ("amount", "amount", ("value",), ("carbon", "apple")),
    "data-story": ("line-chart", "visual", ("chart",), ("material", "apple")),
    "portfolio": ("photo-carousel", "visual", ("assets",), ("material", "carbon")),
    "quiet-resolution": ("statement", "headline", (), ("apple", "carbon")),
}


def recipe_catalog():
    return {"schema_version": 1, "recipes": [
        {"id": key, "composition": value[0], "focus": value[1],
         "requires": list(value[2]), "status": "experimental", "visual_approval": None,
         "invariants": ["Preserve supplied copy, units, values and assets",
                        "One primary attention target; supporting copy follows",
                        "Never invent contact details or data"],
         "source_urls": [SOURCES[s] for s in value[3]]}
        for key, value in RECIPES.items()],
        "limitations": ["Original recipes, not transcriptions of third-party films.",
                        "UI guidance does not define universal film durations.",
                        "Actual render, audio, rights and human review remain required."]}


def _finite(value):
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value))


def select_recipe(shot):
    explicit = shot.get("layout", "auto")
    if explicit == "auto":
        explicit = shot.get("composition", "auto")
    if shot.get("chart") is not None:
        return "data-story"
    if shot.get("assets"):
        return "portfolio"
    if explicit not in ("auto", "statement", "amount", "split-editorial",
                        "line-chart", "photo-carousel", "photo-marquee"):
        return None
    if shot.get("intent", "").strip().lower() in ("cta", "finale", "resolution"):
        return "quiet-resolution"
    if shot.get("asset"):
        return "photo-proof"
    if explicit == "amount" and _finite(shot.get("value")):
        return "metric-proof"
    return "editorial-statement"


def _choreography(shot, focus, motion):
    duration = float(shot.get("duration", 2.8))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Scene duration must be positive and finite")
    gap = min(.22, duration * .08)
    # Do not emit timing/preset entries for nodes this scene does not create.
    present = []
    if shot.get("asset") or shot.get("assets") or shot.get("chart"):
        present.append("visual")
    if _finite(shot.get("value")):
        present.append("amount")
    if shot.get("headline"):
        present.append("headline")
    if shot.get("subtitle"):
        present.append("body")
    roles = ([focus] if focus in present else [])
    roles.extend(role for role in ("headline", "body")
                 if role in present and role not in roles)
    if not roles:
        roles = present
    order = list(dict.fromkeys(roles))
    cues = {role: round(index * gap, 4) for index, role in enumerate(order)}
    chars = len(str(shot.get("headline", ""))) + len(str(shot.get("subtitle", "")))
    minimum_hold = max(1.0, chars / 16.0)
    transition = shot.get("transition") or {}
    exit_allowance = (float(transition.get("duration", .4))
                      if transition.get("type", "cut") != "cut" else 0.0)
    available = duration - max(cues.values()) - .75 - exit_allowance
    issues = []
    if available < minimum_hold:
        issues.append({"code": "craft_reading_hold_review", "severity": "warning",
                       "message": "Short estimated hold; shorten copy or add time/shots.",
                       "estimated_hold_s": round(available, 3),
                       "suggested_hold_s": round(minimum_hold, 3)})
    entrance_presets = {role: (motion if role == focus else "fade-up")
                        for role in roles}
    return {"cues": cues,
            "entrance_presets": entrance_presets}, {
        "focus": focus, "order": order, "estimated_hold_s": round(available, 3),
        "reading_characters_per_second": 16.0,
        "timing_basis": "authored estimate; inspect actual node tracks and MP4",
        "issues": issues}


def refine_plan(spec, legacy_plan):
    """Refine automatic Studio choices without altering explicit author choices.

    Camera Canvas remains unchanged pending visual parity verification.
    The compiler consumes scene_defaults; this is not a parallel renderer.
    """
    result = copy.deepcopy(legacy_plan)
    if spec.get("mode", "studio") != "studio":
        return result
    shots = spec.get("shots", [])
    if len(shots) != len(result):
        raise ValueError("Shot/decision count mismatch")
    previous = None
    for shot, decision in zip(shots, result):
        if decision.get("id") != shot.get("id"):
            raise ValueError("Shot/decision identity mismatch")
        recipe_id = select_recipe(shot)
        if recipe_id is None:
            previous = None
            continue
        composition, focus, required, source_ids = RECIPES[recipe_id]
        if any(key not in shot for key in required):
            raise ValueError("Recipe prerequisites missing: " + recipe_id)
        requested = shot.get("layout", "auto")
        if requested == "auto":
            requested = shot.get("composition", "auto")
        if requested != "auto":
            decision["layout"] = requested
        else:
            decision["layout"] = composition
            decision["layout_reason"] = {"decision": "craft_recipe", "recipe": recipe_id}
        motion = shot.get("typography", {}).get("family", "auto")
        if motion == "auto":
            motion = "fade-up"
            decision["typography_motion"] = motion
            decision["motion_reason"] = {"decision": "craft_coherence", "effect": motion,
                                         "recipe": recipe_id,
                                         "reason": "Coherent copy grammar; no variety override"}
        defaults, choreography = _choreography(shot, focus, motion)
        decision["scene_defaults"] = defaults
        decision["craft"] = {
            "recipe_id": recipe_id, "recipe_status": "experimental", "visual_approval": None,
            "choreography": choreography,
            "connection": {"previous_recipe": previous,
                           "outgoing_method": "authored_transition" if shot.get("transition") else "cut",
                           "shared_object_continuity_verified": False},
            "source_urls": [SOURCES[key] for key in source_ids],
            "limitations": ["Planning heuristics, not aesthetic scoring.",
                            "No automatic morph/shared-object continuity is claimed."]}
        previous = recipe_id
    return result


def plan_issues(plan):
    return [{"shot_id": decision["id"], **copy.deepcopy(issue)}
            for decision in plan
            for issue in decision.get("craft", {}).get("choreography", {}).get("issues", [])]


def calibration_report(expected, predicted):
    """Measure critic A/B choices against externally reviewed, held-out cases."""
    if not isinstance(expected, dict) or not expected or not isinstance(predicted, dict):
        raise ValueError("Nonempty mappings of case IDs to A/B choices required")
    if set(expected) != set(predicted):
        raise ValueError("Calibration case IDs must match exactly")
    if any(not isinstance(key, str) or not key.strip() for key in expected):
        raise ValueError("Nonempty string case IDs required")
    if any(value not in ("A", "B") for value in [*expected.values(), *predicted.values()]):
        raise ValueError("Choices must be A or B")
    correct = sum(expected[key] == predicted[key] for key in expected)
    return {"cases": len(expected), "correct": correct,
            "accuracy": correct / len(expected), "certifies_aesthetic_quality": False,
            "limitations": ["Expected choices need independent human review.",
                            "Use held-out clips and randomize sides.",
                            "Synthetic defects alone do not establish creative judgment."]}


def compile_professional_spec(spec, *, source_dir=".", root=None, check_assets=True):
    """Compile recipe-directed intent through the existing validated compiler.

    This additive entry point does not change legacy plan_shots/render defaults.
    Its output is a normal Studio manifest accepted by studio-qa/studio-render.
    """
    from .spec import validate_creative_spec
    from .director import plan_shots
    from .compiler import compile_creative_spec
    from .quality import audit_creative_spec
    validate_creative_spec(spec)
    directed = refine_plan(spec, plan_shots(spec))
    prepared = copy.deepcopy(spec)
    for shot, decision in zip(prepared["shots"], directed):
        shot["layout"] = decision["layout"]
        shot.setdefault("typography", {})["family"] = decision["typography_motion"]
    manifest, report = compile_creative_spec(
        prepared, source_dir=source_dir, root=root, check_assets=check_assets)
    for scene, decision in zip(manifest["scenes"], directed):
        scene.update(copy.deepcopy(decision.get("scene_defaults", {})))
    qa = audit_creative_spec(prepared, manifest, source_dir=source_dir, root=root)
    craft_issues = plan_issues(directed)
    qa["issues"].extend(craft_issues)
    qa["warnings"] += len(craft_issues)
    report["craft_decisions"] = directed
    report["warnings"].extend(craft_issues)
    report["qa"] = qa
    report["craft_status"] = "experimental"
    report["visual_approval"] = None
    return manifest, report


def main(argv=None):
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description="Compile experimental craft recipes using the existing engine")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-warnings", action="store_true",
                        help="Export a review manifest with warnings; never a creative approval")
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.spec.read_text(encoding="utf-8"))
        manifest, report = compile_professional_spec(
            data, source_dir=args.spec.parent, root=args.root)
        qa = report["qa"]
        if not qa["ok"] or (qa["warnings"] and not args.allow_warnings):
            print(json.dumps({"status": "review_required", "report": report}, ensure_ascii=False))
            return 2
        output = args.output.resolve()
        report_path = output.with_suffix(".craft-report.json")
        if output == args.spec.resolve() or report_path == args.spec.resolve():
            raise ValueError("Output must not overwrite the input")
        if output.exists() or report_path.exists():
            raise ValueError("Output or report already exists; choose a new versioned path")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        with report_path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"status": "compiled_for_review", "manifest": str(output),
                          "report": str(report_path), "visual_approval": None}, ensure_ascii=False))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
