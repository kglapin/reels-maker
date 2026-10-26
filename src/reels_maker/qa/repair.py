"""Repair checks for Studio QA."""
from __future__ import annotations

from ..core.scene_graph import Node, collect_qa_elements
from ..design.tokens import is_vertical_reels_canvas
from ..design.typography_policy import audit_typography_blocks, audit_typography_spacing
from ..textkit.typesetter import FontBook
from .data import _data_checks
from .geometry import (
    _collisions, _safe_area, _text_blocks, _text_ink_safe_area,
    _vertical_reels_content_zone, sample_geometry_frames,
)
from .models import Issue



def _evaluate_built_scene_qa(built, *, fps: int = 30, samples_per_scene: int = 6) -> list[Issue]:
    from types import SimpleNamespace
    frames = max(2, round(float(built.duration) * fps))
    timing = SimpleNamespace(frames=frames)
    samples = sample_geometry_frames(built, timing, fps, samples_per_scene=samples_per_scene)
    vertical_reels = is_vertical_reels_canvas(
        built.context.width, built.context.height)
    issues: list[Issue] = _vertical_reels_content_zone(built)
    seen: set[tuple] = set()
    for local_frame in samples:
        t = local_frame / fps
        nodes = built.at(t)
        elems: list[dict] = []
        for node in nodes:
            elems.extend(collect_qa_elements(node))
        for issue in (
            ([] if vertical_reels else _safe_area(
                elems, built, t, local_frame))
            + _collisions(elems, set(), built, t, local_frame)
            + ([] if vertical_reels else _text_ink_safe_area(
                nodes, built, t, local_frame))
        ):
            sig = (issue.code, tuple(issue.elements))
            if sig not in seen:
                seen.add(sig)
                issues.append(issue)
    # Reuse measured type rules in storyboard candidate QA and layout repair.
    for finding in audit_typography_blocks(
            _text_blocks(Node(kind="group", children=built.at(0.0))),
            width=built.context.width, height=built.context.height):
        issues.append(Issue(
            finding["code"], finding["severity"], finding["message"],
            built.index + 1, None, [finding["role"]], finding["suggestion"]))
    for finding in audit_typography_spacing(
            ((node.role, node.meta.get("bounds")) for node in built.elements.values()),
            width=built.context.width, height=built.context.height):
        issues.append(Issue(
            finding["code"], finding["severity"], finding["message"],
            built.index + 1, None, [finding["role"]], finding["suggestion"]))
    issues.extend(_data_checks(built))
    return issues


def repair_scene_layout(
    ctx,
    scene: Mapping[str, object],
    *,
    max_retries: int = 3,
    fps: int = 30,
    samples_per_scene: int = 6,
) -> dict:
    """Deterministic frame-based QA repair loop with bounded retries and audit report (MD-404)."""
    from dataclasses import replace
    from ..components.scenes import build_scene
    from ..layout.composition_optimizer import solve_scene_layout

    if type(max_retries) is not int or not 1 <= max_retries <= 5:
        raise ValueError("max_retries must be an integer between 1 and 5")

    attempts: list[dict] = []
    current_scene = dict(scene)
    current_ctx = ctx

    def try_build_and_check(attempt_no: int, action: str, candidate_ctx, candidate_scene: dict):
        built = build_scene(candidate_ctx, candidate_scene)
        found = _evaluate_built_scene_qa(
            built, fps=fps, samples_per_scene=samples_per_scene
        )
        errors = [i for i in found if i.severity == "error"]
        warnings = [i for i in found if i.severity == "warning"]
        # Typography aesthetic/semantic warnings require editorial review.
        # They must not make the automatic repair loop shrink readable text or
        # reject a successfully repaired geometry/hold purely on aesthetics.
        repairable_warnings = [i for i in warnings
                               if not i.code.startswith("typography_")]
        attempts.append({
            "attempt": attempt_no,
            "action": action,
            "composition": candidate_scene.get("composition"),
            "errors": len(errors),
            "warnings": len(warnings),
            "repairable_warnings": len(repairable_warnings),
            "issues": [i.to_dict() for i in found],
        })
        return built, errors, repairable_warnings

    built0, errors0, warnings0 = try_build_and_check(0, "initial", current_ctx, current_scene)
    if not errors0 and not warnings0:
        return {
            "ok": True,
            "repaired": False,
            "attempts": attempts,
            "scene": current_scene,
            "built": built0,
        }

    best_built = built0
    best_scene = current_scene
    best_score = (len(errors0), len(warnings0))

    repair_plan = [
        ("layout_solver", None),
        ("compact_typography_90_and_quiet_motion", 0.90),
        ("compact_typography_80_and_extend_hold", 0.80),
    ][:max_retries]

    for retry_idx, (action, scale_factor) in enumerate(repair_plan, 1):
        trial_scene = dict(current_scene)
        trial_ctx = current_ctx
        if action == "layout_solver" and not trial_scene.get("type"):
            solved = solve_scene_layout(
                trial_ctx, trial_scene, fps=fps, samples_per_scene=samples_per_scene
            )
            if solved["selected_built"] is not None:
                selected_comp = next(
                    c["layout"] for c in solved["candidates"]
                    if c["candidate_id"] == solved["selected_id"]
                )
                trial_scene["composition"] = selected_comp
        elif scale_factor is not None:
            t_type = trial_ctx.tokens.typography
            scaled_type = replace(
                t_type,
                display=max(48, round(t_type.display * scale_factor)),
                hero=max(40, round(t_type.hero * scale_factor)),
                title=max(28, round(t_type.title * scale_factor)),
                subtitle=max(20, round(t_type.subtitle * scale_factor)),
                body=max(16, round(t_type.body * scale_factor)),
            )
            scaled_tokens = replace(trial_ctx.tokens, typography=scaled_type)
            new_duration = float(trial_scene.get("duration", trial_ctx.duration))
            if action.endswith("extend_hold"):
                new_duration = min(15.0, new_duration + 0.8)
                trial_scene["duration"] = new_duration
            trial_scene["typography_motion"] = "fade-up"
            trial_ctx = replace(trial_ctx, tokens=scaled_tokens, duration=new_duration)

        built_i, errors_i, warnings_i = try_build_and_check(
            retry_idx, action, trial_ctx, trial_scene
        )
        score_i = (len(errors_i), len(warnings_i))
        if score_i < best_score:
            best_built = built_i
            best_scene = trial_scene
            best_score = score_i
        if not errors_i and not warnings_i:
            return {
                "ok": True,
                "repaired": True,
                "attempts": attempts,
                "scene": trial_scene,
                "built": built_i,
            }

    return {
        "ok": best_score[0] == 0,
        "repaired": best_score < (len(errors0), len(warnings0)),
        "attempts": attempts,
        "scene": best_scene,
        "built": best_built,
    }


def run_polish_typography_regression(
    fonts: FontBook | None = None,
    *,
    fps: int = 24,
) -> dict:
    """Verify all 8 text mechanism families with Polish diacritics across 4 aspect ratios (MD-306)."""
    from ..components.base import SceneContext
    from ..components.scenes import build_scene
    from ..design.tokens import resolve_tokens
    from ..motionkit.presets import text_mechanism_families

    fonts = fonts or FontBook()
    aspects = (
        ("portrait_9_16", 720, 1280),
        ("portrait_4_5", 720, 900),
        ("square_1_1", 720, 720),
        ("landscape_16_9", 1280, 720),
    )
    families = text_mechanism_families()
    results = []
    failures = []
    for aspect_name, w, h in aspects:
        tokens = resolve_tokens("editorial-premium", width=w, height=h)
        for family_name, spec in families.items():
            ctx = SceneContext(
                width=w, height=h, fps=fps, duration=3.0,
                tokens=tokens, style="editorial-premium", fonts=fonts,
            )
            scene = {
                "composition": "stack-center",
                "duration": 3.0,
                "kicker": "ZAŻÓŁĆ GĘŚLĄ JAŹŃ",
                "headline": "ŁĄCZNIE 19 000 ZŁ",
                "subtitle": "Źródło czystej energii — sprawdź oszczędności",
                "typography_motion": str(spec["preset"]),
            }
            built = build_scene(ctx, scene)
            issues = _evaluate_built_scene_qa(built, fps=fps, samples_per_scene=4)
            errors = [i.to_dict() for i in issues if i.severity == "error"]
            if errors:
                failures.append({
                    "aspect": aspect_name,
                    "family": family_name,
                    "preset": spec["preset"],
                    "errors": errors,
                })
            results.append({
                "aspect": aspect_name,
                "family": family_name,
                "preset": spec["preset"],
                "ok": not errors,
            })
    return {
        "ok": not failures,
        "combinations_checked": len(results),
        "aspects": [a[0] for a in aspects],
        "families": list(families),
        "failures": failures,
        "results": results,
    }
