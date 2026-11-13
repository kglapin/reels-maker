"""Carbon defaults for Studio; source tokens vs authored video policy are explicit."""
from __future__ import annotations
import copy
import math
from dataclasses import replace

SPACING_SOURCE = "https://v10.carbondesignsystem.com/guidelines/spacing/overview/"
SEQUENCE_SOURCE = "https://v10.carbondesignsystem.com/guidelines/motion/choreography/"
SPACING_PX = dict(zip((f"spacing-{i:02}" for i in range(1, 14)),
                      (2, 4, 8, 12, 16, 24, 32, 40, 48, 64, 80, 96, 160)))
VIDEO_SPACING = {"xs":"spacing-03", "sm":"spacing-05", "md":"spacing-07",
                 "lg":"spacing-09", "xl":"spacing-10", "xxl":"spacing-12"}


def _motion(setting):
    if setting is False or setting is None:
        return None
    if setting is True:
        return {"mode":"productive"}
    if not isinstance(setting, dict):
        raise ValueError("carbon_motion must be true, false, null or a profile object")
    if set(setting) - {"mode", "roles", "minimum_hold"}:
        raise ValueError("Unknown carbon_motion option")
    mode=setting.get("mode", "productive")
    if not isinstance(mode, str) or mode not in ("productive", "expressive"):
        raise ValueError("Unknown Carbon mode")
    return {"mode":mode, **copy.deepcopy(setting)}


def spacing_values(setting):
    """Map existing engine spacing roles to source tokens in design units."""
    if setting is False or setting is None:
        return {}
    if setting is True:
        selected=dict(VIDEO_SPACING)
    elif isinstance(setting, dict):
        if set(setting) - set(VIDEO_SPACING):
            raise ValueError("Unknown Carbon spacing role")
        selected={**VIDEO_SPACING, **setting}
    else:
        raise ValueError("carbon_spacing must be a boolean, null or role-token object")
    if any(not isinstance(token, str) or token not in SPACING_PX for token in selected.values()):
        raise ValueError("Use source token names spacing-01..spacing-13")
    return {role:SPACING_PX[token] for role,token in selected.items()}


def _number(value, name, low, high):
    if (isinstance(value, bool) or not isinstance(value, (int,float))
            or not math.isfinite(value) or not low <= value <= high):
        raise ValueError(f"{name} must be finite in {low}..{high}")
    return float(value)


def sequence_scene(scene, setting, fps):
    """Optional text-role sequencing; never overwrite authored/audio cues."""
    result=copy.deepcopy(scene)
    if setting is False or setting is None:
        return result
    config={} if setting is True else setting
    if not isinstance(config,dict) or set(config)-{"roles","gap","span"}:
        raise ValueError("carbon_sequence accepts roles, gap, span")
    if type(fps) is not int or not 1 <= fps <= 120:
        raise ValueError("FPS must be integer in 1..120")
    gap=_number(config.get("gap",.12),"sequence gap",.01,1)
    span=_number(config.get("span",.5),"sequence span",.01,2)
    inferred=[]
    if result.get("kicker"): inferred.append("kicker")
    kind=result.get("type") or result.get("kind") or result.get("composition")
    if kind in ("amount","hero-number"):
        inferred.append("amount")
    elif result.get("headline") or result.get("title"):
        inferred.append("headline")
    if result.get("subtitle") or result.get("body"): inferred.append("body")
    roles=config.get("roles",inferred)
    if (not isinstance(roles,list) or any(not isinstance(r,str) or not r for r in roles)
            or len(set(roles)) != len(roles)):
        raise ValueError("Sequence roles must be unique nonempty strings")
    # Existing cues may carry verified narration timing: leave the entire plan intact.
    if result.get("cues") or not roles:
        return result
    frames=math.floor(span*fps+1e-9)
    if len(roles)>1 and frames<len(roles)-1:
        raise ValueError("Too many sequence roles for requested frame span")
    step=(min(max(1,round(gap*fps)), frames//(len(roles)-1)) if len(roles)>1 else 0)
    cues={role:index*step/fps for index,role in enumerate(roles)}
    duration=_number(result.get("duration",2.8),"scene duration",.01,3600)
    if max(cues.values())>=duration:
        raise ValueError("Carbon sequence would extend past scene")
    result["cues"]=cues
    return result


def prepare_scenes(scenes, export, fps):
    """Resolve defaults on copies before QA, rendering and segment caching."""
    if not isinstance(export,dict):
        raise ValueError("export must be an object")
    project_motion=_motion(export.get("carbon_motion",True))
    sequence=export.get("carbon_sequence",False)
    result=[]
    for original in scenes:
        scene=copy.deepcopy(original)
        if "carbon_motion" in scene:
            scene["carbon_motion"]=_motion(scene["carbon_motion"])
        elif "camera_canvas" in scene:
            scene["carbon_motion"]=None
        else:
            scene["carbon_motion"]=copy.deepcopy(project_motion)
        local_sequence=scene.get("carbon_sequence",sequence)
        if "camera_canvas" not in scene:
            scene=sequence_scene(scene,local_sequence,fps)
        result.append(scene)
    return result


def configure_project(project):
    """Called by StudioProject construction, including ordinary studio-render."""
    from ..motionkit.carbon import _profile
    prepared=prepare_scenes(project.scenes,project.export,project.fps)
    for scene in prepared:
        if scene.get("carbon_motion") is not None:
            _profile(scene["carbon_motion"])
    values=spacing_values(project.export.get("carbon_spacing",False))
    tokens=project.tokens
    if values:
        tokens=replace(tokens,spacing=replace(tokens.spacing,**values))
    project.scenes=prepared
    project.tokens=tokens
