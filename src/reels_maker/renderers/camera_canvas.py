"""Opt-in shared canvas: arbitrary camera stops, rotation, and delayed text."""
from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from ..core.transforms import (
    Affine2D, Bounds, Point, Space, TransformHierarchy, TransformNode,
)

def ease(v):
    t=min(1,max(0,float(v)))
    return t*t*(3-2*t)

def validate_camera_canvas(scenes):
    if not scenes or not all(isinstance(s.get("camera_canvas"),dict) for s in scenes):
        raise ValueError("camera_canvas must be configured on all scenes")
    for scene in scenes:
        cfg=scene["camera_canvas"]
        for key in ("x","y"):
            val=cfg.get(key)
            if not isinstance(val,(int,float)) or not math.isfinite(val) or val<0 or val>16000:
                raise ValueError(f"Invalid camera_canvas {key}")
        for key,lo,hi in (("angle",-720,720),("zoom",.65,2),
                          ("move_duration",.05,4),("reveal_delay",0,3),
                          ("reveal_duration",.05,3)):
            val=float(cfg.get(key,0 if key in ("angle","reveal_delay") else 1))
            if not math.isfinite(val) or not lo<=val<=hi:
                raise ValueError(f"Invalid camera_canvas {key}")
        if not (scene.get("photo") or scene.get("video")):
            raise ValueError("camera_canvas scene requires photo or video")
        if cfg.get("layout","photo-above") not in ("photo-above","photo-left","offset","diagonal"):
            raise ValueError("Unknown camera_canvas layout")
        if cfg.get("crop") is not None:
            crop = cfg["crop"]
            if (not isinstance(crop, (list, tuple)) or len(crop) != 4
                    or not (0.0 <= float(crop[0]) < float(crop[2]) <= 1.0
                            and 0.0 <= float(crop[1]) < float(crop[3]) <= 1.0)):
                raise ValueError("Invalid camera_canvas crop")
        if cfg.get("mask", "rect") not in ("rect", "rounded", "circle", "pill"):
            raise ValueError("Unknown camera_canvas mask")
    return True

class CameraCanvasRenderer:
    def __init__(self,project):
        self.scenes=project.scenes
        self.w,self.h=project.width,project.height
        validate_camera_canvas(self.scenes)
        stops=[]
        for s in self.scenes:
            c=s["camera_canvas"]
            stops.append((float(c["x"]),float(c["y"]),
                          float(c.get("angle",0)),float(c.get("zoom",1))))
        self.stops=stops
        ww=int(max(x for x,y,a,z in stops)+self.w*1.5)
        hh=int(max(y for x,y,a,z in stops)+self.h*1.5)
        if ww*hh>32000000:
            raise ValueError("camera_canvas world exceeds 32MP")
        base=Image.new("RGBA",(ww,hh),(247,245,240,255))
        self.stages=[base]
        for i,s in enumerate(self.scenes):
            tile=self._tile(s,photo=True)
            self._paste(base,tile,self.stops[i])
        self.stages=[base.copy()]
        self.local_typography=[]
        for i,s in enumerate(self.scenes):
            tile=self._tile(s,photo=False)
            self.local_typography.append(tile)
            new=self.stages[-1].copy()
            self._paste(new,tile,self.stops[i])
            self.stages.append(new)

    def _font(self,size,bold):
        for p in (["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if bold else
                  ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]):
            if Path(p).is_file():
                return ImageFont.truetype(p,size)
        return ImageFont.load_default()

    def _tile(self,scene,photo):
        w,h=self.w,self.h
        tile=Image.new("RGBA",(w,h),(0,0,0,0))
        layout=scene["camera_canvas"].get("layout","photo-above")
        boxes={"photo-above":(.10,.10,.80,.45),"photo-left":(.08,.17,.59,.52),
               "offset":(.22,.09,.68,.43),"diagonal":(.09,.18,.77,.43)}
        if photo:
            from . import canvas as cv
            cfg = scene["camera_canvas"]
            x,y,bw,bh=boxes[layout]
            x,y,pw,ph=int(x*w),int(y*h),int(bw*w),int(bh*h)
            asset_path = scene.get("video") or scene.get("photo")
            path=Path(asset_path)
            if not path.is_file(): raise ValueError(f"Missing photo: {path}")
            source = cv.load_video_frame(
                path,
                float(cfg.get("sample_time", 0.0)),
                trim_start=float(cfg.get("trim_start", 0.0)),
                trim_end=cfg.get("trim_end"),
            )
            source = cv.crop_region(source, cfg.get("crop"))
            pic=ImageOps.fit(source.convert("RGB"),(pw,ph),method=Image.Resampling.LANCZOS)
            masked = cv.apply_shape_mask(
                pic.convert("RGBA"),
                cfg.get("mask", "rect"),
                radius=float(cfg.get("radius", 18.0)),
            )
            tile.alpha_composite(masked,(x,y))
        else:
            title=scene.get("headline") or ""
            if isinstance(title,dict):
                title=" ".join(str(r.get("text","")) for r in title.get("runs",[]))
            text=str(title).strip()
            x,y={"photo-above":(.09,.65),"photo-left":(.09,.76),
                 "offset":(.10,.61),"diagonal":(.10,.67)}[layout]
            d=ImageDraw.Draw(tile); px,py=int(x*w),int(y*h)
            size=int(w*.095)
            while size>16 and d.textbbox((0,0),text,font=self._font(size,True))[2]>int(w*.83):
                size-=1
            d.text((px,py),text,font=self._font(size,True),fill=(24,31,30,255))
            sub=str(scene.get("subtitle") or "")
            size=int(w*.037)
            while size>11 and d.textbbox((0,0),sub,font=self._font(size,False))[2]>int(w*.83):
                size-=1
            d.text((px,py+int(h*.095)),sub,font=self._font(size,False),fill=(81,100,91,255))
        return tile

    @staticmethod
    def _paste(world,tile,stop):
        x,y,angle,_=stop
        rot=tile.rotate(-angle,resample=Image.Resampling.BICUBIC,expand=True)
        world.alpha_composite(rot,(round(x-rot.width/2),round(y-rot.height/2)))

    def camera(self,index,time):
        if index==0:return self.stops[0]
        cfg=self.scenes[index]["camera_canvas"]
        p=ease(time/float(cfg.get("move_duration",.8)))
        return tuple(a+(b-a)*p for a,b in zip(self.stops[index-1],self.stops[index]))

    def _frame(self,world,stop):
        cx,cy,angle,zoom=stop
        w,h=self.w,self.h
        # Pillow's affine API maps output viewport pixels back to world pixels.
        # Keep that established sampling direction, but express the matrix in
        # the shared coordinate-space contract used by Studio Node bounds.
        camera_to_world = camera_viewport_to_world(
            cx, cy, angle, zoom, w, h)
        mat=(camera_to_world.a, camera_to_world.c, camera_to_world.e,
             camera_to_world.b, camera_to_world.d, camera_to_world.f)
        return world.transform((w,h),Image.Transform.AFFINE,mat,
                               resample=Image.Resampling.BILINEAR).convert("RGBA")

    def render(self,built,time):
        """Travel across preexisting canvas; reveal shot-local type only on arrival."""
        from PIL import ImageChops
        i=built.index; cfg=self.scenes[i]["camera_canvas"]
        move=0 if i==0 else float(cfg.get("move_duration",.8))
        delay=float(cfg.get("reveal_delay",.18))
        duration=float(cfg.get("reveal_duration",.55))
        p=ease((time-move-delay)/duration)
        stop=self.camera(i,time)
        base=self._frame(self.stages[i],stop)
        if p<=0:return base.convert("RGB")

        # At reveal time camera is settled. Typography is drawn in the
        # target shot's camera-facing coordinates (not an unrelated slide).
        overlay=self.local_typography[i].copy()
        effect=cfg.get("typography_motion","fade")
        if effect not in ("fade","slide-up","mask-rise","scale-focus"):
            raise ValueError(f"Unsupported camera_canvas typography_motion: {effect}")
        if effect=="mask-rise":
            bounds=overlay.getbbox()
            if bounds:
                x1,y1,x2,y2=bounds
                clip=Image.new("L",overlay.size,0)
                ImageDraw.Draw(clip).rectangle(
                    (x1,y1,x2,min(y2,int(y1+(y2-y1)*p))),fill=255)
                overlay.putalpha(ImageChops.multiply(overlay.getchannel("A"),clip))
        elif effect=="scale-focus":
            scale=.91+.09*p
            overlay=overlay.resize((max(1,int(overlay.width*scale)),
                                    max(1,int(overlay.height*scale))),
                                   Image.Resampling.BICUBIC)
        else:
            overlay.putalpha(overlay.getchannel("A").point(
                lambda value:int(value*p)))
        # A camera zoom >1 exposes more world space, so the local text
        # contracts proportionally when rendered in screen coordinates.
        zoom=stop[3]
        if zoom!=1:
            overlay=overlay.resize((max(1,int(overlay.width/zoom)),
                                    max(1,int(overlay.height/zoom))),
                                   Image.Resampling.BICUBIC)
        x=(self.w-overlay.width)//2
        y=(self.h-overlay.height)//2
        if effect=="slide-up":
            y+=round((1-p)*min(self.h*.085,62))
        base.alpha_composite(overlay,(x,y))
        return base.convert("RGB")


def camera_viewport_to_world(cx: float, cy: float, angle: float, zoom: float,
                             width: int, height: int) -> Affine2D:
    """Return Pillow's output-viewport-to-world sampling transform."""
    values = (cx, cy, angle, zoom)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Camera values must be finite")
    if zoom <= 0 or type(width) is not int or type(height) is not int \
            or width <= 0 or height <= 0:
        raise ValueError("Camera zoom and viewport dimensions must be positive")
    cosine, sine = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    return Affine2D(
        a=zoom * cosine, b=zoom * sine,
        c=-zoom * sine, d=zoom * cosine,
        e=cx - zoom * cosine * width / 2 + zoom * sine * height / 2,
        f=cy - zoom * sine * width / 2 - zoom * cosine * height / 2,
        source=Space.VIEWPORT, target=Space.WORLD)


def camera_world_to_viewport(cx: float, cy: float, angle: float, zoom: float,
                             width: int, height: int) -> Affine2D:
    """Return the exact forward transform mapping world coordinates to viewport."""
    return camera_viewport_to_world(cx, cy, angle, zoom, width, height).inverse()


_LAYOUT_PHOTO_BOXES = {
    "photo-above": (.10, .10, .80, .45),
    "photo-left": (.08, .17, .59, .52),
    "offset": (.22, .09, .68, .43),
    "diagonal": (.09, .18, .77, .43),
}

_LAYOUT_TEXT_ORIGINS = {
    "photo-above": (.09, .65),
    "photo-left": (.09, .76),
    "offset": (.10, .61),
    "diagonal": (.10, .67),
}


def build_camera_canvas_hierarchy(
    scenes: list[dict], width: int, height: int
) -> tuple[TransformHierarchy, dict[str, Bounds]]:
    """Build a shared TransformHierarchy and local bounds for Camera Canvas shots.

    Each shot tile has its own root node in world space (centered at stop x, y
    and rotated by stop angle) plus child nodes for its photo subject and
    typography block in tile-local coordinates.
    """
    validate_camera_canvas(scenes)
    if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
        raise ValueError("Viewport dimensions must be positive integers")
    hierarchy = TransformHierarchy()
    local_bounds: dict[str, Bounds] = {}
    for index, scene in enumerate(scenes):
        cfg = scene["camera_canvas"]
        sx = float(cfg["x"])
        sy = float(cfg["y"])
        angle = float(cfg.get("angle", 0.0))
        layout = cfg.get("layout", "photo-above")
        rad = math.radians(angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        # Tile-local (0..width, 0..height) centered around (width/2, height/2)
        # mapped into world coordinates at (sx, sy) with rotation `angle`.
        cx_local, cy_local = width / 2.0, height / 2.0
        tx = sx - (cos_a * cx_local - sin_a * cy_local)
        ty = sy - (sin_a * cx_local + cos_a * cy_local)
        shot_id = f"shot-{index}"
        hierarchy.add(TransformNode(
            shot_id,
            Affine2D(a=cos_a, b=sin_a, c=-sin_a, d=cos_a, e=tx, f=ty,
                     source=Space.LOCAL, target=Space.WORLD),
            parent_id=None,
        ))
        local_bounds[shot_id] = Bounds(0.0, 0.0, float(width), float(height))

        px, py, pw, ph = _LAYOUT_PHOTO_BOXES[layout]
        photo_id = f"{shot_id}/photo"
        hierarchy.add(TransformNode(
            photo_id,
            Affine2D(e=px * width, f=py * height,
                     source=Space.LOCAL, target=Space.PARENT),
            parent_id=shot_id,
        ))
        local_bounds[photo_id] = Bounds(0.0, 0.0, pw * width, ph * height)

        tx_rel, ty_rel = _LAYOUT_TEXT_ORIGINS[layout]
        text_id = f"{shot_id}/typography"
        hierarchy.add(TransformNode(
            text_id,
            Affine2D(e=tx_rel * width, f=ty_rel * height,
                     source=Space.LOCAL, target=Space.PARENT),
            parent_id=shot_id,
        ))
        local_bounds[text_id] = Bounds(
            0.0, 0.0, width * .83, min(height * .22, height * (1.0 - ty_rel - .04))
        )
    return hierarchy, local_bounds


def _rect_intersection_area(a: Bounds, b: Bounds) -> float:
    ix = max(0.0, min(a.right, b.right) - max(a.left, b.left))
    iy = max(0.0, min(a.bottom, b.bottom) - max(a.top, b.top))
    return ix * iy


def plan_camera_path(
    scenes: list[dict],
    width: int,
    height: int,
    *,
    max_angle_delta: float = 45.0,
    min_subject_retention: float = 0.55,
) -> dict:
    """Validate camera path travel, rotation deltas and subject retention (MD-204).

    Measures how much of each shot's photo subject remains inside the output
    viewport when settled and across intermediate travel probes.
    """
    hierarchy, local_bounds = build_camera_canvas_hierarchy(scenes, width, height)
    viewport_bounds = Bounds(0.0, 0.0, float(width), float(height))
    stops = [
        (float(s["camera_canvas"]["x"]), float(s["camera_canvas"]["y"]),
         float(s["camera_canvas"].get("angle", 0.0)),
         float(s["camera_canvas"].get("zoom", 1.0)))
        for s in scenes
    ]
    transitions = []
    violations = []
    for index, stop in enumerate(stops):
        photo_id = f"shot-{index}/photo"
        photo_to_world = hierarchy.world_transform(photo_id)
        vp_map = camera_world_to_viewport(*stop, width, height)
        photo_vp = photo_to_world.then(vp_map).map_bounds(local_bounds[photo_id])
        subject_area = max(1.0, (photo_vp.right - photo_vp.left) * (photo_vp.bottom - photo_vp.top))
        settled_retention = _rect_intersection_area(photo_vp, viewport_bounds) / subject_area
        if settled_retention < min_subject_retention:
            violations.append({
                "scene": index + 1,
                "code": "subject_retention_low",
                "retention": round(settled_retention, 4),
                "minimum": min_subject_retention,
            })
        if index == 0:
            transitions.append({
                "scene": 1,
                "distance_px": 0.0,
                "angle_delta_deg": 0.0,
                "settled_subject_retention": round(settled_retention, 4),
                "arrival_probe_retentions": [round(settled_retention, 4)],
            })
            continue
        prev = stops[index - 1]
        distance = math.hypot(stop[0] - prev[0], stop[1] - prev[1])
        angle_delta = abs(stop[2] - prev[2])
        if angle_delta > max_angle_delta:
            violations.append({
                "scene": index + 1,
                "code": "excessive_camera_rotation",
                "angle_delta_deg": round(angle_delta, 3),
                "maximum": max_angle_delta,
            })
        probe_retentions = []
        for fraction in (.5, .75, 1.0):
            p = ease(fraction)
            interp = tuple(a + (b - a) * p for a, b in zip(prev, stop))
            vp_box = photo_to_world.then(
                camera_world_to_viewport(*interp, width, height)
            ).map_bounds(local_bounds[photo_id])
            vp_area = max(1.0, (vp_box.right - vp_box.left) * (vp_box.bottom - vp_box.top))
            probe_retentions.append(
                round(_rect_intersection_area(vp_box, viewport_bounds) / vp_area, 4)
            )
        transitions.append({
            "scene": index + 1,
            "distance_px": round(distance, 2),
            "angle_delta_deg": round(angle_delta, 3),
            "settled_subject_retention": round(settled_retention, 4),
            "arrival_probe_retentions": probe_retentions,
        })
    return {
        "ok": not violations,
        "scene_count": len(scenes),
        "transitions": transitions,
        "violations": violations,
    }


def bezier_camera_point(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    """Evaluate a 2D cubic-Bezier camera trajectory at normalized progress t in 0..1 (MD-504)."""
    u = max(0.0, min(1.0, float(t)))
    om = 1.0 - u
    x = (om ** 3) * p0[0] + 3 * (om ** 2) * u * p1[0] + 3 * om * (u ** 2) * p2[0] + (u ** 3) * p3[0]
    y = (om ** 3) * p0[1] + 3 * (om ** 2) * u * p1[1] + 3 * om * (u ** 2) * p2[1] + (u ** 3) * p3[1]
    return (round(x, 4), round(y, 4))


def apply_camera_motion_blur(
    frame: Image.Image,
    velocity_px: float,
    *,
    max_radius: float = 6.0,
) -> Image.Image:
    """Apply speed-proportional spatial blur during fast camera travel (MD-504)."""
    from PIL import ImageFilter

    if velocity_px <= 12.0 or max_radius <= 0:
        return frame
    radius = min(float(max_radius), (float(velocity_px) - 12.0) / 80.0)
    if radius < 0.35:
        return frame
    return frame.filter(ImageFilter.GaussianBlur(radius=round(radius, 2)))
