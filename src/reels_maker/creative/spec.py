"""Strict, dependency-free validation of LLM-authored Creative Spec v1."""
from __future__ import annotations
import math
import re
from collections.abc import Mapping
from ..design.styles import canonical_style
from ..motionkit.presets import PRESETS
from ..renderers.transition_engine import EFFECTS
from .registry import (CAMERA_LAYOUTS, CAMERA_TEXT_MOTIONS,
                       STUDIO_COMPOSITIONS, CAMERA_SHOT_LIMIT)

class CreativeSpecError(ValueError):
    """A structured Creative Spec failure; path identifies the invalid field."""
    def __init__(self,path,message):
        self.path,self.message=path,message
        super().__init__(f"{path}: {message}")

def _object(v,path):
    if not isinstance(v,Mapping):
        raise CreativeSpecError(path,"expected an object")
    return v

def _text(v,path,max_length=180,required=True):
    if not isinstance(v,str) or (required and not v.strip()) or len(v)>max_length:
        raise CreativeSpecError(path,f"expected a string of 1..{max_length} characters")
    return v

def _number(v,path,minimum,maximum):
    if isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or not minimum<=v<=maximum:
        raise CreativeSpecError(path,f"expected a finite number in [{minimum}, {maximum}]")
    return float(v)

def _keys(value,permitted,path):
    extra=set(value)-set(permitted)
    if extra:
        raise CreativeSpecError(path,"unknown keys: "+", ".join(sorted(map(str,extra))))

def validate_creative_spec(spec):
    """Validate intent and capability references before invoking the renderer.

    Asset accessibility and rendered-frame geometry require later preflight.
    """
    spec=_object(spec,"$")
    _keys(spec,{"creative_schema_version","name","mode","style","video",
                "shots","brand","audio","palette","seed","creative_direction"},"$")
    if spec.get("creative_schema_version")!=1:
        raise CreativeSpecError("$.creative_schema_version","must equal 1")
    _text(spec.get("name"),"$.name",80)
    mode=spec.get("mode","studio")
    if mode not in ("studio","camera_canvas"):
        raise CreativeSpecError("$.mode","choose studio or camera_canvas")
    try:
        canonical_style(spec.get("style","editorial-premium"))
    except ValueError as exc:
        raise CreativeSpecError("$.style",str(exc)) from exc
    video=_object(spec.get("video",{}),"$.video")
    _keys(video,{"width","height","fps"},"$.video")
    width=video.get("width",540)
    height=video.get("height",960)
    fps=video.get("fps",24)
    if any(isinstance(v,bool) or type(v) is not int for v in (width,height,fps)):
        raise CreativeSpecError("$.video","width, height and fps must be integers")
    _number(width,"$.video.width",180,4096)
    _number(height,"$.video.height",180,4096)
    _number(fps,"$.video.fps",1,120)
    if width/height<.4 or width/height>2.5:
        raise CreativeSpecError("$.video","unsupported aspect ratio")
    if "seed" in spec and (type(spec["seed"]) is not int or not 0<=spec["seed"]<2**31):
        raise CreativeSpecError("$.seed","expected nonnegative integer below 2^31")
    if "brand" in spec:
        _text(spec["brand"],"$.brand",80)
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",spec["brand"]):
            raise CreativeSpecError("$.brand","expected lowercase brand slug")
    if "audio" in spec:
        _object(spec["audio"],"$.audio")
    if "palette" in spec:
        palette=_object(spec["palette"],"$.palette")
        _keys(palette,{"background","surface","ink","muted","accent"},"$.palette")
        for k,v in palette.items():
            if not isinstance(v,str) or not re.fullmatch(r"#[0-9a-fA-F]{6}",v):
                raise CreativeSpecError(f"$.palette.{k}","expected #RRGGBB color")
    if "creative_direction" in spec:
        _text(spec["creative_direction"],"$.creative_direction",1000,required=False)
    shots=spec.get("shots")
    if not isinstance(shots,list) or not 1<=len(shots)<=24:
        raise CreativeSpecError("$.shots","expected 1..24 scene objects")
    if mode=="camera_canvas" and len(shots)>CAMERA_SHOT_LIMIT:
        raise CreativeSpecError("$.shots",f"camera_canvas supports at most {CAMERA_SHOT_LIMIT} shots")
    seen=set()
    for i,shot in enumerate(shots):
        p=f"$.shots[{i}]"
        shot=_object(shot,p)
        _keys(shot,{"id","intent","headline","subtitle","duration","asset",
                    "composition","layout","camera","typography","transition",
                    "value","visual","icon_library","icon_assets","rotation",
                    "kicker","allow_repeat_reason"},p)
        sid=_text(shot.get("id"),p+".id",80)
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*",sid):
            raise CreativeSpecError(p+".id","invalid scene identifier")
        if sid in seen:
            raise CreativeSpecError(p+".id","duplicate shot identifier")
        seen.add(sid)
        _text(shot.get("headline"),p+".headline",160)
        for key in ("subtitle","intent","kicker","allow_repeat_reason"):
            if key in shot:
                _text(shot[key],p+"."+key,300,required=False)
        _number(shot.get("duration",2.8),p+".duration",.5,30)
        if "asset" in shot:
            _text(shot["asset"],p+".asset",500)
            if "://" in shot["asset"]:
                raise CreativeSpecError(p+".asset","use a local asset path, not a URL")
        elif mode=="camera_canvas":
            raise CreativeSpecError(p+".asset","camera_canvas requires a real local photograph")
        layout=shot.get("layout","auto")
        allowed={"auto"}|set(CAMERA_LAYOUTS if mode=="camera_canvas" else STUDIO_COMPOSITIONS)
        if layout not in allowed:
            raise CreativeSpecError(p+".layout",f"unsupported {mode} layout {layout!r}")
        if "composition" in shot:
            if mode=="camera_canvas":
                raise CreativeSpecError(p+".composition","use layout for camera_canvas")
            if shot["composition"] not in STUDIO_COMPOSITIONS:
                raise CreativeSpecError(p+".composition","unsupported composition")
        camera=_object(shot.get("camera",{}),p+".camera")
        _keys(camera,{"x","y","angle","zoom","move_duration","reveal_delay",
                      "reveal_duration"},p+".camera")
        for key,(lo,hi) in {
            "x":(0,16000),"y":(0,16000),"angle":(-720,720),
            "zoom":(.65,2),"move_duration":(.05,4),
            "reveal_delay":(0,3),"reveal_duration":(.05,3),
        }.items():
            if key in camera:
                _number(camera[key],p+".camera."+key,lo,hi)
        if camera and mode!="camera_canvas":
            raise CreativeSpecError(p+".camera","camera properties require mode camera_canvas")
        motion=_object(shot.get("typography",{}),p+".typography")
        _keys(motion,{"family","duration","delay"},p+".typography")
        family=motion.get("family","auto")
        supported=CAMERA_TEXT_MOTIONS if mode=="camera_canvas" else PRESETS
        if family!="auto" and family not in supported:
            raise CreativeSpecError(p+".typography.family",
                                    f"{family!r} is not implemented in {mode}")
        if "duration" in motion:_number(motion["duration"],p+".typography.duration",.1,3)
        if "delay" in motion:_number(motion["delay"],p+".typography.delay",0,3)
        trans=_object(shot.get("transition",{}),p+".transition")
        _keys(trans,{"type","duration","direction"},p+".transition")
        if trans and mode=="camera_canvas":
            raise CreativeSpecError(p+".transition","camera travel replaces Studio transitions")
        if trans.get("type","cut") not in set(EFFECTS)|{"cut"}:
            raise CreativeSpecError(p+".transition.type","unknown transition type")
        if "duration" in trans:_number(trans["duration"],p+".transition.duration",.1,2)
        if trans.get("direction","left") not in ("left","right","up","down"):
            raise CreativeSpecError(p+".transition.direction","unsupported direction")
        if "rotation" in shot:
            if mode!="studio":
                raise CreativeSpecError(p+".rotation","use camera.angle in camera_canvas")
            rot=_object(shot["rotation"],p+".rotation")
            for role,r in rot.items():
                if role not in ("headline","body","kicker","visual"):
                    raise CreativeSpecError(p+".rotation","unknown node role "+str(role))
                r=_object(r,p+".rotation."+role)
                _keys(r,{"family","angle","duration","settle_angle","start","reason"},p+".rotation."+role)
                _number(r.get("angle",0),p+".rotation."+role+".angle",-35,35)
    return {"ok":True,"mode":mode,"shot_count":len(shots),
            "duration":round(sum(float(s.get("duration",2.8)) for s in shots),3),
            "width":width,"height":height,"fps":fps}
