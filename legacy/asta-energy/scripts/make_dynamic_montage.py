#!/usr/bin/env python3
import os, subprocess, math, random, json
from pathlib import Path

D = Path('/Users/kamilglapinski_mbp14/Downloads/2592341240723747797')
TMP = Path('/tmp/asta_dynamic_montage')
TMP.mkdir(exist_ok=True)
# Clean temporary work from previous runs
for p in TMP.glob('*'):
    if p.is_file(): p.unlink()

# Music phrase: detected beats at 10.635s and 40.426s; a 44-beat phrase (~29.79s).
MUSIC_IN = 10.635
DURATION = 40.426 - MUSIC_IN
CUT_COUNT = 22
SEG_DUR = DURATION / CUT_COUNT

# Mix the available installation footage, maintaining portrait output and cutting every ~2 beats.
files = [
 '2_dron-pv-dla-firm-asta.mp4',
 '10_tracker-pv.mp4',
 '1_fotowoltaika-25wp-budzyn.mp4',
 '11_chodzież-2x39,59kwp-fotowoltaika-asta.mp4',
 '3_pila-elektronarzedzia-39,6kwp.mp4',
 '12_pv na bloku.mp4',
 '14_Piła-pv-39,96-kwp.mp4',
 '4_Copy of mini max-reels .mp4',
 '7_pila-pv-30,50 kWp - przedszkole.mp4',
 '15_fotowoltaika-spoldzielnia.mp4',
 '9_ dron-pv-dla-firm-asta-pila-49kwp.mp4',
 '13_Copy of asta - konstrukcja tracker.mp4',
 '6_fotowoltaika - poudnie czy wschod zachod.mp4',
 '8_asta-pila-realizacja-30kwp.mp4',
 '5_reels-asta-pv-dla-branzy-drzewnej.mp4',
]

def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

def probe_duration(p):
    s = subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(p)], text=True)
    return float(s.strip())

# Probe sources and pick varied short extracts, rotating through all clips.
meta = [(D/f, probe_duration(D/f)) for f in files]
segments=[]
for i in range(CUT_COUNT):
    src, srcdur = meta[i % len(meta)]
    length = SEG_DUR
    # Distribute each selection across the source rather than repeatedly taking its opening.
    uses = (CUT_COUNT + len(meta)-1)//len(meta)
    occurrence = i // len(meta)
    # Reserve at least 2 seconds before the source clip's ending to avoid outro shots.
    max_start = max(0.0, srcdur - length - 2.0)
    # Keep only the intentionally selected opening shot at source time zero.
    # Every other shot starts after the opening and stays clear of the source ending.
    if i == 0:
        start = 0.0
    else:
        low = min(1.5, max_start)
        fraction = (occurrence + 1) / (uses + 1)
        start = min(max_start, max(low, max_start * fraction))
    out = TMP / f'shot_{i:02d}.mp4'
    run(['ffmpeg','-y','-ss',f'{start:.3f}','-i',str(src),'-t',f'{length:.4f}',
         '-an','-vf','scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=25,format=yuv420p',
         '-c:v','libx264','-preset','fast','-crf','19','-movflags','+faststart',str(out)])
    segments.append(out)

# Concatenate normalized shots losslessly (all have identical video properties).
concat = TMP/'shots.txt'
concat.write_text(''.join(f"file '{p}'\n" for p in segments))
base = TMP/'base.mp4'
run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(base)])

# Cycle through visibly different transition treatments and varied moments of all three assets.
# Every source is green-tinted, but each has its own blend character: glow, flare, strip-flash, wash.
fx_specs = [
    ('254934_medium.mp4', 3.0,  'screen',    0.62, 0.46, 'hue=s=0,colorize=hue=120:saturation=0.92:lightness=0.50:mix=0.95'),
    ('270109_medium.mp4', 1.45, 'softlight', 0.62, 0.52, 'hue=s=0,colorize=hue=120:saturation=0.82:lightness=0.50:mix=0.95'),
    ('270108_medium.mp4', 2.75, 'addition',  0.24, 0.30, 'hue=s=0,colorize=hue=120:saturation=0.72:lightness=0.50:mix=0.92'),
    ('254934_medium.mp4', 4.45, 'lighten',   0.72, 0.38, 'hue=s=0,colorize=hue=120:saturation=0.95:lightness=0.50:mix=0.96'),
    ('270109_medium.mp4', 4.35, 'screen',    0.48, 0.48, 'hue=s=0,colorize=hue=120:saturation=0.88:lightness=0.50:mix=0.94'),
    ('270108_medium.mp4', 0.45, 'addition',  0.32, 0.34, 'hue=s=0,colorize=hue=120:saturation=0.78:lightness=0.50:mix=0.94'),
    ('254934_medium.mp4', 5.45, 'screen',    0.58, 0.54, 'hue=s=0,colorize=hue=120:saturation=0.90:lightness=0.50:mix=0.95'),
    ('270109_medium.mp4', 2.05, 'hardlight', 0.36, 0.36, 'hue=s=0,colorize=hue=120:saturation=0.80:lightness=0.50:mix=0.92'),
    ('270108_medium.mp4', 3.65, 'lighten',   0.34, 0.42, 'hue=s=0,colorize=hue=120:saturation=0.75:lightness=0.50:mix=0.93'),
]
args=['ffmpeg','-y','-i',str(base),'-ss',f'{MUSIC_IN:.3f}','-t',f'{DURATION:.4f}','-i',str(D/'mewwwwwww-rush-433449.mp3')]
for i in range(CUT_COUNT-1):
    fx_name, fx_start, mode, opacity, fx_duration, look = fx_specs[i % len(fx_specs)]
    args += ['-ss',f'{fx_start:.3f}','-t',f'{fx_duration:.3f}','-i',str(D/fx_name)]

filters=['[0:v]format=gbrp[base_rgb]']
cur='base_rgb'
for i in range(CUT_COUNT-1):
    inp=2+i
    fx_name, fx_start, mode, opacity, fx_duration, look = fx_specs[i % len(fx_specs)]
    # Place each extracted effect fragment across the cut, with asset-specific blend/strength.
    start=(i+1)*SEG_DUR - fx_duration/2
    stop=start+fx_duration
    ov=f'ov{i}'
    out=f'v{i}'
    filters.append(f'[{inp}:v]trim=duration={fx_duration:.3f},setpts=PTS-STARTPTS+{start:.4f}/TB,{look},scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=gbrp[{ov}]')
    filters.append(f'[{cur}][{ov}]blend=all_mode={mode}:all_opacity={opacity:.2f}:enable=between(t\\,{start:.4f}\\,{stop:.4f})[{out}]')
    cur=out
filters.append(f'[{cur}]trim=duration={DURATION:.4f},setpts=PTS-STARTPTS,fps=25,format=yuv420p[vout]')
filters.append(f'[1:a]atrim=duration={DURATION:.4f},asetpts=PTS-STARTPTS,afade=t=out:st={DURATION-1.2:.4f}:d=1.2[aout]')
outfile=TMP/'final.mp4'
args += ['-filter_complex',';'.join(filters),'-map','[vout]','-map','[aout]','-c:v','libx264','-preset','fast','-crf','19','-c:a','aac','-b:a','192k','-t',f'{DURATION:.4f}','-movflags','+faststart',str(outfile)]
run(args)

# Replace prior logo version only after successful export. Final has no logo; it contains rapid cuts and overlays.
target=D/'rush_433449_varied-green-overlay-transitions.mp4'
os.replace(outfile,target)
print(f'Created {target} — {DURATION:.3f}s, {CUT_COUNT} shots (~{SEG_DUR:.2f}s each), no logo.')
