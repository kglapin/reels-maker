"""Creative Spec v1 -> executable Studio manifest, with explicit decision report."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from ..design.styles import canonical_style
from .director import plan_shots
from .spec import CreativeSpecError, validate_creative_spec

def _auto_camera_points(shots,width,height):
    # Intentional asymmetry, not repetitive 90-degree steps.
    base=[(1.25,.90,-9),(3.70,1.10,68),(4.15,2.60,158),
          (1.60,3.20,285),(3.08,4.55,325),(5.10,4.33,420)]
    poses=base[:len(shots)]
    max_x=(max(p[0] for p in poses)+1.5)*width
    max_y=(max(p[1] for p in poses)+1.5)*height
    scale=min(1.0,math.sqrt(29_000_000/(max_x*max_y)))
    return [(round(px*width*scale,3),round(py*height*scale,3),a)
            for px,py,a in poses]

def _relative_asset(asset,source_dir,root,brand):
    if brand and root is None:
        source=Path(source_dir).resolve()
        if "brands" not in source.parts:
            raise CreativeSpecError("$.brand",
                "Branded asset scopes require --root pointing to repository root")
        idx=source.parts.index("brands")
        root=Path(*source.parts[:idx]) if idx else Path("/")
    anchor=(Path(root)/"brands"/brand).resolve() if brand else Path(source_dir).resolve()
    path=Path(asset)
    candidate=(path if path.is_absolute() else anchor/path).resolve()
    try:
        candidate.relative_to(anchor)
    except ValueError as exc:
        raise CreativeSpecError("$.shots.asset","asset path escapes scoped project directory") from exc
    if not candidate.is_file():
        raise CreativeSpecError("$.shots.asset",f"image asset not found: {candidate}")
    if candidate.suffix.lower() not in (".jpg",".jpeg",".png",".webp"):
        raise CreativeSpecError("$.shots.asset","only PNG, JPEG or WebP stills supported")
    return str(candidate)

def compile_creative_spec(spec,*,source_dir=".",root=None,check_assets=True):
    """Pure, deterministic translation into the existing renderer's contract.

    The compiler never calls an LLM, invents an image, or silently downgrades
    an unimplemented effect. Asset scope is checked before rendering.
    """
    valid=validate_creative_spec(spec)
    shots=spec["shots"]
    mode=valid["mode"]
    directed=plan_shots(spec)
    brand=spec.get("brand")
    width,height,fps=valid["width"],valid["height"],valid["fps"]
    manifest={
        "schema_version":1,
        "name":spec["name"],
        "style":canonical_style(spec.get("style","editorial-premium")),
        "video":{"width":width,"height":height,"fps":fps},
        "export":{"codec":"libx264","crf":19,"preset":"veryfast"},
        "audio":copy.deepcopy(spec.get("audio") or {}),
        "scenes":[],
    }
    if brand:manifest["brand"]=brand
    if "palette" in spec:
        manifest["design_overrides"]={"palette":copy.deepcopy(spec["palette"])}
    warnings=[]
    camera_points=_auto_camera_points(shots,width,height) if mode=="camera_canvas" else []
    for index,(shot,decision) in enumerate(zip(shots,directed)):
        scene={
            "id":shot["id"],
            "duration":float(shot.get("duration",2.8)),
            "composition":("statement" if mode=="camera_canvas" else decision["layout"]),
            "headline":shot["headline"],
            "subtitle":shot.get("subtitle",""),
            "creative_intent":shot.get("intent",""),
        }
        if "kicker" in shot:scene["kicker"]=shot["kicker"]
        if "asset" in shot:
            if check_assets:
                scene["photo"]=_relative_asset(shot["asset"],source_dir,root,brand)
            else:
                scene["photo"]=str(shot["asset"])
        if "assets" in shot:
            carousel_cfg = shot.get("carousel") or {}
            labels = carousel_cfg.get("labels") or []
            items = []
            for asset_index, asset in enumerate(shot["assets"]):
                image = (_relative_asset(asset,source_dir,root,brand)
                         if check_assets else str(asset))
                item = {"image": image}
                if labels:
                    item["label"] = labels[asset_index]
                items.append(item)
            scene["carousel"] = {
                "items": items,
                "advance_seconds": float(
                    carousel_cfg.get("advance_seconds", 1.6)),
            }
        if mode=="camera_canvas":
            camera=shot.get("camera",{})
            x,y,angle=camera_points[index]
            scene["camera_canvas"]={
                "x":camera.get("x",x),
                "y":camera.get("y",y),
                "angle":camera.get("angle",angle),
                "zoom":camera.get("zoom",1),
                "layout":decision["layout"],
                "move_duration":camera.get("move_duration",.88),
                "reveal_delay":camera.get("reveal_delay",
                                          shot.get("typography",{}).get("delay",.18)),
                "reveal_duration":camera.get("reveal_duration",
                                             shot.get("typography",{}).get("duration",.56)),
                "typography_motion":decision["typography_motion"],
            }
            if index==0 and scene["camera_canvas"]["move_duration"]==0:
                scene["camera_canvas"]["move_duration"]=.88
        else:
            scene["typography_motion"]=decision["typography_motion"]
            if "value" in shot:scene["value"]=shot["value"]
            if "visual" in shot:scene["visual"]=shot["visual"]
            if "chart" in shot:scene.update(copy.deepcopy(shot["chart"]))
            if "rotation" in shot:scene["editorial_rotation"]=copy.deepcopy(shot["rotation"])
            if "icon_library" in shot:scene["icon_library"]=shot["icon_library"]
            if "icon_assets" in shot:scene["icon_assets"]=copy.deepcopy(shot["icon_assets"])
            if "transition" in shot and shot["transition"].get("type","cut")!="cut":
                scene["transition_out"]=copy.deepcopy(shot["transition"])
        manifest["scenes"].append(scene)
    decisions=[{**choice,"camera":manifest["scenes"][idx].get("camera_canvas")}
               for idx,choice in enumerate(directed)]
    report={
        "ok":True,
        "creative_spec_version":1,
        "mode":mode,
        "name":spec["name"],
        "shot_count":len(shots),
        "duration":valid["duration"],
        "decisions":decisions,
        "warnings":warnings,
        "limitations":[
            "Motion ranking is deterministic heuristic direction, not semantic inference.",
            "Visual QC of actual rendered frames is required before publication.",
        ],
    }
    return manifest,report
