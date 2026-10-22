#!/usr/bin/env python3
"""Create a <=30s Polish promo for ASTA home energy storage support."""
import os, subprocess, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path('/Users/kamilglapinski_mbp14/Downloads/2592341240723747797')
ENGINE = ROOT/'engine'
ASSETS = ENGINE/'assets'/'commons'
OUTDIR = ROOT/'render'
WORK = ENGINE/'work'/'subsidy_ad'
WORK.mkdir(exist_ok=True)
for p in WORK.iterdir():
    if p.is_file(): p.unlink()
OUTDIR.mkdir(exist_ok=True)

DURATION = 29.70
FPS = 25

# Source shots: ASTA supplied installation footage plus openly licensed Wikimedia Commons stock.
# Only the first shot starts at the beginning of its source. External stock is used with its applicable license.
shots = [
    (ROOT/'2_dron-pv-dla-firm-asta.mp4', 0.0, 3.35, 'ASTA footage'),
    (ASSETS/'roof_pv.webm', 11.4, 3.20, 'Commons CC BY 3.0'),
    (ROOT/'10_tracker-pv.mp4', 8.0, 3.30, 'ASTA footage'),
    (ASSETS/'solar_home_animation.webm', 8.2, 3.20, 'Commons CC0'),
    (ROOT/'11_chodzież-2x39,59kwp-fotowoltaika-asta.mp4', 5.0, 3.30, 'ASTA footage'),
    (ROOT/'12_pv na bloku.mp4', 6.0, 3.30, 'ASTA footage'),
    (ASSETS/'solar_home_animation.webm', 14.0, 3.25, 'Commons CC0'),
    (ROOT/'9_ dron-pv-dla-firm-asta-pila-49kwp.mp4', 6.0, 3.25, 'ASTA footage'),
    (ROOT/'8_asta-pila-realizacja-30kwp.mp4', 7.0, 3.55, 'ASTA footage'),
]

# Source durations align to the 29.70 second picture and music bed.
assert abs(sum(s[2] for s in shots)-DURATION) < 0.001

def run(args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

# Normalize every shot to the same vertical 9:16 format, retaining clean source audio-free video.
parts=[]
for i,(src,ss,dur,_) in enumerate(shots):
    dest=WORK/f'shot_{i:02d}.mp4'
    run(['ffmpeg','-y','-ss',f'{ss:.3f}','-i',str(src),'-t',f'{dur:.3f}','-an',
         '-vf','scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=25,format=yuv420p',
         '-c:v','h264_videotoolbox','-b:v','8M','-movflags','+faststart',str(dest)])
    parts.append(dest)

listing=WORK/'shots.txt'
listing.write_text(''.join(f"file '{p}'\n" for p in parts))
base=WORK/'base.mp4'
run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy',str(base)])

# Text cards: short, accurate claims based on the ASTA page checked 22 Oct 2026.
font_reg='/System/Library/Fonts/Supplemental/Arial.ttf'
font_bold='/System/Library/Fonts/Supplemental/Arial Bold.ttf'

def make_card(index, kicker, headline, body='', footer='', big=False):
    im=Image.new('RGBA',(1080,1920),(0,0,0,0))
    d=ImageDraw.Draw(im)
    # Bottom-safe translucent green-black panel with crisp ASTA green accent.
    x0,y0,x1,y1=66,1030,1014,1690
    d.rounded_rectangle((x0,y0,x1,y1),radius=34,fill=(5,27,24,232),outline=(67,218,123,245),width=4)
    d.rounded_rectangle((x0+28,y0+30,x0+40,y1-30),radius=6,fill=(82,227,125,255))
    x=80
    y=y0+54
    kfont=ImageFont.truetype(font_bold,34)
    hfont=ImageFont.truetype(font_bold,92 if big else 66)
    bfont=ImageFont.truetype(font_reg,40)
    ffont=ImageFont.truetype(font_reg,27)
    d.text((x+24,y),kicker.upper(),font=kfont,fill=(111,239,153,255))
    y+=66
    # wrap headings within panel width
    maxw=810
    lines=[]
    for paragraph in headline.split('\n'):
        words=paragraph.split(); line=''
        for word in words:
            test=(line+' '+word).strip()
            if d.textbbox((0,0),test,font=hfont)[2] > maxw and line:
                lines.append(line); line=word
            else: line=test
        if line: lines.append(line)
    for line in lines:
        d.text((x+24,y),line,font=hfont,fill=(255,255,255,255),stroke_width=0)
        y += int(hfont.size*1.12)
    y+=8
    for paragraph in body.split('\n') if body else []:
        words=paragraph.split(); line=''
        for word in words:
            test=(line+' '+word).strip()
            if d.textbbox((0,0),test,font=bfont)[2] > maxw and line:
                d.text((x+24,y),line,font=bfont,fill=(221,242,231,255)); y+=49; line=word
            else: line=test
        if line:
            d.text((x+24,y),line,font=bfont,fill=(221,242,231,255)); y+=49
    if footer:
        d.line((x+24,y1-105,x1-30,y1-105),fill=(100,170,130,180),width=2)
        ftext=footer
        # smaller footer wraps if needed
        words=ftext.split();line=''; fy=y1-88
        for word in words:
            test=(line+' '+word).strip()
            if d.textbbox((0,0),test,font=ffont)[2] > maxw and line:
                d.text((x+24,fy),line,font=ffont,fill=(184,212,195,255)); fy+=34; line=word
            else: line=test
        if line: d.text((x+24,fy),line,font=ffont,fill=(184,212,195,255))
    path=WORK/f'card_{index:02d}.png'
    im.save(path)
    return path

boundaries=[0.0,3.35,6.55,9.85,13.05,16.35,19.65,22.90,26.15,29.70]
card_specs=[
    ('Fotowoltaika w domu','Masz własną\ninstalację PV?','Zatrzymaj nadwyżki energii na później.',''),
    ('Więcej własnej energii','Magazynuj\nenergię ze słońca','Korzystaj z niej także wtedy, gdy instalacja nie produkuje.',''),
    ('Program PME 2','Dotacja na\nmagazyn energii','Dofinansowanie przydomowych magazynów energii.',''),
    ('Wsparcie dla domu','Do 19 000 zł*','maksymalnie na jeden punkt poboru energii','*Łączna kwota maksymalna; obowiązują limity i warunki programu.'),
    ('Kto może skorzystać?','Prosument z\ninstalacją OZE','Wymagana mikroinstalacja przyłączona do sieci i odpowiednia umowa.',''),
    ('Ważne wymogi','Magazyn min. 10 kWh','Wymagane m.in. EMS i możliwość pracy wyspowej (zasilanie awaryjne).',''),
    ('Nabór aktywny','Do 1.10.2027','lub do wyczerpania budżetu.',''),
    ('Sprawdź swoją inwestycję','Dotacja dla Twojego domu','Nabór trwa do 1.10.2027 lub do wyczerpania budżetu.',''),
    ('ASTA Energy','Porozmawiaj z doradcą','Sprawdź warunki na asta-energy.pl','asta-energy.pl/finansowanie/przydomowe-magazyny-energii/ • *Kwota zależy od systemu rozliczeń, kosztów kwalifikowanych i warunków programu. Dotacja nie obejmuje samej PV.'),
]
cards=[]
for i,spec in enumerate(card_specs):
    kicker,headline,body,footer=spec
    cards.append(make_card(i,kicker,headline,body,footer,big=(i==3)))

# Composite each caption with its corresponding shot separately to keep rendering efficient.
captioned=[]
for i,((src,ss,dur,_),png) in enumerate(zip(shots,cards)):
    part=WORK/f'shot_{i:02d}.mp4'
    text_dur=dur
    out=WORK/f'captioned_{i:02d}.mp4'
    graph=(f'[0:v]format=rgba,fade=t=in:st=0:d=0.20:alpha=1,'
           f'fade=t=out:st={text_dur-0.20:.3f}:d=0.20:alpha=1[txt];'
           f'[1:v][txt]overlay=0:0:shortest=1,format=yuv420p[v]')
    run(['ffmpeg','-y','-loop','1','-framerate',str(FPS),'-t',f'{text_dur:.3f}','-i',str(png),'-i',str(part),
         '-filter_complex',graph,'-map','[v]','-an','-c:v','h264_videotoolbox','-b:v','8M','-t',f'{dur:.3f}',str(out)])
    captioned.append(out)

# Join the already-captioned shots; add supplied music, trimmed to an energetic 29.7s section with a soft ending.
caption_list=WORK/'captioned.txt'
caption_list.write_text(''.join(f"file '{p}'\n" for p in captioned))
caption_base=WORK/'captioned_base.mp4'
run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(caption_list),'-c','copy',str(caption_base)])
outfile=OUTDIR/'asta_dotacje_magazyny_energii_30s.mp4'
run(['ffmpeg','-y','-i',str(caption_base),'-ss','10.635','-t',f'{DURATION:.3f}','-i',str(ROOT/'mewwwwwww-rush-433449.mp3'),
     '-filter_complex',f'[1:a]atrim=duration={DURATION:.3f},asetpts=PTS-STARTPTS,volume=0.70,afade=t=out:st={DURATION-1.1:.3f}:d=1.1[aout]',
     '-map','0:v','-map','[aout]','-c:v','copy','-c:a','aac','-b:a','192k','-t',f'{DURATION:.3f}','-movflags','+faststart',str(outfile)])

# Preserve licenses and attribution for external stock media used in the edit.
credits=ENGINE/'assets'/'stock_credits.txt'
credits.write_text('''ASTA Energy — promo video sources and stock attribution\n\nProgram facts: https://www.asta-energy.pl/finansowanie/przydomowe-magazyny-energii/\nChecked 22 October 2026. Confirm current NFOŚiGW rules before publishing.\n\nExternal stock footage:\n1) “Solar triplex home animation” — Wikideas1, Wikimedia Commons, CC0 1.0 (public domain dedication).\n   https://commons.wikimedia.org/wiki/File:Solar_triplex_home_animation.webm\n2) “Zonnepanelen op dak basisschool De Wegwijzer in Winssen” — RN7, Wikimedia Commons, CC BY 3.0.\n   https://commons.wikimedia.org/wiki/File:Zonnepanelen_op_dak_basisschool_De_Wegwijzer_in_Winssen.webm\n\nOther footage: ASTA Energy clips supplied by the client.\nMusic: “Rush”, supplied in the project folder by the client.\n''')
print(f'Created {outfile} ({DURATION:.2f}s)')
