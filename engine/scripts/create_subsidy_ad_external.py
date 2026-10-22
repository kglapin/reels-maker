#!/usr/bin/env python3
"""ASTA Energy – 30 s promo about the home energy storage subsidy (programme PME 2).

Only external footage is used (Wikimedia Commons: CC0 / public domain / CC BY).
Cards that talk about the energy storage itself are always backed by storage
hardware — never by photovoltaic imagery. Landscape clips are framed with a
blurred fill so the real subject stays visible in the vertical format.
"""
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ENGINE = Path(__file__).resolve().parents[1]
ROOT = ENGINE.parent
ASSETS = ENGINE/'assets'
COMMONS = ASSETS/'commons'
WORK = ENGINE/'work'/'subsidy_ad_external'
OUTDIR = ROOT/'render'
WORK.mkdir(parents=True, exist_ok=True)
OUTDIR.mkdir(exist_ok=True)

FPS = 25
W, H = 1080, 1920
SHOT_LEN = 3.30           # 9 shots x 3.30 s = 29.70 s
DURATION = SHOT_LEN * 9
MUSIC_IN = 10.635         # beat-aligned phrase of the supplied "Rush" track

FONT_BOLD = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
FONT_REG = '/System/Library/Fonts/Supplemental/Arial.ttf'
GREEN = (95, 227, 154, 255)
WHITE = (255, 255, 255, 255)
BODY = (223, 240, 230, 255)
MUTED = (176, 205, 188, 255)
INK = (4, 22, 18, 255)

# ------------------------------------------------------------------ typography
def gradient_strip(size, top_alpha, bottom_alpha, color=INK):
    w, h = size
    strip = Image.new('RGBA', (1, h))
    px = strip.load()
    for y in range(h):
        t = y / max(1, h - 1)
        a = top_alpha + (bottom_alpha - top_alpha) * t
        px[0, y] = (color[0], color[1], color[2], int(max(0, min(255, a))))
    return strip.resize((w, h))


def letter_spaced(draw, xy, text, font, fill, spacing):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + spacing
    return x - spacing


def wrap(draw, text, font, max_width):
    lines = []
    for paragraph in text.split('\n'):
        words = paragraph.split()
        if not words:
            continue
        line = words[0]
        for word in words[1:]:
            probe = line + ' ' + word
            if draw.textlength(probe, font=font) <= max_width:
                line = probe
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def render_card(index, kicker, headline, body, footnote=''):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    im.alpha_composite(gradient_strip((W, 520), 165, 0), (0, 0))
    im.alpha_composite(gradient_strip((W, 1000), 0, 238), (0, H - 1000))
    d = ImageDraw.Draw(im)

    mark = ASSETS/'asta_logo.png'
    if mark.exists():
        logo_im = Image.open(mark).convert('RGBA')
        lw = 236
        lh = int(logo_im.height * lw / logo_im.width)
        im.alpha_composite(logo_im.resize((lw, lh), Image.LANCZOS), (88, 92))

    margin = 88
    text_left = margin + 26
    max_width = W - text_left - margin

    f_kicker = ImageFont.truetype(FONT_BOLD, 30)
    f_head = ImageFont.truetype(FONT_BOLD, 78)
    f_body = ImageFont.truetype(FONT_REG, 37)
    f_note = ImageFont.truetype(FONT_REG, 25)

    head_lines = wrap(d, headline, f_head, max_width)
    body_lines = wrap(d, body, f_body, max_width) if body else []
    note_lines = wrap(d, footnote, f_note, max_width) if footnote else []

    head_lead, body_lead, note_lead = 88, 54, 36
    block_h = 34 + 26 + head_lead * len(head_lines)
    if body_lines:
        block_h += 26 + body_lead * len(body_lines)
    if note_lines:
        block_h += 30 + note_lead * len(note_lines)

    bottom = H - 150
    y = bottom - block_h
    d.rounded_rectangle((margin, y - 6, margin + 6, y - 6 + block_h + 12), radius=3, fill=GREEN)

    letter_spaced(d, (text_left, y), kicker.upper(), f_kicker, GREEN, 3.2)
    y += 34 + 26
    for line in head_lines:
        d.text((text_left, y), line, font=f_head, fill=WHITE)
        y += head_lead
    if body_lines:
        y += 26
        for line in body_lines:
            d.text((text_left, y), line, font=f_body, fill=BODY)
            y += body_lead
    if note_lines:
        y += 30
        d.line((text_left, y - 14, W - margin, y - 14), fill=(120, 190, 150, 140), width=2)
        for line in note_lines:
            d.text((text_left, y), line, font=f_note, fill=MUTED)
            y += note_lead

    path = WORK/f'card_{index:02d}.png'
    im.save(path)
    return path


# --------------------------------------------------------------------- plan
# file, in-point, framing, kicker, headline, body, footnote
# framing: 'crop' for aerial/vertical-friendly shots, 'pad' for wide shots that
# would lose their subject in a 9:16 crop.
PLAN = [
    ('battery_cutaway.webm', 49.5, 'pad',
     'Magazyn energii', 'Magazyn energii\nw Twoim domu',
     'Nadwyżki z fotowoltaiki zostają w domu i czekają na moment, gdy ich potrzebujesz.'),
    ('battery_cutaway.webm', 63.0, 'pad',
     'Magazyn energii', 'Ładuje się,\ngdy jest nadmiar',
     'EMS steruje ładowaniem i rozładowaniem magazynu, a zużycie energii planujesz sam.'),
    ('wind_turbine_montrigaud.webm', 3.0, 'crop',
     'Program PME 2', 'Dotacja do\n19 000 zł',
     'Tyle łącznie może wynieść wsparcie: magazyn energii, magazyn ciepła i premia UE.'),
    ('white_house_solar.webm', 106.0, 'pad',
     'Dla kogo?', 'Prosument\nz instalacją OZE',
     'Mikroinstalacja przyłączona do sieci oraz wymagana umowa dotycząca sprzedaży energii.'),
    ('battery_cutaway.webm', 78.0, 'pad',
     'Magazyn energii', 'Magazyn\nmin. 10 kWh',
     'Taka minimalna pojemność nominalna oraz dwukrotność mocy szczytowej instalacji PV.'),
    ('battery_cutaway.webm', 85.0, 'pad',
     'Magazyn energii', 'Praca wyspowa,\nczyli awaryjnie',
     'Sprzęt z EMS potrafi zasilać dom także wtedy, gdy zabraknie zasilania z sieci.'),
    ('white_house_solar.webm', 75.5, 'pad',
     'Nabór aktywny', 'Premia UE\ndo 2 000 zł',
     'Przysługuje, gdy magazyn energii albo niezbędny falownik hybrydowy pochodzi z UE.'),
    ('agrivoltaics_heggelbach_05.webm', 8.0, 'crop',
     'Nabór aktywny', 'Do 1.10.2027',
     'Nabór trwa do 1 października 2027 r. lub do wyczerpania budżetu programu.'),
    ('battery_cutaway.webm', 90.0, 'pad',
     'ASTA Energy', 'Porozmawiaj\nz doradcą',
     'Sprawdź, czy ta forma wsparcia pasuje do Twojej inwestycji.',
     'Kwota zależy od systemu rozliczeń, kosztów kwalifikowanych i warunków programu. Dotacja nie obejmuje samej fotowoltaiki.'),
]

CROP = 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=25,format=yuv420p'
PAD = ('[0:v]split=2[bg0][fg0];'
       '[bg0]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=28:2,eq=brightness=-0.10[b];'
       '[fg0]scale=1180:-2[f];[b][f]overlay=(W-w)/2:(H-h)/2-140,setsar=1,fps=25,format=yuv420p[v]')


def run(args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def main():
    parts = []
    for i, (fname, t_in, framing, *card) in enumerate(PLAN):
        src = COMMONS/fname
        shot = WORK/f'shot_{i:02d}.mp4'
        if framing == 'crop':
            vf_cmd = ['-vf', CROP, '-map', '0:v']
        else:
            vf_cmd = ['-filter_complex', PAD, '-map', '[v]']
        run(['ffmpeg','-y','-ss',f'{t_in:.3f}','-i',str(src),'-t',f'{SHOT_LEN:.3f}','-an',
             *vf_cmd,'-c:v','h264_videotoolbox','-b:v','8M',
             '-movflags','+faststart',str(shot)])

        png = render_card(i, *card)
        captioned = WORK/f'captioned_{i:02d}.mp4'
        run(['ffmpeg','-y','-loop','1','-framerate',str(FPS),'-t',f'{SHOT_LEN:.3f}','-i',str(png),'-i',str(shot),
             '-filter_complex','[0:v]format=rgba[t];[1:v][t]overlay=0:0:shortest=1,format=yuv420p[v]',
             '-map','[v]','-an','-c:v','h264_videotoolbox','-b:v','8M','-t',f'{SHOT_LEN:.3f}',str(captioned)])
        parts.append(captioned)
        print(f'shot {i}: {fname} @ {t_in}s ({framing})')

    listing = WORK/'parts.txt'
    listing.write_text(''.join("file '" + str(p) + "'" + chr(10) for p in parts))
    base = WORK/'base.mp4'
    run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy',str(base)])

    out = OUTDIR/'asta_dotacje_magazyny_energii_30s_external.mp4'
    run(['ffmpeg','-y','-i',str(base),'-ss',f'{MUSIC_IN:.3f}','-t',f'{DURATION:.3f}','-i',str(ROOT/'mewwwwwww-rush-433449.mp3'),
         '-filter_complex',
         f'[1:a]atrim=duration={DURATION:.3f},asetpts=PTS-STARTPTS,volume=0.65,'
         f'afade=t=out:st={DURATION-1.2:.3f}:d=1.2[aout]',
         '-map','0:v','-map','[aout]','-c:v','copy','-c:a','aac','-b:a','192k',
         '-t',f'{DURATION:.3f}','-movflags','+faststart',str(out)])
    print('Created', out)


if __name__ == '__main__':
    main()
