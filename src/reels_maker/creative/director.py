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
    best,report=evaluate_candidates(scores)
    return best.layout,{"decision":"candidate_ranking","layout":best.layout,
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
