"""Opt-in Carbon choreography using native retained nodes and tracks.

Video duration/selection formulas are authored adaptations, not IBM algorithms.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
from dataclasses import replace


def number(value, name, low, high):
    if (isinstance(value,bool) or not isinstance(value,(int,float))
            or not math.isfinite(value) or not low <= value <= high):
        raise ValueError(f"{name} must be finite in {low}..{high}")
    return float(value)


def adaptive_duration(distance, scale_from, scale_to, short_side, fps, available, mode="productive"):
    distance=number(distance,"distance",0,1e7)
    side=number(short_side,"short side",1,1e5)
    first=number(scale_from,"scale_from",.001,1000)
    last=number(scale_to,"scale_to",.001,1000)
    room=number(available,"available",0,3600)
    if type(fps) is not int or not 1<=fps<=120 or mode not in ("productive","expressive"):
        raise ValueError("Invalid FPS or motion mode")
    seconds=.18+.34*math.sqrt(distance/side)+.18*abs(math.log(last/first))
    seconds=min(.9,max(.18,seconds*(1.25 if mode=="expressive" else 1)))
    frames=math.ceil(seconds*fps-1e-9)
    if frames>math.floor(room*fps+1e-9):
        raise ValueError("Adaptive motion cannot fit without consuming reading hold")
    return frames/fps


def accent_indices(scenes, limit=1):
    if type(limit) is not int or not 0<=limit<=3:
        raise ValueError("Accent limit must be integer in 0..3")
    explicit=[i for i,s in enumerate(scenes) if isinstance(s.get("carbon_motion"),dict)
              and s["carbon_motion"].get("mode")=="expressive"]
    priority={"proof":5,"reveal":5,"statistics":4,"hook":3,"opening":2}
    candidates=[]
    for i,scene in enumerate(scenes):
        if scene.get("carbon_lock",False) or i in explicit or "camera_canvas" in scene:
            continue
        if scene.get("carbon_motion") is None:
            continue
        intent=str(scene.get("creative_intent",scene.get("intent",""))).strip().lower()
        if intent in priority: candidates.append((-priority[intent],i))
    return [i for _,i in sorted(candidates)[:max(0,limit-len(explicit))]]


def prepare_project(project):
    """Resolve opt-in accent decisions and cross-scene cache dependencies."""
    scenes=copy.deepcopy(project.scenes)
    director=project.export.get("carbon_director",False)
    if type(director) is not bool:
        raise ValueError("carbon_director must be boolean")
    if director:
        for i in accent_indices(scenes,project.export.get("carbon_accent_limit",1)):
            scenes[i]["carbon_motion"]={**scenes[i]["carbon_motion"],"mode":"expressive"}
    for scene in scenes:
        if "carbon_lock" in scene and type(scene["carbon_lock"]) is not bool:
            raise ValueError("carbon_lock must be boolean")
        scene.pop("_carbon_shared_next",None)
        bindings=scene.get("carbon_shared",{})
        if (not isinstance(bindings,dict)
                or any(not isinstance(k,str) or not k or not isinstance(v,str) or not v for k,v in bindings.items())
                or len(set(bindings.values()))!=len(bindings)):
            raise ValueError("Shared bindings require unique nonempty IDs and root roles")
    snapshots=copy.deepcopy(scenes)
    for i in range(len(scenes)-1):
        left=scenes[i].get("carbon_shared",{})
        right=scenes[i+1].get("carbon_shared",{})
        if not isinstance(left,dict) or not isinstance(right,dict):
            raise ValueError("carbon_shared must map stable IDs to root roles")
        if set(left)&set(right):
            raw=json.dumps(snapshots[i+1],sort_keys=True,ensure_ascii=False,allow_nan=False)
            scenes[i]["_carbon_shared_next"]=hashlib.sha256(raw.encode()).hexdigest()
    project.scenes=scenes


def _clone_scene(item):
    memo={}
    def clone(node):
        if id(node) in memo: return memo[id(node)]
        result=copy.copy(node);memo[id(node)]=result
        result.props=dict(node.props);result.meta=dict(node.meta)
        result.tracks=dict(node.tracks)
        result.reveal=dict(node.reveal) if node.reveal is not None else None
        result.children=[clone(child) for child in node.children]
        return result
    result=copy.copy(item)
    result.nodes=[clone(node) for node in item.nodes]
    result.elements={role:clone(node) for role,node in item.elements.items()}
    result.meta=dict(item.meta)
    result._subtree_settles={};result._settled_samples={}
    return result


def _node(item,role,root=False):
    nodes=item.nodes if root else [n for r in item.nodes for n in r.flatten()]
    matches={id(n):n for n in nodes if n.role==role}
    if len(matches)!=1: raise ValueError(f"Expected one {'root ' if root else ''}node for role {role!r}")
    return next(iter(matches.values()))


def _keys(track,keys):
    return type(track)(keys,clamp_before=track.clamp_before,clamp_after=track.clamp_after)


def _append(node,prop,start,end,first,last,mode):
    from .keyframes import Keyframe,Track
    from .carbon import curve_params
    previous=node.tracks.get(prop)
    kept=[k for k in previous.keys if k.time<start] if previous else []
    node.tracks[prop]=Track([*kept,Keyframe(start,first,"linear"),
                            Keyframe(end,last,"cubic-bezier",curve_params(mode,"standard"))])


def _roles(item,config,project):
    from .carbon import APPEARANCE,curve_params
    if not isinstance(config,dict) or set(config)-{"roles","attention_limit"}:
        raise ValueError("carbon_choreography accepts roles and attention_limit")
    roles=config.get("roles",{})
    if not isinstance(roles,dict): raise ValueError("roles must be an object")
    for role,options in roles.items():
        if not isinstance(options,dict) or set(options)-{"segments","adaptive","path","mode","relation"}:
            raise ValueError("Invalid role choreography options")
        node=_node(item,role)
        mode=options.get("mode",(item.scene.get("carbon_motion") or {}).get("mode","productive"))
        relation=options.get("relation","replace")
        if relation not in ("replace","reveal","detail","result"):
            raise ValueError("Unknown spatial relation")
        phase="entrance" if relation in ("reveal","result") else "standard"
        curve_params(mode,phase)
        if "path" in options and ("adaptive" in options or "segments" in options):
            raise ValueError("A path cannot also request segment edits/adaptive retiming")
        segments=options.get("segments",{})
        if not isinstance(segments,dict): raise ValueError("segments must be an object")
        for prop,entries in segments.items():
            if prop not in APPEARANCE or prop not in node.tracks or not isinstance(entries,list):
                raise ValueError("Explicit segments require existing appearance tracks")
            track=node.tracks[prop];keys=list(track.keys);used=set()
            for entry in entries:
                if not isinstance(entry,dict) or set(entry)!={"index","phase"}:
                    raise ValueError("Segment requires exactly index and phase")
                index=entry["index"]
                if type(index) is not int or not 1<=index<len(keys) or index in used:
                    raise ValueError("Invalid/duplicate destination key index")
                if keys[index-1].value==keys[index].value:
                    raise ValueError("A hold segment must not be rewritten")
                used.add(index)
                keys[index]=replace(keys[index],easing="cubic-bezier",params=curve_params(mode,entry["phase"]))
            node.tracks[prop]=_keys(track,keys)
        if "adaptive" in options:
            adaptive=options["adaptive"]
            if not isinstance(adaptive,dict) or set(adaptive)-{"properties","minimum_hold"}:
                raise ValueError("adaptive accepts properties and minimum_hold")
            if segments: raise ValueError("Adaptive retiming cannot also edit segments")
            props=adaptive.get("properties",[p for p in ("dx","dy","scale") if p in node.tracks])
            if not isinstance(props,list) or not props or len(set(props))!=len(props):
                raise ValueError("Adaptive properties must be a nonempty unique list")
            selected=[]
            for prop in props:
                if prop not in {"dx","dy","scale","opacity","reveal"} or prop not in node.tracks or len(node.tracks[prop].keys)!=2:
                    raise ValueError("Adaptive retiming requires two-key appearance tracks")
                selected.append(node.tracks[prop])
            intervals={(t.keys[0].time,t.keys[-1].time) for t in selected}
            if len(intervals)!=1: raise ValueError("Coupled adaptive tracks must share an interval")
            start,_=next(iter(intervals))
            hold=number(adaptive.get("minimum_hold",.8),"minimum_hold",0,30)
            delta=lambda p:abs(node.tracks[p].keys[-1].value-node.tracks[p].keys[0].value) if p in props else 0
            scale=node.tracks.get("scale") if "scale" in props else None
            duration=adaptive_duration(math.hypot(delta("dx"),delta("dy")),
                scale.keys[0].value if scale else 1,scale.keys[-1].value if scale else 1,
                min(project.width,project.height),project.fps,item.duration-start-hold,mode)
            for prop,track in zip(props,selected):
                node.tracks[prop]=_keys(track,[track.keys[0],replace(track.keys[-1],time=start+duration,
                    easing="cubic-bezier",params=curve_params(mode,phase))])
        if "path" in options:
            path=options["path"]
            if not isinstance(path,dict) or set(path)-{"to","at","duration","axis"}:
                raise ValueError("path accepts to, at, duration, axis")
            if all(node is not root for root in item.nodes):
                raise ValueError("Spatial paths currently require root nodes")
            target=path.get("to")
            if not isinstance(target,list) or len(target)!=2: raise ValueError("path.to requires [dx,dy] canvas fractions")
            x=number(target[0],"path x",-1,1)*project.width
            y=number(target[1],"path y",-1,1)*project.height
            start=number(path.get("at",.8),"path at",0,item.duration)
            duration=number(path.get("duration",.7),"path duration",.05,4)
            duration=math.ceil(duration*project.fps-1e-9)/project.fps
            if start+duration>item.duration: raise ValueError("Path exceeds scene")
            axis=path.get("axis","x")
            if axis not in ("x","y"): raise ValueError("axis must be x or y")
            if any(node.tracks[p].end>start for p in ("dx","dy") if p in node.tracks):
                raise ValueError("Path would overwrite active authored translation")
            sampled=node.sample(start)
            first_prop,second_prop=("dx","dy") if axis=="x" else ("dy","dx")
            goals={"dx":x,"dy":y}
            frames=round(duration*project.fps)
            if frames<3: raise ValueError("Rounded paths require at least three frames")
            lag=max(1,round(frames*.2))/project.fps
            _append(node,first_prop,start,start+duration-lag,getattr(sampled,first_prop),goals[first_prop],mode)
            _append(node,second_prop,start+lag,start+duration,getattr(sampled,second_prop),goals[second_prop],mode)
        item.meta.setdefault("carbon_choreography",{})[role]={"mode":mode,"relation":relation}


def bridge_transform(base,goal,anchor=None):
    """Uniform root transform preserving aspect; geometry only, not pixel identity."""
    if not all(isinstance(box,(list,tuple)) and len(box)==4 for box in (base,goal)):
        raise ValueError("Expected two four-coordinate bounds")
    for value in (*base,*goal): number(value,"bound",-1e7,1e7)
    aw,ah=base[2]-base[0],base[3]-base[1]
    bw,bh=goal[2]-goal[0],goal[3]-goal[1]
    if min(aw,ah,bw,bh)<=0 or not math.isclose(bw/aw,bh/ah,rel_tol=1e-5):
        raise ValueError("Shared bridge requires matching aspect ratio")
    scale=bw/aw;cx=(base[0]+base[2])/2;cy=(base[1]+base[3])/2
    ax,ay=anchor or (cx,cy)
    dx=(goal[0]+goal[2])/2-(ax+scale*(cx-ax))
    dy=(goal[1]+goal[3])/2-(ay+scale*(cy-ay))
    return scale,dx,dy


def _bridge(left,right,role_a,role_b,project,duration):
    from .carbon import APPEARANCE
    a=_node(left,role_a,True);b=_node(right,role_b,True)
    if a.kind!=b.kind or a.kind not in ("image","rect","circle") or a.children or b.children:
        raise ValueError("Shared bridges support matching leaf image/rect/circle root nodes only")
    if any(k in n.props for n in (a,b) for k in ("stroke","outline","width")):
        raise ValueError("Shared bridges do not rescale stroked shapes")
    geometry={"x","y","w","h","cx","cy","r"}
    if {k:v for k,v in a.props.items() if k not in geometry}!={k:v for k,v in b.props.items() if k not in geometry}:
        raise ValueError("Shared object content/style differs")
    for node in (a,b):
        if node.clip is not None or node.rotation!=0 or node.sx is not None or node.sy is not None:
            raise ValueError("Shared bridges reject clipping, rotation and nonuniform scale")
        if set(node.tracks)-APPEARANCE: raise ValueError("Shared object has unsupported animated content")
    end=(round(left.duration*project.fps)-1)/project.fps
    start=end-math.ceil(duration*project.fps-1e-9)/project.fps
    if start<.8: raise ValueError("Shared bridge would consume the initial reading hold")
    if any(a.tracks[p].end>start for p in ("dx","dy","scale","rotation") if p in a.tracks):
        raise ValueError("Shared bridge conflicts with authored transform")
    current=a.sample(start)
    if current.opacity<.99 or current.rotation!=0 or (current.reveal and current.reveal.get("progress",1)<.999):
        raise ValueError("Shared source is not fully visible/settled")
    target=copy.copy(b);target.reveal=None
    base=a.base_bounds();goal=target.world_bounds()
    if base is None or goal is None: raise ValueError("Shared bounds are missing")
    scale,dx,dy=bridge_transform(base,goal,a.anchor)
    margin,top,bottom=project.tokens.safe_pixels(project.width,project.height)
    for box in (current.world_bounds(),goal):
        if box[0]<margin or box[1]<top or box[2]>project.width-margin or box[3]>project.height-bottom:
            raise ValueError("Shared object leaves rectangular content safe area")
    mode=(left.scene.get("carbon_motion") or {}).get("mode","productive")
    for prop,first,last in (("dx",current.dx,dx),("dy",current.dy,dy),("scale",current.scale,scale),("opacity",1.,1.)):
        _append(a,prop,start,end,first,last,mode)
    if a.reveal is not None: _append(a,"reveal",start,end,1.,1.,mode)
    for prop in list(b.tracks):
        if prop in APPEARANCE: b.tracks.pop(prop)
    b.opacity=1.;b.reveal=None
    record={"from_role":role_a,"to_role":role_b,"start":start,"end":end,
            "continuity":"geometry at last encoded frame -> next first frame",
            "pixel_identity_verified":False}
    left.meta.setdefault("carbon_shared",[]).append(record)


def concurrency_report(item,limit=3):
    if type(limit) is not int or not 1<=limit<=20: raise ValueError("attention limit must be integer in 1..20")
    from .carbon import APPEARANCE
    intervals=[];events={0.,item.duration}
    for root in item.nodes:
        for node in root.flatten():
            for prop,track in node.tracks.items():
                if prop not in APPEARANCE: continue
                for a,b in zip(track.keys,track.keys[1:]):
                    if a.value!=b.value and b.time>a.time:
                        intervals.append((max(0.,a.time),min(item.duration,b.time),node.role))
                        events.update((max(0.,a.time),min(item.duration,b.time)))
    times=sorted(t for t in events if 0<=t<=item.duration)
    peak=0
    for a,b in zip(times,times[1:]):
        t=(a+b)/2
        peak=max(peak,len({r for start,end,r in intervals if start<t<end}))
    return {"simultaneous_roles":peak,"limit":limit,"review_required":peak>limit,
            "basis":"track concurrency, not perceptual attention or aesthetic scoring"}


def apply_project(project,built):
    """Atomic graph transformation, invoked by the ordinary Studio build path."""
    active=any(s.get("carbon_choreography") is not None or s.get("carbon_shared") for s in project.scenes)
    if not active: return built
    result=[_clone_scene(item) for item in built]
    for scene,item in zip(project.scenes,result):
        if "camera_canvas" in scene and (scene.get("carbon_shared") or scene.get("carbon_choreography")):
            raise ValueError("Advanced Carbon choreography does not support Camera Canvas")
        config=scene.get("carbon_choreography") or {}
        if (scene.get("carbon_shared") or config.get("roles")) and scene.get("carbon_motion") is None:
            raise ValueError("Advanced motion requires an enabled Carbon profile")
        _roles(item,config,project)
    for i in range(len(result)-1):
        left,right=project.scenes[i:i+2]
        shared_a=left.get("carbon_shared",{});shared_b=right.get("carbon_shared",{})
        if not isinstance(shared_a,dict) or not isinstance(shared_b,dict): raise ValueError("Invalid shared bindings")
        for stable_id in sorted(set(shared_a)&set(shared_b)):
            if not isinstance(stable_id,str) or not stable_id or not all(isinstance(r,str) and r for r in (shared_a[stable_id],shared_b[stable_id])):
                raise ValueError("Shared IDs and roles must be nonempty strings")
            outgoing=left.get("transition_out") or {};incoming=right.get("transition_in") or {}
            kind=lambda value:value.get("type","cut") if isinstance(value,dict) else value or "cut"
            if kind(outgoing)!="cut" or kind(incoming)!="cut":
                raise ValueError("Shared bridge cannot be combined with scene transitions")
            for scene,role in ((left,shared_a[stable_id]),(right,shared_b[stable_id])):
                if (scene.get("carbon_choreography") or {}).get("roles",{}).get(role):
                    raise ValueError("Shared binding cannot also own role choreography")
            duration=number(left.get("carbon_bridge_duration",.7),"bridge duration",.1,2)
            _bridge(result[i],result[i+1],shared_a[stable_id],shared_b[stable_id],project,duration)
    for item in result:
        config=item.scene.get("carbon_choreography") or {}
        item.meta["carbon_concurrency"]=concurrency_report(item,config.get("attention_limit",3))
        item._subtree_settles.clear();item._settled_samples.clear()
    return result
