"""Deterministic creative decisions, candidate ranking and diverse motion.

Director recommends explicit, renderer-supported choices. It does not pretend
to use learned aesthetic judgement or hallucinate missing media.
"""
from __future__ import annotations
from ..layout.composition_optimizer import CompositionCandidate, evaluate_candidates
from .registry import CAMERA_LAYOUTS, STUDIO_COMPOSITIONS, CAMERA_TEXT_MOTIONS
from ..motionkit.presets import PRESETS

SEMANTIC_MOTION={
    "intro":"mask-rise",
    "opening":"mask-rise",
    "reveal":"tracking-in",
    "proof":"scale-focus",
    "statistics":"scale-focus",
    "compare":"slide-left",
    "comparison":"slide-left",
    "finale":"pop-settle",
    "cta":"pop-settle",
    "explain":"word-cascade",
    "process":"word-cascade",
}
CAMERA_MOTION={
    "opening":"mask-rise",
    "reveal":"scale-focus",
    "proof":"slide-up",
    "explain":"mask-rise",
    "finale":"scale-focus",
}

def _family(preset):
    if preset in ("fade-up","rise","slide-left","slide-right"):
        return "translation"
    if preset in ("mask-rise","reveal-right","word-cascade"):
        return "masked"
    if preset in ("tracking-in",):
        return "letter-geometry"
    if preset in ("pop-settle","scale-focus"):
        return "scale"
    return "static"

def _candidate_score(layout,index,shot,mode):
    # Deterministic and explainable heuristic baseline, not semantic AI.
    length=len(str(shot.get("headline","")))
    subject=shot.get("visual","")
    placement={
        "photo-above":.94 if length>21 else .86,
        "photo-left":.70 if length>24 else .91,
        "offset":.87,
        "diagonal":.90 if index%2 else .79,
        "statement":.86,
        "split-editorial":.90 if shot.get("asset") else .74,
        "stack-center":.81,
        "full-bleed-type":.70 if length>20 else .86,
        "spotlight":.83,
    }.get(layout,.75)
    focus=.91 if shot.get("asset") else .80
    return {
        "hierarchy":placement,
        "legibility":.92 if length<30 else .76,
        "subject_retention":focus,
        "balance":min(.96,placement+.02),
        "continuity":.84 if index%2==0 else .90,
        "brand":.89,
    }

def choose_layout(shot,index,mode,used):
    requested=shot.get("layout",shot.get("composition","auto"))
    if requested!="auto":
        return requested,{"decision":"explicit","layout":requested}
    menu=(CAMERA_LAYOUTS if mode=="camera_canvas" else
          ("statement","split-editorial","stack-center","spotlight"))
    scores=[]
    for i,layout in enumerate(menu):
        metrics=_candidate_score(layout,index,shot,mode)
        # penalize same adjacent layout through balance/continuity.
        if used and used[-1]==layout:
            metrics["continuity"]=.38
        scores.append(CompositionCandidate(
            candidate_id=f"{index}-{i}-{layout}",layout=layout,
            scores=metrics,element_count=3 if shot.get("asset") else 2))
    report=evaluate_candidates(scores)
    selected=next(c for c in scores if c.candidate_id==report["selected_id"])
    return selected.layout,{"decision":"candidate_ranking","layout":selected.layout,
                        "candidate_count":len(scores),
                        "reason":"heuristic hierarchy, legibility and continuity"}

def choose_typography(shot,index,mode,used):
    explicit=shot.get("typography",{}).get("family","auto")
    if explicit!="auto":
        return explicit,{"decision":"explicit","effect":explicit}
    intent=str(shot.get("intent","")).lower()
    if mode=="camera_canvas":
        menu=list(CAMERA_TEXT_MOTIONS)
        preferred=CAMERA_MOTION.get(intent,menu[index%len(menu)])
    else:
        menu=list(PRESETS)
        preferred=SEMANTIC_MOTION.get(intent,("mask-rise","tracking-in",
                 "slide-left","scale-focus","word-cascade")[index%5])
    options=[preferred]+[m for m in menu if m!=preferred]
    if used:
        prev=_family(used[-1])
        # prefer a new motion mechanism over changing slide direction.
        for candidate in options:
            if _family(candidate)!=prev and candidate not in ("none",):
                return candidate,{"decision":"variety_override","effect":candidate,
                                  "avoided_previous":used[-1],"semantic_preference":preferred}
    return preferred,{"decision":"semantic_default","effect":preferred,"intent":intent}

def plan_shots(spec):
    """Returns complete reversible decisions for a Creative Spec."""
    mode=spec.get("mode","studio")
    layouts=[];motions=[];plan=[]
    for i,shot in enumerate(spec["shots"]):
        layout,layout_reason=choose_layout(shot,i,mode,layouts)
        motion,motion_reason=choose_typography(shot,i,mode,motions)
        layouts.append(layout);motions.append(motion)
        plan.append({
            "id":shot["id"],"layout":layout,"typography_motion":motion,
            "layout_reason":layout_reason,"motion_reason":motion_reason,
        })
    return plan


REFERENCE_RHYTHM_PROFILES = {
    "editorial-premium": (3.2, 2.8, 3.5, 2.6, 3.0),
    "kinetic-advertising": (2.2, 1.9, 2.5, 1.8, 2.4),
}


def match_reference_rhythm(
    shot_durations: list[float],
    *,
    style: str = "editorial-premium",
) -> dict:
    """Score shot duration cadence against reference-board rhythm templates (MD-505)."""
    if not shot_durations or any(d <= 0 for d in shot_durations):
        raise ValueError("shot_durations must be non-empty positive numbers")
    pattern = REFERENCE_RHYTHM_PROFILES.get(style, REFERENCE_RHYTHM_PROFILES["editorial-premium"])
    deltas = [
        abs(float(d) - pattern[idx % len(pattern)])
        for idx, d in enumerate(shot_durations)
    ]
    mean_delta = sum(deltas) / len(deltas)
    has_contrast = (max(shot_durations) - min(shot_durations)) >= 0.35 if len(shot_durations) >= 2 else True
    score = max(0.1, min(1.0, 1.0 - mean_delta / 3.0 - (0.0 if has_contrast else 0.15)))
    return {
        "style": style,
        "rhythm_score": round(score, 4),
        "has_pacing_contrast": has_contrast,
        "mean_deviation_s": round(mean_delta, 4),
    }


def rank_video_sources(
    candidates: list[dict],
    *,
    target_width: int = 1080,
    target_height: int = 1920,
    min_duration: float = 2.5,
) -> list[dict]:
    """Rank clean-source video clips by resolution, frame rate, duration and motion stability (MD-506)."""
    ranked = []
    for item in candidates:
        if not isinstance(item, dict):
            raise ValueError("video candidate must be a dict")
        state = str(item.get("editorial_state", "unreviewed"))
        if state != "clean_source":
            continue
        dur = float(item.get("duration", 0.0))
        if dur < min_duration:
            continue
        w = int(item.get("width", 0))
        h = int(item.get("height", 0))
        fps = float(item.get("fps", 24.0))
        stability = max(0.0, min(1.0, float(item.get("motion_stability", 0.85))))
        res_score = min(1.0, (w * h) / max(1, target_width * target_height))
        fps_score = min(1.0, fps / 30.0)
        score = round(0.40 * res_score + 0.35 * stability + 0.25 * fps_score, 4)
        ranked.append({**item, "quality_score": score})
    ranked.sort(key=lambda r: (-r["quality_score"], str(r.get("id", ""))))
    return ranked


def generate_and_select_storyboard(spec: dict) -> dict:
    """Generate 3 distinct storyboard candidates and choose the winner with measurable evidence (MD-508)."""
    import copy

    base_shots = spec.get("shots")
    if not isinstance(base_shots, list) or not base_shots:
        raise ValueError("spec requires non-empty shots")
    variants_cfg = (
        ("editorial-balanced", "editorial-premium", 1.0),
        ("kinetic-contrast", "kinetic-advertising", 0.90),
        ("visual-forward", "editorial-premium", 1.08),
    )
    candidates = []
    for var_id, style_name, dur_scale in variants_cfg:
        variant_spec = copy.deepcopy(spec)
        if style_name in ("editorial-premium", "kinetic-advertising"):
            variant_spec["style"] = style_name
        for idx, shot in enumerate(variant_spec["shots"]):
            base_d = float(shot.get("duration", 2.8))
            shot["duration"] = round(max(1.5, min(12.0, base_d * (dur_scale if idx % 2 == 0 else 1.0))), 2)
        shot_plan = plan_shots(variant_spec)
        durations = [float(s["duration"]) for s in variant_spec["shots"]]
        rhythm = match_reference_rhythm(durations, style=style_name)
        unique_layouts = len({p["layout"] for p in shot_plan})
        unique_motions = len({p["typography_motion"] for p in shot_plan})
        variety = min(1.0, (unique_layouts + unique_motions) / max(2, len(shot_plan) * 1.5))
        evidence_score = round(0.55 * rhythm["rhythm_score"] + 0.45 * variety, 4)
        candidates.append({
            "storyboard_id": var_id,
            "style": style_name,
            "plan": shot_plan,
            "rhythm": rhythm,
            "variety_score": round(variety, 4),
            "evidence_score": evidence_score,
        })
    candidates.sort(key=lambda c: (-c["evidence_score"], c["storyboard_id"]))
    winner = candidates[0]
    return {
        "selected_storyboard_id": winner["storyboard_id"],
        "selected": winner,
        "candidates": candidates,
    }


class PreferenceLibrary:
    """Human-feedback preference store gated on licensed/authorized reference provenance (MD-509)."""

    def __init__(self) -> None:
        self._entries: list[dict] = []

    def record(
        self,
        *,
        reference_id: str,
        intent: str,
        preferred_layout: str,
        preferred_motion: str,
        reviewer: str,
        license_name: str,
        rights_authorized: bool,
    ) -> dict:
        if not rights_authorized or not str(license_name or "").strip():
            raise ValueError(
                "PreferenceLibrary rejects unlicensed or unauthorized reference assets"
            )
        if not str(reference_id or "").strip() or not str(reviewer or "").strip():
            raise ValueError("reference_id and reviewer are required")
        entry = {
            "reference_id": str(reference_id).strip(),
            "intent": str(intent).strip().lower(),
            "preferred_layout": str(preferred_layout).strip(),
            "preferred_motion": str(preferred_motion).strip(),
            "reviewer": str(reviewer).strip(),
            "license": str(license_name).strip(),
            "rights_authorized": True,
        }
        self._entries.append(entry)
        return dict(entry)

    def recommend(self, intent: str) -> dict | None:
        key = str(intent or "").strip().lower()
        matches = [e for e in self._entries if e["intent"] == key]
        return dict(matches[-1]) if matches else None
