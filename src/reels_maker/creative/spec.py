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
                    "chart","kicker","allow_repeat_reason","assets","carousel"},p)
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
        selected_composition = shot.get("composition", layout)
        if selected_composition == "photo-carousel":
            if mode != "studio":
                raise CreativeSpecError(p+".layout",
                                        "photo-carousel is Studio-only")
            if ("composition" in shot and
                    shot.get("layout", "auto") not in ("auto", "photo-carousel")):
                raise CreativeSpecError(p+".layout",
                                        "photo-carousel cannot be combined with another layout")
            if ("layout" in shot and shot.get("composition") not in
                    (None, "photo-carousel")):
                raise CreativeSpecError(p+".composition",
                                        "photo-carousel cannot be combined with another composition")
            if "asset" in shot:
                raise CreativeSpecError(p+".asset",
                                        "photo-carousel uses assets, not a single asset")
            assets = shot.get("assets")
            if not isinstance(assets, list) or not 3 <= len(assets) <= 12:
                raise CreativeSpecError(p+".assets",
                                        "photo-carousel requires 3..12 image paths")
            for asset_index, asset in enumerate(assets):
                _text(asset, f"{p}.assets[{asset_index}]", 500)
                if "://" in asset:
                    raise CreativeSpecError(
                        f"{p}.assets[{asset_index}]",
                        "use local image paths, not URLs")
            carousel = _object(shot.get("carousel", {}), p+".carousel")
            _keys(carousel, {"advance_seconds", "labels"}, p+".carousel")
            if "advance_seconds" in carousel:
                _number(carousel["advance_seconds"],
                        p+".carousel.advance_seconds", .8, 4)
            if "labels" in carousel:
                labels = carousel["labels"]
                if not isinstance(labels, list) or len(labels) != len(assets):
                    raise CreativeSpecError(
                        p+".carousel.labels",
                        "provide one label per photo asset")
                for label_index, label in enumerate(labels):
                    _text(label, f"{p}.carousel.labels[{label_index}]", 80)
        elif "assets" in shot or "carousel" in shot:
            raise CreativeSpecError(p+".assets",
                                    "assets and carousel require photo-carousel")
        if "composition" in shot:
            if mode=="camera_canvas":
                raise CreativeSpecError(p+".composition","use layout for camera_canvas")
            if shot["composition"] not in STUDIO_COMPOSITIONS:
                raise CreativeSpecError(p+".composition","unsupported composition")
        selected_chart = shot.get("composition", layout) == "line-chart"
        chart = shot.get("chart")
        if selected_chart and mode != "studio":
            raise CreativeSpecError(p+".chart","line-chart is Studio-only")
        if selected_chart and not isinstance(chart, dict):
            raise CreativeSpecError(p+".chart","line-chart requires explicit chart data")
        if chart is not None:
            if not selected_chart or mode != "studio":
                raise CreativeSpecError(p+".chart","chart data is supported only with Studio line-chart")
            _keys(chart,{"points","x_axis_type","x_axis_label","y_axis_label","y_domain"},p+".chart")
            points=chart.get("points")
            if not isinstance(points,list) or not 2<=len(points)<=12:
                raise CreativeSpecError(p+".chart.points","expected 2..12 explicit points")
            labels=[]
            values=[]
            for point_index,point in enumerate(points):
                pp=f"{p}.chart.points[{point_index}]"
                point=_object(point,pp)
                _keys(point,{"label","value"},pp)
                labels.append(_text(point.get("label"),pp+".label",80))
                values.append(_number(point.get("value"),pp+".value",-1e15,1e15))
            if len(set(labels))!=len(labels):
                raise CreativeSpecError(p+".chart.points","labels must be unique")
            axis_type=chart.get("x_axis_type","category")
            if axis_type not in ("category","date"):
                raise CreativeSpecError(p+".chart.x_axis_type","choose category or date")
            _text(chart.get("x_axis_label"),p+".chart.x_axis_label",80)
            _text(chart.get("y_axis_label"),p+".chart.y_axis_label",80)
            domain=chart.get("y_domain")
            if not isinstance(domain,list) or len(domain)!=2:
                raise CreativeSpecError(p+".chart.y_domain","requires two explicit bounds")
            lower=_number(domain[0],p+".chart.y_domain[0]",-1e15,1e15)
            upper=_number(domain[1],p+".chart.y_domain[1]",-1e15,1e15)
            if upper<=lower:
                raise CreativeSpecError(p+".chart.y_domain","maximum must exceed minimum")
            if any(value<lower or value>upper for value in values):
                raise CreativeSpecError(p+".chart.y_domain","must contain every point value")
            if axis_type=="date":
                from datetime import date
                try:
                    parsed=[date.fromisoformat(label) for label in labels]
                except ValueError as exc:
                    raise CreativeSpecError(p+".chart.points","date labels must use ISO YYYY-MM-DD") from exc
                if any(current<=previous for previous,current in zip(parsed,parsed[1:])):
                    raise CreativeSpecError(p+".chart.points","date labels must be strictly increasing")
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
