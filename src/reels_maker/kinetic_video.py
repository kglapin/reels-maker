"""Native frame-by-frame kinetic graphics for reels-maker.

Manifest-driven Cairo renderer; optional dependencies, no per-campaign fork.
"""
import io
import json
import math
import subprocess
from pathlib import Path

from .ffmpeg import RenderError, probe, require_tool
from .kinetics import ease_out_cubic, counter_value, format_pln


KINDS = ("amount", "breakdown", "announcement", "donut", "comparison",
         "heat", "europe", "deadline", "urgency", "cta")


def render_kinetic(manifest, *, root=None, output=None):
    try:
        import cairocffi as cairo
        from PIL import Image
    except ImportError as exc:
        raise RenderError('Install pip install -e ".[kinetic]"') from exc
    manifest = Path(manifest).resolve()
    root = Path(root or manifest.parent).resolve()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    video = data.get("video", {})
    width, height, fps = (video.get("width", 720), video.get("height", 1280),
                          video.get("fps", 25))
    if (any(type(x) is not int for x in (width, height, fps))
            or width % 2 or height % 2 or not
            (360 <= width <= 1920 and 640 <= height <= 2160 and 15 <= fps <= 60)):
        raise RenderError("Invalid kinetic dimensions or frame rate")
    scenes = data.get("scenes", [])
    if not isinstance(scenes, list) or not scenes:
        raise RenderError("Expected a nonempty scenes list")
    for n, item in enumerate(scenes):
        if (not isinstance(item, dict) or item.get("type") not in KINDS
                or not isinstance(item.get("duration"), (int, float))
                or not .5 <= item["duration"] <= 30):
            raise RenderError(f"Invalid kinetic scene {n}")
    def asset(value):
        path = Path(value)
        path = (root / path).resolve() if not path.is_absolute() else path.resolve()
        if not path.is_file():
            raise RenderError(f"Missing asset {path}")
        return path

    voice = asset(data["voiceover"]) if data.get("voiceover") else None
    music = asset(data["music"]) if data.get("music") else None
    logo = asset(data["logo"]) if data.get("logo") else None
    photos = {s["photo"]: asset(s["photo"]) for s in scenes if s.get("photo")}
    result = Path(output or data.get("output") or root / "kinetic.mp4").resolve()
    result.parent.mkdir(parents=True, exist_ok=True)
    frame_counts = []
    ticks = 0.0
    last = 0
    for scene in scenes:
        ticks += scene["duration"]
        next_frame = round(ticks * fps)
        frame_counts.append(next_frame-last)
        last = next_frame
    W,H=720,1280
    GREEN=(71,160,19); DARK=(22,44,30); PALE=(239,247,234)
    WHITE=(255,255,255); GRAY=(98,112,101); BORDER=(215,230,209)
    surf=cairo.ImageSurface(cairo.FORMAT_ARGB32,width,height)
    c=cairo.Context(surf)
    c.scale(width/W,height/H)
    cache={}
    def rgb(value,alpha=1):
        c.set_source_rgba(*(v/255 for v in value),max(0,min(1,alpha)))
    def rect(x,y,w,h,col,alpha=1):
        rgb(col,alpha);c.rectangle(x,y,w,h);c.fill()
    def rounded(x,y,w,h,r,col,alpha=1):
        r=min(r,w/2,h/2);c.new_path()
        c.arc(x+w-r,y+r,r,-math.pi/2,0)
        c.arc(x+w-r,y+h-r,r,0,math.pi/2)
        c.arc(x+r,y+h-r,r,math.pi/2,math.pi)
        c.arc(x+r,y+r,r,math.pi,1.5*math.pi)
        c.close_path();rgb(col,alpha);c.fill()
    def text(value,x,y,size,col=DARK,weight=True):
        c.select_font_face("Open Sans",cairo.FONT_SLANT_NORMAL,
                           cairo.FONT_WEIGHT_BOLD if weight else cairo.FONT_WEIGHT_NORMAL)
        while size>16:
            c.set_font_size(size)
            e=c.text_extents(str(value))
            if e.width<=620: break
            size-=2
        e=c.text_extents(str(value))
        rgb(col)
        c.move_to(x-e.x_bearing-e.width/2,y-e.y_bearing)
        c.show_text(str(value))
    def pop(t,onset,duration,x,y,fn,scale=.88):
        if t<onset:return
        raw=min(1,(t-onset)/duration)
        p=ease_out_cubic(raw); alpha=min(1,(t-onset)/.17)
        s=scale+(1-scale)*p
        c.save();c.translate(x,y+30*(1-p));c.scale(s,s);c.push_group()
        fn()
        c.pop_group_to_source();c.paint_with_alpha(alpha);c.restore()
    def image_surface(path):
        path=str(path)
        if path not in cache:
            im=Image.open(path).convert("RGBA")
            mem=io.BytesIO();im.save(mem,format="PNG");mem.seek(0)
            cache[path]=(cairo.ImageSurface.create_from_png(mem), im.width,im.height)
        return cache[path]
    def photo(path,t):
        img,w,h=image_surface(photos[path]); k=max(720/w,1085/h)*(1.02+.13*ease_out_cubic(t/3.5))
        c.save();c.rectangle(0,195,720,1085);c.clip()
        c.translate(360,738);c.scale(k,k);c.translate(-w*.5,-h*.5)
        c.set_source_surface(img,0,0);c.get_source().set_filter(cairo.FILTER_BEST)
        c.paint();c.restore()
    def battery(t):
        rounded(-210,-105,420,210,30,WHITE)
        rounded(210,-39,20,78,7,BORDER)
        rounded(-180,-74,360,148,14,PALE)
        charge=5*ease_out_cubic((t-.65)/1.3)
        for i in range(5):
            rounded(-166+67*i,-57,56,114,8,GREEN,max(.12,min(1,charge-i)))
    def chart(t):
        c.set_line_width(72)
        c.new_path();c.arc(0,0,173,0,2*math.pi);rgb(BORDER);c.stroke()
        p=ease_out_cubic((t-.55)/1.0)
        if p>0:
            c.new_path()
            c.arc(0,0,173,-math.pi/2,-math.pi/2+2*math.pi*.3*p)
            rgb(GREEN);c.set_line_cap(cairo.LINE_CAP_ROUND);c.stroke()
        text(f"{round(30*p)}%",0,-64,105,GREEN)
        text("KOSZTÓW",0,52,28,GRAY)
    def header(index):
        rect(0,0,720,180,DARK);rect(0,180,720,7,GREEN)
        if logo:
            im,w,h=image_surface(logo); scale=260/w
            c.save();c.translate(360-130,58-h*scale/2);c.scale(scale,scale)
            c.set_source_surface(im,0,0);c.paint();c.restore()
        else:text("ASTA ENERGY",360,43,42,WHITE)
        text(f"{index+1:02d} / {len(scenes):02d}",360,122,22,(216,230,208),False)
    def scene_frame(s,index,t):
        kind=s["type"]
        rect(0,0,720,1280,PALE)
        if s.get("photo"):
            photo(s["photo"],t)
            rect(0,195,720,1085,WHITE,.77)
        if kind=="amount":
            pop(t,.08,.45,360,345,lambda:text(s.get("kicker","DOTACJA DO"),0,0,42))
            amount=counter_value(int(s.get("value",16000)),int(t*fps),int(.3*fps),int(1.3*fps))
            pop(t,.3,.5,360,465,lambda:text(format_pln(amount),0,0,116,GREEN))
            pop(t,.9,.4,360,587,lambda:text(s.get("subtitle","NA MAGAZYN ENERGII"),0,0,35))
            pop(t,.65,.55,360,921,lambda:battery(t))
        elif kind=="breakdown":
            pop(t,.08,.4,360,341,lambda:text("ŁĄCZNIE NAWET",0,0,42))
            v=counter_value(int(s.get("value",19000)),int(t*fps),int(.25*fps),int(1.1*fps))
            pop(t,.25,.48,360,452,lambda:text(format_pln(v),0,0,118,GREEN))
            for j,(title,val) in enumerate((("MAGAZYN ENERGII","16 000 zł"),
                    ("MAGAZYN CIEPŁA","1 000 zł"),("PREMIA UE","2 000 zł"))):
                def card(title=title,val=val):
                    rounded(-305,-52,610,110,22,WHITE)
                    text(title,-119,-22,28,DARK)
                    text(val,164,18,32,GREEN)
                pop(t,.62+j*.26,.43,360,660+j*145,card)
        elif kind=="announcement":
            pop(t,.09,.45,360,370,lambda:text("NABÓR",0,0,112))
            pop(t,.3,.45,360,496,lambda:text("OTWARTY",0,0,103,GREEN))
            pop(t,.62,.44,360,621,lambda:text("PRZYDOMOWE MAGAZYNY ENERGII",0,0,34))
            def calendar():
                rounded(-250,-137,500,275,30,WHITE)
                text("20",0,-111,147,GREEN)
                text("PAŹDZIERNIKA 2026",0,58,35)
            pop(t,.9,.55,360,903,calendar)
        elif kind=="donut":
            pop(t,.1,.45,360,356,lambda:text("MAGAZYN ENERGII",0,0,56))
            pop(t,.4,.52,360,804,lambda:chart(t),.96)
            pop(t,1.5,.45,360,1125,lambda:text("DO 30% KOSZTÓW KWALIFIKOWANYCH",0,0,34))
        elif kind=="comparison":
            pop(t,.08,.45,360,329,lambda:text("DWA SYSTEMY ROZLICZEŃ",0,0,40))
            for j,(name,value) in enumerate((("NET-BILLING",16000),("NET-METERING",8000))):
                def card(name=name,value=value,j=j):
                    rounded(-308,-127,616,254,28,WHITE)
                    text(name,0,-93,41)
                    v=counter_value(value,int(t*fps),int((.6+j*.82)*fps),int(1*fps))
                    text(format_pln(v),0,4,91,GREEN)
                pop(t,.42+j*.83,.5,360,568+j*338,card)
        elif kind=="heat":
            pop(t,.1,.44,360,365,lambda:text("MAGAZYN CIEPŁA",0,0,65))
            def icon():
                c.new_path();c.arc(0,0,170,0,2*math.pi);rgb((255,234,205));c.fill()
                text("CIEPŁO",0,-43,64,(201,94,29))
                for i in range(3):
                    c.new_path();c.arc(0,-30+i*60,100+i*14,math.pi*.18,math.pi*.7)
                    rgb((226,100,29));c.set_line_width(8);c.stroke()
            pop(t,.35,.5,360,805,icon)
            val=counter_value(1000,int(t*fps),int(.82*fps),int(1.15*fps))
            pop(t,.85,.46,360,1119,lambda:text("DO "+format_pln(val),0,0,85,GREEN))
        elif kind=="europe":
            pop(t,.1,.4,360,346,lambda:text("SPRZĘT Z UE",0,0,83))
            def flag():
                c.new_path();c.arc(0,0,172,0,2*math.pi);rgb((0,51,153));c.fill()
                for i in range(12):
                    p=ease_out_cubic((t-.5-i*.06)/.35)
                    if p:
                        angle=i*math.pi/6-math.pi/2+t*.07
                        text("★",140*math.cos(angle),140*math.sin(angle)-15,42*p,(255,204,0))
                text("UE",0,-58,99,WHITE)
            pop(t,.3,.55,360,797,flag)
            val=counter_value(2000,int(t*fps),int(1*fps),int(1*fps))
            pop(t,1.0,.46,360,1111,lambda:text("+ DO "+format_pln(val),0,0,81,GREEN))
        elif kind=="deadline":
            pop(t,.1,.4,360,358,lambda:text("NABÓR DO",0,0,66))
            pop(t,.36,.5,360,511,lambda:text("1.10.2027",0,0,116,GREEN))
            pop(t,.92,.45,360,681,lambda:text("LUB DO WYCZERPANIA BUDŻETU",0,0,35))
            text("BUDŻET PROGRAMU",360,855,29,GRAY)
            rounded(88,930,544,56,28,BORDER)
            p=ease_out_cubic((t-1.13)/1.8)
            rounded(88,930,544*(1-.8*p),56,28,(209,107,38) if p>.7 else GREEN)
        elif kind=="urgency":
            pop(t,.06,.45,360,356,lambda:text("NIE ZWLEKAJ",0,0,104,(192,65,34)))
            def clock():
                c.new_path();c.arc(0,0,181,0,2*math.pi);rgb(WHITE);c.fill()
                for i in range(12):
                    a=i*math.pi/6
                    c.new_path();c.move_to(144*math.cos(a),144*math.sin(a))
                    c.line_to(157*math.cos(a),157*math.sin(a))
                    rgb(DARK);c.set_line_width(7);c.stroke()
                for rad,ang in ((119,t*5-math.pi/2),(73,t*.9-math.pi/2)):
                    c.new_path();c.move_to(0,0);c.line_to(rad*math.cos(ang),rad*math.sin(ang))
                    rgb(DARK);c.set_line_width(10);c.stroke()
            pop(t,.38,.55,360,805,clock)
            pop(t,1.03,.48,360,1110,lambda:text("NIE PRZEGAP OKAZJI",0,0,49,GREEN))
        elif kind=="cta":
            pop(t,.1,.44,360,355,lambda:text("ZADZWOŃ LUB NAPISZ",0,0,57))
            def phone():
                rounded(-305,-104,610,207,36,GREEN)
                text(s.get("phone","67 350 90 90"),0,-53,79,WHITE)
                text("SPRAWDŹ DOTACJĘ",0,46,35,WHITE)
            pop(t,.38,.5,360,639,phone)
            pop(t,.99,.4,360,917,lambda:text("SPRAWDZIMY ILE MOŻESZ ZYSKAĆ",0,0,31))
            pop(t,1.45,.4,360,1002,lambda:text("POMOŻEMY W CAŁYM PROCESIE",0,0,31))
            pop(t,1.9,.4,360,1122,lambda:text("asta-energy.pl",0,0,62,GREEN))
        header(index)
        remain=s["duration"]-t
        if index<len(scenes)-1 and remain <.17:
            rect(0,0,720*ease_out_cubic((.17-remain)/.17),1280,GREEN)
    args=[require_tool("ffmpeg"),"-hide_banner","-loglevel","error","-y",
          "-f","rawvideo","-pix_fmt","bgra","-s",f"{width}x{height}","-r",str(fps),"-i","-"]
    if voice:args+=["-i",str(voice)]
    if music:args+=["-i",str(music)]
    if voice and music:
        args += ["-filter_complex",
            "[1:a]aformat=channel_layouts=stereo[v];"
            "[2:a]aformat=channel_layouts=stereo,volume=0.14[m];"
            "[m][v]sidechaincompress=threshold=0.018:ratio=8:attack=40:release=400[d];"
            "[v][d]amix=inputs=2:duration=first:normalize=0[a]",
            "-map","0:v","-map","[a]"]
    elif voice or music:args += ["-map","0:v","-map","1:a"]
    args+=["-frames:v",str(sum(frame_counts)),"-c:v","libx264","-preset","veryfast",
           "-crf","20","-pix_fmt","yuv420p","-movflags","+faststart"]
    if voice or music:args+=["-c:a","aac","-b:a","192k"]
    args+=[str(result)]
    p=subprocess.Popen(args,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for index,(scene,count) in enumerate(zip(scenes,frame_counts)):
            for j in range(count):
                c.identity_matrix();c.scale(width/W,height/H)
                scene_frame(scene,index,j/fps)
                surf.flush()
                p.stdin.write(bytes(surf.get_data()))
        p.stdin.close()
        stderr=p.stderr.read().decode(errors="replace")
        if p.wait():
            raise RenderError("Kinetic FFmpeg error: "+stderr[-2000:])
    except Exception:
        if p.poll() is None:p.kill()
        raise
    metadata=probe(result)
    return {"ok":True,"output":str(result),"frames":sum(frame_counts),
            "scenes":len(scenes),"types":sorted({s["type"] for s in scenes}),
            "duration":float(metadata["format"]["duration"]),"width":width,
            "height":height,"fps":fps}
