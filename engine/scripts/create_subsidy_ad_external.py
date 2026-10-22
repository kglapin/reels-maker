#!/usr/bin/env python3
"""ASTA Energy – 30 s promo about the home energy storage subsidy.

Only external footage is used (Wikimedia Commons, CC0 / public domain / CC BY).
Typography is rendered with PIL using measured baselines, a gradient scrim and
letter-spaced labels instead of solid text boxes.
"""
import subprocess, sys, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path('/Users/kamilglapinski_mbp14/Downloads/2592341240723747797')
ENGINE = ROOT/'engine'
ASSETS = ENGINE/'assets'
COMMONS = ASSETS/'commons'
WORK = ENGINE/'work'/'subsidy_ad_external'
OUTDIR = ROOT/'render'
WORK.mkdir(parents=True, exist_ok=True)
OUTDIR.mkdir(exist_ok=True)

FPS = 25
W, H = 1080, 1920

# ---------------------------------------------------------------- typography
FONT_BOLD = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
FONT_REG = '/System/Library/Fonts/Supplemental/Arial.ttf'

GREEN = (95, 227, 154, 255)
GREEN_DIM = (67, 190, 121, 255)
WHITE = (255, 255, 255, 255)
BODY = (223, 240, 230, 255)
MUTED = (176, 205, 188, 255)
INK = (4, 22, 18, 255)


def gradient_strip(size, top_alpha, bottom_alpha, color=INK):
    """Vertical alpha gradient used as a readability scrim."""
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


def render_card(index, kicker, headline, body, footnote='', logo=True):
    """Compose a full-frame caption card: gradient scrims, measured text, brand mark."""
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    # readability scrims: soft at the top for the logo, strong at the bottom for the copy
    im.alpha_composite(gradient_strip((W, 520), 165, 0).crop((0, 0, W, 520)), (0, 0))
    bottom = gradient_strip((W, 1000), 0, 238)
    im.alpha_composite(bottom, (0, H - 1000))

    d = ImageDraw.Draw(im)

    if logo:
        mark = ASSETS/'asta_logo.png'
        if mark.exists():
            logo_im = Image.open(mark).convert('RGBA')
            lw = 236
            lh = int(logo_im.height * lw / logo_im.width)
            logo_im = logo_im.resize((lw, lh), Image.LANCZOS)
            im.alpha_composite(logo_im, (88, 92))

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

    head_lead = 88
    body_lead = 54
    note_lead = 36
    gap_kicker_head = 26
    gap_head_body = 26
    gap_body_note = 30

    block_h = (34 + gap_kicker_head + head_lead * len(head_lines))
    if body_lines:
        block_h += gap_head_body + body_lead * len(body_lines)
    if note_lines:
        block_h += gap_body_note + note_lead * len(note_lines)

    bottom = H - 150
    y = bottom - block_h

    # accent bar aligned with the text block
    bar_top = y - 6
    bar_h = block_h + 12
    d.rounded_rectangle((margin, bar_top, margin + 6, bar_top + bar_h), radius=3, fill=GREEN)

    kicker_y = y
    letter_spaced(d, (text_left, kicker_y), kicker.upper(), f_kicker, GREEN, 3.2)
    y = kicker_y + 34 + gap_kicker_head

    for line in head_lines:
        d.text((text_left, y), line, font=f_head, fill=WHITE)
        y += head_lead

    if body_lines:
        y += gap_head_body - body_lead + 26
        for line in body_lines:
            d.text((text_left, y), line, font=f_body, fill=BODY)
            y += body_lead

    if note_lines:
        y += gap_body_note - note_lead + 26
        d.line((text_left, y - 14, W - margin, y - 14), fill=(120, 190, 150, 140), width=2)
        for line in note_lines:
            d.text((text_left, y), line, font=f_note, fill=MUTED)
            y += note_lead

    path = WORK/f'card_{index:02d}.png'
    im.save(path)
    return path


# ---------------------------------------------------------------- media plan
# (file, in-point, out-point, kicker, headline, body, footnote)
PLAN = [
    ('solar_home_animation.webm', 2.0, 5.4,
     'Dla właścicieli domu', 'Masz na dachu\nfotowoltaikę?',
     'Zostań z nadwyżkami energii — zamiast oddawać je do sieci, zgromadź je w domu.'),
    ('white_house_solar.webm', 73.5, 76.9,
     'Instalacja', 'Panele na dachu\nTwojego domu',
     'Fotowoltaika to pierwszy krok. Kolejny to magazyn energii.'),
    ('roof_pv.webm', 10.4, 13.8,
     'Program PME 2', 'Dotacja na magazyn\nenergii',
     'Nabór dofinansowania przydomowych magazynów energii trwa do 1 października 2027 r.'),
    ('agrivoltaics_heggelbach_01.webm', 13.0, 16.4,
     'Wsparcie dla domu', 'Do 19 000 zł\nna jeden PPE',
     'Tyle łącznie może wynieść wsparcie: magazyn energii, magazyn ciepła i premia UE.'),
    ('agrivoltaics_heggelbach_05.webm', 8.0, 11.4,
     'Dla kogo?', 'Prosument\nz instalacją OZE',
     'Mikroinstalacja przyłączona do sieci i wymagana umowa dotycząca sprzedaży energii.'),
    ('battery_cutaway.webm', 56.0, 59.4,
     'Techniczne wymogi', 'Magazyn\nmin. 10 kWh',
     'Pojemność nominalna co najmniej 10 kWh oraz dwa razy większa niż moc szczytowa PV.'),
    ('battery_cutaway.webm', 86.0, 89.4,
     'EMS i praca wyspowa', 'Inteligentne\nzarządzanie energią',
     'EMS steruje ładowaniem i rozładowaniem, a magazyn może zasilać dom awaryjnie.'),
    ('wind_turbine_montrigaud.webm', 2.0, 5.4,
     'Nabór aktywny', 'Premia UE\ndo 2 000 zł',
     'Gdy magazyn energii albo niezbędny falownik hybrydowy pochodzi z Unii Europejskiej.'),
    ('solar_home_animation.webm', 20.0, 23.4,
     'ASTA Energy', 'Porozmawiaj\nz doradcą',
     'Sprawdź, czy ta forma wsparcia pasuje do Twojej inwestycji.',
     'Kwota zależy od systemu rozliczeń, kosztów kwalifikowanych i warunków programu. Dotacja nie obejmuje samej fotowoltaiki.'),
]

CARDS = [
    ('Dla właścicieli domu', 'Masz na dachu\nfotowoltaikę?',
     'Zostań z nadwyżkami energii — zamiast oddawać je do sieci, zgromadź je w domu.'),
    ('Instalacja', 'Panele na dachu\nTwojego domu',
     'Fotowoltaika to pierwszy krok. Kolejny to magazyn energii.'),
    ('Program PME 2', 'Dotacja na magazyn\nenergii',
     'Nabór dofinansowania przydomowych magazynów energii trwa do 1 października 2027 r.'),
    ('Wsparcie dla domu', 'Do 19 000 zł\nna jeden PPE',
     'Tyle łącznie może wynieść wsparcie: magazyn energii, magazyn ciepła i premia UE.'),
    ('Dla kogo?', 'Prosument\nz instalacją OZE',
     'Mikroinstalacja przyłączona do sieci i wymagana umowa dotycząca sprzedaży energii.'),
    ('Techniczne wymogi', 'Magazyn\nmin. 10 kWh',
     'Pojemność nominalna co najmniej 10 kWh oraz dwa razy większa niż moc szczytowa PV.'),
    ('EMS i praca wyspowa', 'Inteligentne\nzarządzanie energią',
     'EMS steruje ładowaniem i rozładowaniem, a magazyn może zasilać dom awaryjnie.'),
    ('Nabór aktywny', 'Premia UE\ndo 2 000 zł',
     'Gdy magazyn energii albo niezbędny falownik hybrydowy pochodzi z Unii Europejskiej.'),
    ('ASTA Energy', 'Porozmawiaj\nz doradcą',
     'Sprawdź, czy ta forma wsparcia pasuje do Twojej inwestycji.',
     'Kwota zależy od systemu rozliczeń, kosztów kwalifikowanych i warunków programu. Dotacja nie obejmuje samej fotowoltaiki.'),
]


def run(args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def probe_duration(p):
    return float(subprocess.check_output(
        ['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(p)], text=True).strip())


def main():
    # Music: use the supplied track, beat-aligned phrase with a soft fade at the end.
    music = ROOT/'mewwwwwww-rush-433449.mp3'
    music_in = 10.635
    duration = 29.72

    shots = []
    for (fname, t_in, t_out, *_rest), card in zip(PLAN, CARDS):
        src = COMMONS/fname
        dur = probe_duration(src)
        start = min(t_in, max(0.0, dur - (t_out - t_in) - 0.2))
        shots.append((src, start, t_out - t_in))

    parts = []
    for i, ((src, start, length), card) in enumerate(zip(shots, CARDS)):
        shot = WORK/f'shot_{i:02d}.mp4'
        run(['ffmpeg','-y','-ss',f'{start:.3f}','-i',str(src),'-t',f'{length:.3f}','-an',
             '-vf','scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=25,format=yuv420p',
             '-c:v','h264_videotoolbox','-b:v','8M','-movflags','+faststart',str(shot)])

        png = render_card(i, *card)
        captioned = WORK/f'captioned_{i:02d}.mp4'
        graph = ('[0:v]format=rgba[t];[1:v][t]overlay=0:0:shortest=1,format=yuv420p[v]')
        run(['ffmpeg','-y','-loop','1','-framerate',str(FPS),'-t',f'{length:.3f}','-i',str(png),'-i',str(shot),
             '-filter_complex',graph,'-map','[v]','-an','-c:v','h264_videotoolbox','-b:v','8M',
             '-t',f'{length:.3f}',str(captioned)])
        parts.append(captioned)
        print(f'shot {i}: {src.name} {start:.1f}s -> {length:.2f}s')

    listing = WORK/'parts.txt'
    listing.write_text(''.join("file '" + str(p) + "'" + chr(10) for p in parts))
    base = WORK/'base.mp4'
    run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy',str(base)])

    out = OUTDIR/'asta_dotacje_magazyny_energii_30s_external.mp4'
    run(['ffmpeg','-y','-i',str(base),'-ss',f'{music_in:.3f}','-t',f'{duration:.3f}','-i',str(music),
         '-filter_complex',
         f'[1:a]atrim=duration={duration:.3f},asetpts=PTS-STARTPTS,volume=0.65,'
         f'afade=t=out:st={duration-1.2:.3f}:d=1.2[aout]',
         '-map','0:v','-map','[aout]','-c:v','copy','-c:a','aac','-b:a','192k',
         '-t',f'{duration:.3f}','-movflags','+faststart',str(out)])
    print('Created', out)


if __name__ == '__main__':
    main()
