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


_GRAPHIC_COLORS={"ink","muted","accent","kicker","surface","base"}
_GRAPHIC_GEOMETRY={
    "rect":{"x","y","w","h"},
    "round":{"x","y","w","h","radius"},
    "circle":{"cx","cy","r"},
    "ring":{"cx","cy","r"},
    "line":{"x1","y1","x2","y2"},
    "path":{"points","closed"},
}


def _graphic_color(value,path):
    if (not isinstance(value,str) or
            (value not in _GRAPHIC_COLORS and
             not re.fullmatch(r"#[0-9a-fA-F]{6}",value))):
        raise CreativeSpecError(path,"use a theme color token or literal #RRGGBB")


def _validate_graphic_elements(elements,path,*,mode,duration,width,height):
    if mode!="studio":
        raise CreativeSpecError(path,"graphic_elements are Studio-only")
    if not isinstance(elements,list) or not 1<=len(elements)<=12:
        raise CreativeSpecError(path,"expected 1..12 graphic elements")
    short=min(width,height)
    scene_duration=float(duration)
    seen=set()
    common={"id","type","draw","enter"}
    for index,raw in enumerate(elements):
        p=f"{path}[{index}]"
        item=_object(raw,p)
        kind=item.get("type")
        if kind not in _GRAPHIC_GEOMETRY:
            raise CreativeSpecError(p+".type","unsupported vector primitive")
        appearance={
            "rect":{"fill","border","border_width"},
            "round":{"fill","border","border_width"},
            "circle":{"fill","border","border_width"},
            "ring":{"color","width","stroke_width"},
            "line":{"color","width","stroke_width"},
            "path":{"color","width","stroke_width","fill"},
        }[kind]
        if kind=="round":
            appearance=appearance|{"radius"}
        permitted=common|_GRAPHIC_GEOMETRY[kind]|appearance
        _keys(item,permitted,p)
        element_id=_text(item.get("id"),p+".id",40)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*",element_id):
            raise CreativeSpecError(p+".id","invalid graphic element identifier")
        if element_id in seen:
            raise CreativeSpecError(p+".id","duplicate graphic element identifier")
        seen.add(element_id)

        for color_key in ("color","fill","border"):
            if color_key in item:
                _graphic_color(item[color_key],p+"."+color_key)
        if "width" in item and "stroke_width" in item:
            raise CreativeSpecError(p,"use width or stroke_width, not both")
        if "border" in item and "border_width" not in item:
            raise CreativeSpecError(p+".border_width","required when border is set")
        if "border_width" in item and "border" not in item:
            raise CreativeSpecError(p+".border_width","requires a border color")
        border_px=(short*_number(item["border_width"],p+".border_width",.001,.05)
                   if "border_width" in item else 0.0)
        stroke_key="stroke_width" if "stroke_width" in item else "width"
        stroke_norm=_number(item.get(stroke_key,.004),p+"."+stroke_key,.001,.05)
        stroke_px=short*stroke_norm

        box=None
        if kind in ("rect","round"):
            x=_number(item.get("x"),p+".x",0,1)*width
            y=_number(item.get("y"),p+".y",0,1)*height
            w=_number(item.get("w"),p+".w",.001,1)*width
            h=_number(item.get("h"),p+".h",.001,1)*height
            if x+w>width or y+h>height:
                raise CreativeSpecError(p,"rectangle must remain within the canvas")
            if kind=="round":
                radius=_number(item.get("radius",0),p+".radius",0,.25)*short
                if radius>min(w,h)/2:
                    raise CreativeSpecError(p+".radius","exceeds half the short side")
            if "fill" not in item and "border" not in item:
                raise CreativeSpecError(p,"rect/round needs fill or border")
            box=(x-border_px/2,y-border_px/2,
                 x+w+border_px/2,y+h+border_px/2)
        elif kind in ("circle","ring"):
            cx=_number(item.get("cx"),p+".cx",0,1)*width
            cy=_number(item.get("cy"),p+".cy",0,1)*height
            radius=_number(item.get("r"),p+".r",.001,.5)*short
            if kind=="circle":
                if "fill" not in item and "border" not in item:
                    raise CreativeSpecError(p,"circle needs fill or border")
                extent=radius+border_px/2
            else:
                if "color" not in item or not ("width" in item or "stroke_width" in item):
                    raise CreativeSpecError(p,"ring needs color and width/stroke_width")
                extent=radius+stroke_px/2
            box=(cx-extent,cy-extent,cx+extent,cy+extent)
        elif kind=="line":
            if "color" not in item or not ("width" in item or "stroke_width" in item):
                raise CreativeSpecError(p,"line needs color and width/stroke_width")
            x1=_number(item.get("x1"),p+".x1",0,1)*width
            y1=_number(item.get("y1"),p+".y1",0,1)*height
            x2=_number(item.get("x2"),p+".x2",0,1)*width
            y2=_number(item.get("y2"),p+".y2",0,1)*height
            if x1==x2 and y1==y2:
                raise CreativeSpecError(p,"line endpoints must be distinct")
            half=stroke_px/2
            box=(min(x1,x2)-half,min(y1,y2)-half,
                 max(x1,x2)+half,max(y1,y2)+half)
        else:
            if "color" not in item or not ("width" in item or "stroke_width" in item):
                raise CreativeSpecError(p,"path needs color and width/stroke_width")
            points=item.get("points")
            if not isinstance(points,list) or not 2<=len(points)<=32:
                raise CreativeSpecError(p+".points","expected 2..32 points")
            px=[]
            for point_index,point in enumerate(points):
                pp=f"{p}.points[{point_index}]"
                if not isinstance(point,list) or len(point)!=2:
                    raise CreativeSpecError(pp,"expected [x, y]")
                px.append((_number(point[0],pp+"[0]",0,1)*width,
                           _number(point[1],pp+"[1]",0,1)*height))
            if len(set(px))<2:
                raise CreativeSpecError(p+".points","needs two distinct points")
            if "closed" in item and not isinstance(item["closed"],bool):
                raise CreativeSpecError(p+".closed","expected a boolean")
            if item.get("closed") and "fill" not in item:
                raise CreativeSpecError(p+".fill","closed paths require a fill color")
            half=stroke_px/2
            box=(min(x for x,_ in px)-half,min(y for _,y in px)-half,
                 max(x for x,_ in px)+half,max(y for _,y in px)+half)
        if box and (box[0]<0 or box[1]<0 or box[2]>width or box[3]>height):
            raise CreativeSpecError(p,"graphic element and stroke must remain within canvas")

        if "draw" in item:
            if kind not in ("ring","line","path"):
                raise CreativeSpecError(p+".draw","supported only on ring/line/path")
            draw=_object(item["draw"],p+".draw")
            _keys(draw,{"delay","duration"},p+".draw")
            if "duration" not in draw:
                raise CreativeSpecError(p+".draw.duration","is required")
            delay=_number(draw.get("delay",0),p+".draw.delay",0,scene_duration)
            draw_duration=_number(draw["duration"],p+".draw.duration",
                                  .05,min(8,scene_duration))
            if delay+draw_duration>scene_duration+.0001:
                raise CreativeSpecError(p+".draw","must finish within scene duration")
        if "enter" in item:
            enter=_object(item["enter"],p+".enter")
            _keys(enter,{"preset","delay","duration"},p+".enter")
            preset=enter.get("preset","fade-up")
            from ..motionkit.presets import canonical_preset
            try:
                canonical=canonical_preset(preset) if isinstance(preset,str) else None
            except ValueError:
                canonical=None
            if canonical not in PRESETS:
                raise CreativeSpecError(p+".enter.preset","unsupported entrance preset")
            delay=_number(enter.get("delay",0),p+".enter.delay",0,scene_duration)
            enter_duration=_number(enter.get("duration",.45),p+".enter.duration",
                                   .05,min(3,scene_duration))
            if delay+enter_duration>scene_duration+.0001:
                raise CreativeSpecError(p+".enter","must finish within scene duration")

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
                    "chart","kicker","allow_repeat_reason","assets","carousel",
                    "split_lines","cues","perspective","graphic_elements"},p)
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
        if selected_composition in ("photo-carousel", "photo-marquee"):
            if mode != "studio":
                raise CreativeSpecError(p+".layout",
                                        f"{selected_composition} is Studio-only")
            if ("composition" in shot and
                    shot.get("layout", "auto") not in ("auto", selected_composition)):
                raise CreativeSpecError(p+".layout",
                                        f"{selected_composition} cannot be combined with another layout")
            if ("layout" in shot and shot.get("composition") not in
                    (None, selected_composition)):
                raise CreativeSpecError(p+".composition",
                                        f"{selected_composition} cannot be combined with another composition")
            if "asset" in shot:
                raise CreativeSpecError(p+".asset",
                                        f"{selected_composition} uses assets, not a single asset")
            assets = shot.get("assets")
            if not isinstance(assets, list) or not 3 <= len(assets) <= 12:
                raise CreativeSpecError(p+".assets",
                                        f"{selected_composition} requires 3..12 image paths")
            for asset_index, asset in enumerate(assets):
                _text(asset, f"{p}.assets[{asset_index}]", 500)
                if "://" in asset:
                    raise CreativeSpecError(
                        f"{p}.assets[{asset_index}]",
                        "use local image paths, not URLs")
            carousel = _object(shot.get("carousel", {}), p+".carousel")
            _keys(carousel, {"advance_seconds", "labels", "direction"}, p+".carousel")
            if "direction" in carousel and carousel["direction"] not in ("horizontal", "vertical"):
                raise CreativeSpecError(
                    p+".carousel.direction",
                    "choose horizontal or vertical")
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
        if "split_lines" in shot:
            split=shot["split_lines"]
            if not (isinstance(split,bool) or split == "words" or
                    isinstance(split,list) and all(
                        role in ("headline","body","kicker") for role in split)):
                raise CreativeSpecError(p+".split_lines",
                    "choose true, false, 'words', or a list of headline/body/kicker roles")
            if isinstance(split,list):
                available={"headline"}
                if shot.get("subtitle"): available.add("body")
                if shot.get("kicker"): available.add("kicker")
                if set(split)-available:
                    raise CreativeSpecError(p+".split_lines",
                        "cannot split an absent headline/body/kicker role")
        if "cues" in shot:
            if mode != "studio":
                raise CreativeSpecError(p+".cues","authored scene cues require Studio mode")
            cues=_object(shot["cues"],p+".cues")
            if len(cues)>12:
                raise CreativeSpecError(p+".cues","at most 12 role cues are supported")
            composition=shot.get("composition",layout)
            available={"headline"}
            if shot.get("subtitle"): available.add("body")
            if shot.get("kicker"): available.add("kicker")
            if composition=="quote": available.add("quote-mark")
            if composition in ("amount","stats","bars","line-chart","checklist"):
                available.add("visual")
            for role,value in cues.items():
                if role not in available:
                    raise CreativeSpecError(p+f".cues.{role}",
                        "cue must target a rendered element in this scene")
                _number(value,p+f".cues.{role}",0,float(shot.get("duration",2.8)))
        if "perspective" in shot:
            if mode != "studio":
                raise CreativeSpecError(p+".perspective","perspective is Studio-only")
            perspective=_object(shot["perspective"],p+".perspective")
            try:
                from ..renderers.perspective import perspective_spec
                normalized=perspective_spec({"perspective":perspective})
            except (TypeError,ValueError) as exc:
                raise CreativeSpecError(p+".perspective",str(exc)) from exc
            duration=float(shot.get("duration",2.8))
            if normalized["delay"]+normalized["duration"]>duration+.0001:
                raise CreativeSpecError(p+".perspective",
                    "camera move must finish within the scene duration")
            if normalized["path"] and normalized["path"][-1]["t"]>duration:
                raise CreativeSpecError(p+".perspective.path",
                    "camera path must finish within the scene duration")
        if "graphic_elements" in shot:
            _validate_graphic_elements(
                shot["graphic_elements"], p+".graphic_elements",
                mode=mode, duration=shot.get("duration", 2.8),
                width=width, height=height)
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
