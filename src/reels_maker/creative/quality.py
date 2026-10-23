"""Structural and camera-safe creative QA before and after compilation.

Automated heuristics flag predictable problems; this is not a substitute for
render sampling and an editorial review of the actual MP4.
"""
from __future__ import annotations
import math
from pathlib import Path
from PIL import Image
from .spec import validate_creative_spec
from .compiler import compile_creative_spec

def audit_creative_spec(spec,manifest=None,*,source_dir=".",root=None):
    validated=validate_creative_spec(spec)
    if manifest is None:
        manifest,_=compile_creative_spec(spec,source_dir=source_dir,root=root)
    issues=[]
    def issue(severity,code,path,message):
        issues.append({"severity":severity,"code":code,"path":path,
                       "message":message})
    mode=validated["mode"]
    w,h=validated["width"],validated["height"]
    used=[]
    for i,(shot,scene) in enumerate(zip(spec["shots"],manifest["scenes"])):
        path=f"$.shots[{i}]"
        duration=float(scene["duration"])
        motion=(scene.get("camera_canvas") or {})
        if mode=="camera_canvas":
            hold=duration-(0 if i==0 else motion["move_duration"]) - (
                motion["reveal_delay"]+motion["reveal_duration"])
            if hold<.6:
                issue("error","insufficient_reading_hold",path,
                      f"{max(0,hold):.2f}s available; need at least 0.60s after typography enters")
            if motion["zoom"]<.85:
                issue("warning","camera_safe_zoom",path+".camera.zoom",
                      "Zoom below .85 may crop camera-facing content")
            if i and abs(motion["angle"]-manifest["scenes"][i-1]["camera_canvas"]["angle"])>240:
                issue("warning","large_camera_rotation",path+".camera.angle",
                      "Large turn may be hard to follow without a longer travel")
            if i and duration< motion["move_duration"]+motion["reveal_delay"]+motion["reveal_duration"]+.6:
                issue("error","animation_exceeds_shot",path,
                      "Travel + entrance leaves insufficient settled reading time")
        else:
            if duration<1.1:
                issue("warning","fast_studio_shot",path+".duration",
                      "Short scene may not provide sufficient reading time")
        text=str(shot["headline"])
        if len(text)>55:
            issue("warning","long_headline",path+".headline",
                  "Headline may require uncomfortable font scaling or wrapping")
        asset=scene.get("photo")
        if asset:
            file=Path(asset)
            if not file.is_file():
                issue("error","missing_asset",path+".asset",f"File missing: {file}")
            else:
                try:
                    with Image.open(file) as pic:
                        pw,ph=pic.size
                        if min(pw,ph)<min(w,h)*.45:
                            issue("warning","low_resolution_asset",path+".asset",
                                  "Source photo resolution may be insufficient for crop")
                        if pw*ph>60_000_000:
                            issue("warning","huge_asset",path+".asset",
                                  "Large source should be preprocessed for efficient rendering")
                except (OSError,ValueError) as exc:
                    issue("error","invalid_asset",path+".asset",str(exc))
        used.append(motion.get("typography_motion",scene.get("typography_motion")))
        if len(used)>=3 and used[-1]==used[-2]==used[-3]:
            reason=shot.get("allow_repeat_reason")
            if not reason:
                issue("warning","monotonous_typography",path+".typography",
                      "Same animation used for three consecutive shots")
    if mode=="camera_canvas":
        points=[s["camera_canvas"] for s in manifest["scenes"]]
        ww=max(int(c["x"]) for c in points)+int(w*1.5)
        hh=max(int(c["y"]) for c in points)+int(h*1.5)
        if ww*hh>32_000_000:
            issue("error","world_memory_budget","$.shots",
                  "Shared canvas exceeds renderer's 32 megapixel budget")
        # A center must give the full camera-facing tile room at angle 0;
        # rotated bounding boxes need an additional allowance.
        for i,c in enumerate(points):
            extent=.5*math.hypot(w,h)
            if c["x"]<extent or c["y"]<extent:
                issue("warning","world_edge_margin",f"$.shots[{i}].camera",
                      "Camera target near world edge may clip tilted material")
    errors=sum(x["severity"]=="error" for x in issues)
    return {
        "ok":errors==0,
        "status":"ok" if errors==0 else "review_required",
        "errors":errors,
        "warnings":sum(x["severity"]=="warning" for x in issues),
        "issues":issues,
        "limitations":[
            "Camera safe checks approximate geometry and do not replace full-frame inspection.",
            "Subject-aware cropping, perceptual scoring and audio alignment are not verified.",
        ]
    }
