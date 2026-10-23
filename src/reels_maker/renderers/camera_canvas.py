"""Opt-in shared canvas: arbitrary camera stops, rotation, and delayed text."""
from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

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
        if not scene.get("photo"):
            raise ValueError("camera_canvas scene requires photo")
        if cfg.get("layout","photo-above") not in ("photo-above","photo-left","offset","diagonal"):
            raise ValueError("Unknown camera_canvas layout")
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
            x,y,bw,bh=boxes[layout]
            x,y,pw,ph=int(x*w),int(y*h),int(bw*w),int(bh*h)
            path=Path(scene["photo"])
            if not path.is_file(): raise ValueError(f"Missing photo: {path}")
            with Image.open(path) as source:
                pic=ImageOps.fit(source.convert("RGB"),(pw,ph),method=Image.Resampling.LANCZOS)
            tile.alpha_composite(pic.convert("RGBA"),(x,y))
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
        c,s=math.cos(math.radians(angle)),math.sin(math.radians(angle))
        w,h=self.w,self.h
        mat=(zoom*c,-zoom*s,cx-zoom*c*w/2+zoom*s*h/2,
             zoom*s,zoom*c,cy-zoom*s*w/2-zoom*c*h/2)
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
                    (x1,max(y1,int(y2-(y2-y1)*p)),x2,y2),fill=255)
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
