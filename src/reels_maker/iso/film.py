"""Film timeline: state model, eased cameras, typography and frame assembly."""
from __future__ import annotations

import functools
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import world as _world_mod
from .projection import (
    C,
    DEFAULT_PALETTE,
    E,
    W,
    H,
    Canvas,
    decal,
    glyph,
    mix,
    resolve_font,
    snow_layer,
    vignette,
)
from .world import (
    PUMP_C,
    PUMP_COIL,
    PUMP_FAN,
    TLAB,
    TILES,
    UD,
    UH,
    UW,
    UX,
    UY,
    air_streams,
    boiler_room,
    buffer_tank,
    circulator,
    compressor,
    controller,
    drops,
    expansion_vessel,
    glow_layer,
    ground_patch,
    house,
    icicles,
    lawn_ground,
    obstacles,
    pipes,
    plume_layer,
    puddle,
    pump,
    ring,
    snow_ground,
    thermostat,
    tile_house,
    tile_warning,
)

FILM_DURATION = 110.0
OFFSET = 0.25

import threading as _threading

_mute_shadow = _threading.local()
_orig_contact_shadow = _world_mod.contact_shadow


def _contact_shadow_dispatch(*args, **kwargs):
    if getattr(_mute_shadow, "on", False):
        return None
    return _orig_contact_shadow(*args, **kwargs)


_world_mod.contact_shadow = _contact_shadow_dispatch

# (start, headline, body lines) — the proven 14-beat educational arc, kept whole.
COPY_BEATS = [
    (0, "Biała para nad pompą ciepła.",
     ["Zauważyłeś białą mgiełkę nad jednostką",
      "i zastanawiasz się, czy to usterka?",
      "Zimą to zazwyczaj całkowicie naturalny objaw."]),
    (7, "To automatyczne odszranianie.",
     ["Gdy na zewnątrz jest chłodno i wilgotno,",
      "wymiennik pompy pokrywa się szronem,",
      "który urządzenie musi okresowo usunąć."]),
    (15, "Skąd bierze się szron na lamelach?",
     ["Wentylator przetłacza wilgotne powietrze",
      "przez zimny wymiennik ciepła. Cząsteczki wody",
      "błyskawicznie zamarzają na metalowych lamelach."]),
    (27, "Pompa na chwilę odwraca obieg.",
     ["Wentylator zatrzymuje się, a układ kieruje",
      "ciepło do wymiennika zewnętrznego,",
      "aby szybko i bezpiecznie stopić nagromadzony lód."]),
    (39, "Biała para to efekt topnienia lodu.",
     ["Rozgrzany wymiennik styka się z mroźnym",
      "powietrzem, tworząc lekką parę wodną.",
      "Powstała woda swobodnie spływa do odpływu."]),
    (49, "Cykl trwa zazwyczaj kilka minut.",
     ["Długość odszraniania zależy od wilgotności,",
      "temperatury oraz algorytmu sterownika.",
      "Urządzenie samo decyduje o zakończeniu cyklu."]),
    (59, "Ogrzewanie domu wraca samoczynnie.",
     ["Gdy lamele wymiennika zostaną oczyszczone,",
      "wentylator natychmiast startuje ponownie,",
      "a pompa wraca do stabilnego ogrzewania budynku."]),
    (66, "Lód nie znika po cyklu?",
     ["Lód nie znika mimo zakończenia cyklu,",
      "a gruba bryła narasta na wymienniku."]),
    (72, "Odszranianie bez przerwy?",
     ["Odszranianie powtarza się bez przerwy,",
      "a pompa nie dogrzewa pomieszczeń."]),
    (78, "Błąd na sterowniku?",
     ["Na sterowniku widnieje kod usterki,",
      "czuć zapach przegrzania lub słychać hałas."]),
    (84, "W domu za zimno?",
     ["Pompa nie utrzymuje zadanej temperatury,",
      "a odpływ skroplin zamarzł pod jednostką."]),
    (90, "Czego nie wolno robić zimą?",
     ["Nigdy nie skuwaj lodu ostrymi narzędziami",
      "ani nie polewaj obudowy wrzątkiem.",
      "Zadbaj o swobodny odpływ wody i czysty wlot."]),
    (100, "Spokojna zima z pompą ciepła.",
     ["Obserwuj naturalną pracę urządzenia,",
      "a w razie wątpliwości skonsultuj się",
      "z certyfikowanym serwisem ASTA Energy."]),
]
COPY_END = 110.0


def speed(u):
    if u < 14:
        return 0.0
    if u < 15.5:
        return E((u - 14) / 1.5)
    if u < 27.5:
        return 1.0
    if u < 29:
        return 1 - E((u - 27.5) / 1.5)
    if u < 49:
        return 0.0
    if u < 50:
        return E(u - 49)
    if u < 53.3:
        return 1.0
    if u < 53.9:
        return 1 - E((u - 53.3) / 0.6)
    if u < 56.5:
        return 0.0
    if u < 57.2:
        return E((u - 56.5) / 0.7)
    return 1.0


TG = np.arange(0, FILM_DURATION + 1, 1 / 60)
CUM = np.cumsum([speed(x) for x in TG]) / 60


def fan_angle(u):
    return float(np.interp(u, TG, CUM)) * math.tau * 1.5


def bump(x, a, b, ra, rb):
    return E((x - a) / ra) * (1 - E((x - b) / rb))


def ustate(u, P):
    c = (u - 49) / 10 if 49 <= u < 59 else None
    if u < 7:
        f = 0.30 - 0.18 * E(u / 7)
    elif u < 14:
        f = 0.12 * (1 - E((u - 7) / 6.5))
    elif u < 15:
        f = 0.0
    elif u < 26:
        f = 0.88 * E((u - 15) / 11)
    elif u < 29.5:
        f = 0.88
    elif u < 37.5:
        f = 0.88 * (1 - E((u - 29.5) / 8))
    elif u < 49:
        f = 0.0
    elif c is not None:
        f = 0.82 * E(c / 0.45) if c < 0.45 else 0.82 * (1 - E((c - 0.45) / 0.3)) if c < 0.75 else 0.0
    else:
        f = 0.0

    if u < 7:
        g = 0.85
    elif u < 14:
        g = 0.85 * (1 - E((u - 7) / 6.5))
    elif u < 27.5:
        g = 0.0
    elif u < 29.5:
        g = E((u - 27.5) / 2)
    elif u < 39:
        g = 1.0
    elif u < 47:
        g = 1 - E((u - 39) / 8)
    elif c is not None:
        g = bump(c, 0.45, 0.75, 0.03, 0.05)
    else:
        g = 0.0

    if u < 7:
        p = 0.9 - 0.2 * E(u / 7)
    elif u < 13.5:
        p = 0.7 * (1 - E((u - 7) / 6))
    elif u < 31:
        p = 0.0
    elif u < 39:
        p = 0.82 * E((u - 31) / 3)
    elif u < 48:
        p = 0.82 * (1 - E((u - 41) / 7)) if u >= 41 else 0.82
    elif c is not None:
        p = 0.78 * bump(c, 0.5, 0.74, 0.04, 0.05)
    else:
        p = 0.0

    if u < 7:
        dr = 0.6 * (1 - E(u / 7))
    elif 30 <= u < 45:
        dr = E((u - 30) / 2) * (1 - E((u - 39) / 5))
    elif c is not None:
        dr = 0.8 * bump(c, 0.55, 0.8, 0.05, 0.05)
    else:
        dr = 0.0

    if u < 14:
        pd = 0.6 * (1 - E((u - 3) / 10)) if u > 3 else 0.6
    elif 33 <= u < 50:
        pd = 0.9 * E((u - 33) / 5) * (1 - E((u - 44) / 5))
    else:
        pd = 0.0

    ring_val = max(bump(u, 7, 13.6, 1, 1.2), bump(u, 28, 38, 0.8, 0.8),
                   bump(c, 0.45, 0.76, 0.03, 0.04) * 0.9 if c is not None else 0)
    if 15 <= u < 28:
        air = E((u - 15.5) / 1) * (1 - E((u - 26.5) / 1))
    elif c is not None:
        air = 0.6 * E(c * 10) if c < 0.45 else 0.6 * E((c - 0.78) * 10) if c > 0.78 else 0.0
    elif 59 <= u < 110:
        air = 0.55 * E((u - 59) / 1) * (1 - E((u - 64.5) / 1)) + 0.5 * E((u - 96) / 2) * (u >= 96)
    else:
        air = 0.0

    return dict(frost=f, heat=g, plume=p, drip=dr, puddle=pd, ring=ring_val, air=air,
                speed=speed(u), angle=fan_angle(u),
                led=P["amber"] if g > 0.05 else P["mint"])


def _iso_uv(p):
    return C * (p[0] - p[1]), (p[0] + p[1]) * 0.5 - p[2]


def focus(p, k, screen=(540, 1140), spin=0.0):
    u, v = _iso_uv(p)
    if spin:
        c, s = math.cos(spin), math.sin(spin)
        u, v = u * c - v * s, u * s + v * c
    return k, (screen[0] - u * k, screen[1] - v * k)


def cammix(a, b, p):
    return a[0] + (b[0] - a[0]) * p, mix(a[1], b[1], p)


WP = (-0.9, -1.5, 1.0)
PP = (1.0, -1.0, 1.0)
S5 = (540, 985)

KEYS = [
    (0, focus(PUMP_FAN, 470)),
    (3, focus(PUMP_FAN, 410)),
    (7, focus(PUMP_C, 235)),
    (15, focus(PUMP_C, 255)),
    (17, focus(PUMP_COIL, 390)),
    (27, focus(PUMP_COIL, 430)),
    (37, focus(PUMP_COIL, 380)),
    (39, focus(PP, 265)),
    (49, focus(PP, 240)),
    (51, focus(PUMP_C, 215, S5)),
    (59, focus(PUMP_C, 215, S5)),
    (66, focus(WP, 105)),
    (90, focus(PUMP_C, 215)),
    (100, focus(WP, 104)),
    (110, focus(WP, 100)),
]


def world_cam(u, drift=True):
    for (a, aa), (b, bb) in zip(KEYS, KEYS[1:]):
        if a <= u <= b:
            k, origin = cammix(aa, bb, E((u - a) / (b - a)))
            if drift:
                # Subtle handheld breathing so holds never feel frozen.
                ox = 5 * math.sin(u * 0.5) + 2 * math.sin(u * 1.13)
                oy = 4 * math.cos(u * 0.37) + 2 * math.sin(u * 0.91)
                origin = (origin[0] + ox, origin[1] + oy)
            return k, origin
    return KEYS[-1][1]


def tile_cam(u):
    pos = 0.0
    for j in (1, 2, 3):
        pos += E((u - (66 + 6 * j - 0.6)) / 1.2)
    return focus((TILES[0][0] + 3.6 * pos + 0.1, -0.1, 0.6), 170, (540, 1060))


def tile_state(v, u, P):
    base = dict(frost=0.0, heat=0.0, speed=0.0, angle=0.0, led=P["mint"])
    if v == 0:
        base.update(frost=0.96, led=P["amber"])
    elif v == 1:
        ph = (u * 0.62) % 1
        g = bump(ph, 0.15, 0.45, 0.08, 0.08)
        base.update(frost=0.55 * (1 - g) + 0.1, heat=g, led=P["amber"] if g > 0.05 else P["mint"])
    elif v == 2:
        base.update(speed=1.0, angle=fan_angle(u + 12) + 0.15 * math.sin(u * 14),
                    led=(255, 110, 92))
    else:
        base.update(speed=1.0, angle=fan_angle(u + 5))
    return base


@functools.lru_cache(maxsize=1024)
def _asset(s, n, col, font_path, bold=False):
    fp = font_path or resolve_font()
    if bold:
        from pathlib import Path as _P
        from reels_maker.iso.projection import resolve_font_bold as _rb
        cand = (fp.replace("Regular", "Bold").replace("regular", "bold"))
        try:
            fp = cand if (cand != fp and _P(cand).is_file()) else _rb()
        except Exception:
            fp = _rb()
    z = glyph(s, n * 2, tuple(col), fp)
    return z.resize((math.ceil(z.width / 2), math.ceil(z.height / 2)), Image.Resampling.LANCZOS)


def asset(s, n, col, font_path, bold=False):
    return _asset(s, n, tuple(col), font_path or "", bold)


TITLE_MAX_WIDTH = W - 256  # symmetric 128 px margins, like the body copy
TITLE_SIZE = 52
TITLE_LINE_STEP = 62


def wrap_title(title, font_path, size=52, max_width=TITLE_MAX_WIDTH,
               bold=False):
    """Split an overflowing headline into balanced lines within margins.

    Single-line titles pass through untouched (identical frames); longer
    ones break at the word boundary that minimizes the longest line.
    """
    words = str(title).split()
    if len(words) < 2:
        return [str(title)]
    widths = [asset(" ".join(words[:k]), size, (255, 255, 255), font_path,
                   bold).width
              for k in range(1, len(words))]
    full = asset(str(title), size, (255, 255, 255), font_path, bold).width
    if full <= max_width:
        return [str(title)]
    best, best_over = None, None
    for k in range(1, len(words)):
        first = widths[k - 1]
        second = asset(" ".join(words[k:]), size, (255, 255, 255),
                       font_path, bold).width
        over = max(first, second)
        if over <= max_width and (best_over is None or over < best_over):
            best, best_over = k, over
    if best is None:
        # No balanced 2-line break fits: greedy multi-line wrap.
        out, cur = [], []
        for w_ in words:
            trial = cur + [w_]
            if cur and asset(" ".join(trial), size, (255, 255, 255),
                             font_path, bold).width > max_width:
                out.append(" ".join(cur))
                cur = [w_]
            else:
                cur = trial
        if cur:
            out.append(" ".join(cur))
        return out or [str(title)]
    return [" ".join(words[:best]), " ".join(words[best:])]


MAIN_GREEN = (62, 134, 43)


def text_render(im, boxes, s, x, y, font_path, n=34, col=(248, 249, 240), a=1.0, dy=0.0,
                dx=0.0, bold=False):
    z = asset(s, n, tuple(col), font_path, bold)
    b = (x, y, x + z.width, y + z.height)
    boxes.append((s, b))
    if a <= 0.003:
        return z.width
    if a < 1:
        z = z.copy()
        z.putalpha(z.getchannel("A").point(lambda v: round(v * a)))
    im.paste(z, (round(x + dx), round(y + dy)), z)
    return z.width


TYPE_T0, TYPE_DT, TYPE_GAP, TYPE_BDT = 0.15, 0.22, 0.35, 0.13


def _bold_font_path(font_path):
    from pathlib import Path as _P
    from reels_maker.iso.projection import resolve_font_bold as _rb
    fp = font_path or resolve_font()
    cand = fp.replace("Regular", "Bold").replace("regular", "bold")
    try:
        if cand != fp and _P(cand).is_file():
            return cand
    except Exception:
        pass
    return _rb()


def wrap_body_lines(lines, font, max_width=TITLE_MAX_WIDTH):
    """Greedy word wrap for body copy into visual lines."""
    out = []
    for txt in lines:
        words = str(txt).split()
        cur = []
        for w_ in words:
            trial = cur + [w_]
            if cur and font.getlength(" ".join(trial)) / 2 > max_width:
                out.append(" ".join(cur))
                cur = [w_]
            else:
                cur = trial
        if cur:
            out.append(" ".join(cur))
    return out


BODY_BASE, BODY_MIN = 40, 30


@functools.lru_cache(maxsize=64)
def _body_fit(texts_key, font_path):
    """Per-scene body size: fit the longest line, shrink to fit."""
    from PIL import ImageFont as _F
    fp = font_path or resolve_font()
    fnt = _F.truetype(fp, BODY_BASE * 2)
    maxw = 0.0
    for t, _s in texts_key:
        if str(t).strip():
            maxw = max(maxw, fnt.getlength(str(t)) / 2)
    size = BODY_BASE
    if maxw > TITLE_MAX_WIDTH:
        size = max(BODY_MIN, BODY_BASE * TITLE_MAX_WIDTH / maxw)
    size = int(round(size))
    return size, int(round(size * 46 / BODY_BASE))


@functools.lru_cache(maxsize=64)
def _typed_layout(title, body_key, tsize, font_path, ty0=340.0, by0=440.0):
    """Word images at 2x for sharp dolly moves; cuts measured with the
    SAME rasterizer that drew them (zero drift). All coords in 1x px."""
    from PIL import ImageFont as _F
    body = [(str(a), str(b)) for a, b in body_key]
    bold_fp = _bold_font_path(font_path)
    reg_fp = font_path or resolve_font()
    bold_fnt = _F.truetype(bold_fp, tsize * 2)
    _bsize, _bstep = _body_fit(body_key, font_path)
    reg_fnt = _F.truetype(reg_fp, _bsize * 2)
    tstep = TITLE_LINE_STEP * tsize / TITLE_SIZE
    lines = wrap_title(title, font_path, tsize, bold=True)
    items, wi = [], 0
    for k, line in enumerate(lines):
        words = str(line).split()
        img = _typed_line(str(line), bold_fnt, tsize)
        if img is None:
            continue
        cuts = [bold_fnt.getlength(" ".join(words[:i + 1])) / 2 - img[1]
                for i in range(len(words))]
        items.append({"img": img[0], "x0": 128 + img[1],
                      "y0": ty0 + tstep * k + img[2],
                      "cuts": cuts, "n": len(words), "off": wi, "title": True,
                      "fw": img[3]})
        wi += len(words)
    title_end = TYPE_T0 + max(wi - 1, 0) * TYPE_DT
    bj = 0
    vj = 0
    for j, (txt, side) in enumerate(body):
        if side and side not in ("left", "right"):
            raise ValueError(
                f"copy line 'from' must be left/right, got {side!r}")
        for vtxt in wrap_body_lines([txt], reg_fnt):
            words = vtxt.split()
            img = _typed_line(vtxt, reg_fnt, _bsize)
            if img is None:
                continue
            cuts = [reg_fnt.getlength(" ".join(words[:i + 1])) / 2 - img[1]
                    for i in range(len(words))]
            items.append({"img": img[0], "x0": 128 + img[1],
                          "y0": by0 + _bstep * vj + img[2],
                          "cuts": cuts, "n": len(words), "off": bj,
                          "title": False,
                          "base": title_end + TYPE_GAP, "fw": img[3]})
            bj += len(words)
            vj += 1
    last_t = title_end + TYPE_GAP + max(bj - 1, 0) * TYPE_BDT if bj else title_end
    tb = [it for it in items if it["title"]]
    if tb:
        px0 = min(it["x0"] for it in tb)
        px1 = max(it["x0"] + it["fw"] for it in tb)
        py0 = min(it["y0"] for it in tb)
        py1 = max(it["y0"] + it["img"].height / 2 for it in tb)
    else:
        px0, px1, py0, py1 = 128.0, 952.0, 340.0, 340.0 + tsize
    return {"items": items, "last_t": last_t, "span": wi,
            "pivot": ((px0 + px1) / 2, (py0 + py1) / 2)}


def _typed_line(text, font, size):
    """One RGBA line at 2x + trims and full width in 1x px."""
    if not text.strip():
        return None
    layer = Image.new("RGBA", ((TITLE_MAX_WIDTH + 40) * 2, size * 2 + 40),
                      (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text((0, 0), text, font=font, fill=(255, 255, 255, 255))
    bbox = layer.getchannel("A").getbbox()
    if not bbox:
        return None
    return (layer.crop(bbox), bbox[0] / 2, bbox[1] / 2,
            (bbox[2] - bbox[0]) / 2)


def _paste_typed_layer(im, lay, t, a):
    """Word-by-word reveal with a real dolly move (1.0->1.7->1.0),
    rendered from 2x masters so the punch-in stays sharp."""
    items = lay["items"]
    z = 1.0
    cx, cy = lay["pivot"]
    shown = []
    for it in items:
        for i in range(it["n"]):
            if it["title"]:
                wt = TYPE_T0 + (it["off"] + i) * TYPE_DT
            else:
                wt = it["base"] + (it["off"] + i) * TYPE_BDT
            if t < wt:
                break
            wa = a * E(min(max((t - wt) / 0.18, 0.0), 1.0))
            if wa > 0.003:
                shown.append((it, i, wa))
    if not shown:
        return
    last = None
    for it, i, wa in shown:
        x0 = max(0 if i == 0 else it["cuts"][i - 1], 0)
        x1 = min(it["cuts"][i], it["fw"])
        if x1 <= x0:
            continue
        seg = it["img"].crop((int(round(x0 * 2)), 0,
                              int(round(x1 * 2)), it["img"].height))
        dw = max(1, round((x1 - x0) * z))
        dh = max(1, round(it["img"].height / 2 * z))
        if (dw, dh) != seg.size:
            seg = seg.resize((dw, dh), Image.Resampling.LANCZOS)
        if wa < 1:
            seg = seg.copy()
            seg.putalpha(seg.getchannel("A").point(lambda v: round(v * wa)))
        px = cx + (it["x0"] + x0 - cx) * z
        py = cy + (it["y0"] - cy) * z
        im.paste(seg, (round(px), round(py)), seg)
        last = (it, x1)
    cur = lay["last_t"]
    if t < cur + 0.6 and (t * 2.5) % 1 < 0.6 and last is not None:
        it, x1 = last
        px = cx + (it["x0"] + x1 - cx) * z
        py = cy + (it["y0"] - cy) * z
        dcur = ImageDraw.Draw(im, "RGBA")
        dcur.rectangle((round(px) + 4, round(py),
                        round(px) + 4 + max(2, round(14 * z)),
                        round(py) + round(it["img"].height / 2 * z)),
                       fill=(255, 255, 255, 230))


def _duotone(im, P, s):
    """Brand duotone over a photo: shadows into bg green, highlights
    into pale green; ``s`` 0 = untouched photo, 1 = full duotone."""
    import numpy as _np
    a = _np.asarray(im.convert("RGB"), dtype=float) / 255.0
    lum = a.mean(axis=2, keepdims=True)
    dark = _np.array(P["bg"][:3], dtype=float) / 255.0
    light = _np.array([233, 238, 215], dtype=float) / 255.0
    duo = dark * (1.0 - lum) + light * lum
    out = a * (1.0 - s) + duo * s
    return Image.fromarray((out * 255).astype("uint8"), "RGB")


def pill(im, boxes, s, x, y, col, anchor_pt, u, font_path, n=26):
    """Callout chip with a pulsing halo and leader line (v2 motion)."""
    z = asset(s, n, tuple(col), font_path)
    pulse = 0.5 + 0.5 * math.sin(u * 2.6)
    d = ImageDraw.Draw(im, "RGBA")
    halo = int(60 + 50 * pulse)
    d.rounded_rectangle((x - 18, y - 14, x + z.width + 18, y + z.height + 14), 14,
                        outline=col + (halo,), width=6)
    d.rounded_rectangle((x - 14, y - 10, x + z.width + 14, y + z.height + 10), 12,
                        fill=(14, 38, 24, 215), outline=col + (190,), width=2)
    d.line((anchor_pt[0], anchor_pt[1], x - 14, y + z.height / 2), fill=col + (235,), width=2)
    d.ellipse((anchor_pt[0] - 5, anchor_pt[1] - 5, anchor_pt[0] + 5, anchor_pt[1] + 5),
              fill=col + (255,))
    text_render(im, boxes, s, x, y, font_path, n, col)


def anchor_of(q, p):
    a = q.P(p)
    return (a[0] / 2 + 80, a[1] / 2 + 790)


MASK = Image.fromarray((np.clip(np.arange(750) / 35, 0, 1)[:, None]
                        * np.minimum(np.clip(np.arange(920) / 40, 0, 1),
                                     np.clip((920 - np.arange(920)) / 40, 0, 1))[None, :]
                        * 255).astype("uint8"))


def chart(im, boxes, u, font_path, P):
    c = (u - 49) / 10
    d = ImageDraw.Draw(im, "RGBA")
    x0, x1, yb, amp = 146, 902, 1440, 92
    d.rounded_rectangle((128, 1305, 920, 1490), 18, fill=(14, 38, 24, 205),
                        outline=(84, 133, 74, 230), width=2)
    for a, b, col in ((0, 0.45, P["cool"] + (34,)), (0.45, 0.75, P["amber"] + (46,)),
                      (0.75, 1, P["mint"] + (34,))):
        d.rectangle((x0 + (x1 - x0) * a, 1340, x0 + (x1 - x0) * b, yb + 4), fill=col)

    def fr(cc):
        return 0.82 * E(cc / 0.45) if cc < 0.45 else (
            0.82 * (1 - E((cc - 0.45) / 0.3)) if cc < 0.75 else 0.0)

    pts = [(x0 + (x1 - x0) * s, yb - amp * fr(s) / 0.82) for s in np.linspace(0, 1, 120)]
    # Draw-on sweep: the curve reveals left-to-right with the playhead (v2).
    shown = [pt for pt in pts if pt[0] <= x0 + (x1 - x0) * max(0.0, min(1.0, c))]
    if len(shown) > 1:
        d.line(shown, fill=P["mint"] + (255,), width=4, joint="curve")
    cx = x0 + (x1 - x0) * max(0.0, min(1.0, c))
    cy = yb - amp * fr(max(0.0, min(1.0, c))) / 0.82
    d.line((cx, 1342, cx, yb + 4), fill=(255, 255, 255, 200), width=2)
    d.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=(255, 255, 255, 255),
              outline=P["mint"] + (255,), width=3)
    text_render(im, boxes, "Stan szronu — schemat", 144, 1316, font_path, 20, P["muted"])
    for a, b, s in ((0, 0.45, "szron rośnie"), (0.45, 0.75, "odszranianie"),
                    (0.75, 1, "ogrzewanie wraca")):
        w = asset(s, 20, tuple(P["white"]), font_path).width
        text_render(im, boxes, s, x0 + (x1 - x0) * (a + b) / 2 - w, 1457, font_path, 20,
                    P["white"])


WINDOWS = [(65.75, 66.3, 0), (89.75, 90.3, 1)]


def _world_window(u, P, font_path, snow=1.0):
    if 66 <= u < 90:
        q = Canvas(P["bg"], *tile_cam(u))
        cur = 0.0
        for j in (1, 2, 3):
            cur += E((u - (66 + 6 * j - 0.6)) / 1.2)
        for i, (ox, oy) in enumerate(TILES):
            q.dim = float(np.clip(abs(cur - i) * 0.9, 0, 0.62))
            q.box((ox - 1.55, oy - 1.2, -0.14), (ox + 1.55, oy + 1.2, 0),
                  (224, 236, 226), (150, 176, 156), (238, 246, 240))
            q.box((ox - 1.5, oy - 1.15, -0.02), (ox + 1.5, oy + 1.15, 0.012),
                  (196, 216, 204), (150, 176, 156), (210, 226, 214))
            stt = tile_state(i, u, P)
            lod = 1.0 if q.dim < 0.2 else 0.5
            if i == 3:
                tile_house(q, ox, oy, P)
                # The unit reads oversized next to the schematic house:
                # draw it at 70% around its own centre, clear of the wall.
                q.push((ox + 0.19, oy + 0.08, 0.5), 0.7)
                pump(q, ox - 0.05, oy - 0.55, stt, u, P, lod)
                q.pop()
            else:
                pump(q, ox - 0.24, oy - 0.55, stt, u, P, lod)
            if i == 0:
                icicles(q, 0.96, u, P)
            if i == 1:
                ring(q, u, 0.9 * (1 if stt["heat"] > 0.05 else 0.45), ox, oy, 1.3, P)
            if i == 2:
                tile_warning(q, ox - 0.24, oy - 0.55, u, P)
            decal(q, TLAB[i], (ox - 1.3, oy + 0.88, 0.014), (1, 0, 0), (0, 1, 0),
                  0, 0, 0.2, (40, 86, 48) if q.dim < 0.3 else (110, 140, 112), font_path, 2.4)
            q.dim = 0.0
        st = dict(heat=0.0, plume=0.0)
        base = q.im.resize((920, 750), Image.Resampling.LANCZOS).convert("RGBA")
    else:
        seg = (0, 66) if u < 75 else (90, 110)
        ue = min(max(u, seg[0]), seg[1] - 1e-3)
        st = ustate(ue, P)
        q = Canvas(P["bg"], *world_cam(ue))
        snow_ground(q, P)
        house(q, P, True)
        pipes(q, P)
        ring(q, ue, st["ring"], UX + UW * 0.5, UY + UD * 0.5, 1.45, P)
        puddle(q, st["puddle"], ue, P)
        pump(q, UX, UY, st, ue, P)
        air_streams(q, ue, st["air"], P)
        drops(q, ue, st["drip"], UX + UW * 0.5, UY + 0.1, UY + UD - 0.1, P)
        if 90 <= ue < 100:
            obstacles(q, E((ue - 90.4) / 0.8), P)
        base = q.im.resize((920, 750), Image.Resampling.LANCZOS).convert("RGBA")
        base = Image.alpha_composite(base, glow_layer(q, st["heat"], P))
        if st["plume"] > 0.02:
            base = Image.alpha_composite(base, plume_layer(q, ue, st["plume"], P))
        u, st, q = ue, st, q
    # Two-depth snowfall for a 2.5D drift (v2).
    base = Image.alpha_composite(base, snow_layer(u, 0.55 * snow, parallax=0.55))
    base = Image.alpha_composite(base, snow_layer(u * 1.0 + 7.3, 0.8 * snow, parallax=1.25))
    base = Image.alpha_composite(base, vignette())
    return base.convert("RGB"), st


def _overlays(im, boxes, u, q_anchor_world, P, font_path):
    ue = u
    WHITE, MUTED, MINT, COOL, AMBER = P["white"], P["muted"], P["mint"], P["cool"], P["amber"]

    def anchor(p):
        a = q_anchor_world.P(p)
        return (a[0] / 2 + 80, a[1] / 2 + 790)

    if 7 <= ue < 15:
        pill(im, boxes, "Cykl odszraniania", 600, 1400, MINT,
             anchor((UX + UW * 0.5 + 1.1, UY + UD * 0.5 + 0.95, 0.0)), ue, font_path)
    if 15 <= ue < 27:
        pill(im, boxes, "Lamele wymiennika", 600, 1130, COOL,
             anchor((UX + UW * 0.5, UY + UD, 0.55)), ue, font_path)
        pill(im, boxes, "Zimne, wilgotne powietrze", 560, 1350, COOL,
             anchor((UX + UW * 0.5, UY + UD + 0.75, 0.4)), ue, font_path)
        text_render(im, boxes, "Najczęściej przy temperaturach w pobliżu zera i wilgotnym powietrzu.",
                    128, 715, font_path, 22, MUTED)
    if 29 <= ue < 39:
        pill(im, boxes, "Wymiennik jest ogrzewany", 560, 1100, AMBER,
             anchor((UX + UW * 0.5, UY + UD, 0.45)), ue, font_path)
    if 39 <= ue < 49:
        pill(im, boxes, "Biała para wodna", 640, 1010, WHITE,
             anchor((UX + UW, UY + UD * 0.48, 1.15)), ue, font_path)
        pill(im, boxes, "Woda spływa do odpływu", 560, 1390, COOL,
             anchor((UX + UW * 0.5, UY + UD * 0.5, 0.0)), ue, font_path)
        text_render(im, boxes, "Biała para szybko się rozprasza w otoczeniu.",
                    128, 715, font_path, 22, MUTED)
    if 49 <= ue < 59:
        chart(im, boxes, ue, font_path, P)
        text_render(im, boxes, "Przykład: producent podaje 5–15 min. To nie jest sztywny limit.",
                    128, 715, font_path, 22, MUTED)
    if 90 <= ue < 100:
        text_render(im, boxes, "Przeszkody przy jednostce utrudniają przepływ powietrza i odpływ wody.",
                    128, 715, font_path, 21, MUTED)
    if 66 <= ue < 90:
        text_render(im, boxes, "Schemat poglądowy, nie diagnoza konkretnej instalacji.",
                    128, 715, font_path, 22, MUTED)


# --- taktowanie film: mild-weather cycling story, own zones + cameras ---
#
# Zones (film seconds): 0-15 house wide, 15-30 outdoor unit close,
# 30-45 compressor macro (START/STOP), 45-60 boiler room, 60-75
# controller + cycle chart, 75-90 buffer + thermostat, 90-100 calm
# house, 100+ shared contact card. No snow, no tiles, no shadow blobs
# in rooms (owner rule); remote zones sit far apart so wide shots never
# collide.

TAKT_COMP = (6.0, 0.5)
TAKT_CTRL = (6.0, -3.08)
TAKT_BUF = (-0.5, 5.5)
TAKT_TH = (0.9, 5.3)


class _Shift:
    """Canvas proxy translating world coords by (ox, oy) and dropping
    contact shadows (rooms and film zones ground via feet and floors)."""

    def __init__(self, q, ox, oy):
        self._q = q
        self._ox = ox
        self._oy = oy

    def __getattr__(self, name):
        return getattr(self._q, name)

    def _t(self, p):
        x, y, z = p
        return (x + self._ox, y + self._oy, z)

    def _ts(self, ps):
        return [self._t(p) for p in ps]

    def box(self, a, b, *args, **kwargs):
        return self._q.box(self._t(a), self._t(b), *args, **kwargs)

    def poly(self, ps, *args, **kwargs):
        return self._q.poly(self._ts(ps), *args, **kwargs)

    def line(self, ps, *args, **kwargs):
        return self._q.line(self._ts(ps), *args, **kwargs)

    def fp(self, x, X, y, *args, **kwargs):
        return self._q.fp(x + self._ox, X + self._ox, y + self._oy,
                          *args, **kwargs)

    def dot(self, p, *args, **kwargs):
        return self._q.dot(self._t(p), *args, **kwargs)

    def disc_x(self, x, cy, cz, *args, **kwargs):
        return self._q.disc_x(x + self._ox, cy + self._oy, cz,
                              *args, **kwargs)

    def disc_y(self, cx, y, cz, *args, **kwargs):
        return self._q.disc_y(cx + self._ox, y + self._oy, cz,
                              *args, **kwargs)

    def ground_ellipse(self, cx, cy, *args, **kwargs):
        return self._q.ground_ellipse(cx + self._ox, cy + self._oy,
                                      *args, **kwargs)

    def contact_shadow(self, *args, **kwargs):
        return None

    def push(self, pivot, s):
        return self._q.push(self._t(pivot), s)


def cyc(u):
    """Compressor START (1.0) / POSTÓJ (0.0): ~8 s demonstration cycle."""
    if not 30 <= u < 45:
        return 0.0
    return 1.0 if (u - 30) % 8 < 5 else 0.0


def tstate(u, P):
    """Mild-weather animation state (no frost, no plume)."""
    if 15 <= u < 30:
        speed, angle = 0.35, fan_angle(u)
    else:
        speed, angle = 0.0, 0.6
    return dict(frost=0.0, heat=0.0, plume=0.0, drip=0.0, puddle=0.0,
                ring=0.0, air=0.0, speed=speed, angle=angle,
                led=P["mint"], cyc=cyc(u))


TZONES = [0, 15, 30, 45, 60, 75, 90, 100]

# Settled camera per zone start. Zones sit far apart, so the camera
# arrives with a quick 0.6 s swoop and then holds: no scene window
# (see scenariusz.md) ever spans a zone edge mid-shot.
TAKT_SLAB = (-6.0, -6.0, 9.0, 8.0)

# Settled cameras per zone: (start, end) — every zone carries its own
# slow move (push, pull or pan), hard cuts between zones (reels grammar).
# No scene window (see scenariusz.md) ever spans a zone edge mid-shot.
TKEYS = {
    0: (focus((-1.6, -2.0, 1.35), 100), focus((-1.6, -2.0, 1.35), 110)),
    15: (focus((0.11, -1.625, 0.5), 250), focus((0.11, -1.625, 0.5), 268)),
    30: (focus((TAKT_COMP[0], TAKT_COMP[1], 0.42), 430),
         focus((TAKT_COMP[0], TAKT_COMP[1], 0.42), 395)),
    45: (focus((6.0, 5.2, 1.28), 120), focus((6.2, 5.2, 1.28), 120)),
    60: (focus((TAKT_CTRL[0], TAKT_CTRL[1] + 0.1, 0.985), 230),
         focus((TAKT_CTRL[0], TAKT_CTRL[1] + 0.1, 1.0), 250)),
    75: (focus((0.1, 5.4, 0.8), 150), focus((-0.25, 5.4, 0.8), 150)),
    90: (focus((-1.6, -2.0, 1.35), 105), focus((-1.6, -2.0, 1.35), 95)),
}


def world_cam_takt(u, drift=True):
    u = min(max(u, 0.0), 100.0)
    for i, a in enumerate(TZONES[:-1]):
        b = TZONES[i + 1]
        if a <= u < b or (b == 100 and u >= 100):
            (k0, o0), (k1, o1) = TKEYS[a]
            e = E((min(u, b - 1e-6) - a) / (b - a))
            k = k0 + (k1 - k0) * e
            origin = (o0[0] + (o1[0] - o0[0]) * e,
                      o0[1] + (o1[1] - o0[1]) * e)
            if drift:
                ox = 5 * math.sin(u * 0.5) + 2 * math.sin(u * 1.13)
                oy = 4 * math.cos(u * 0.37) + 2 * math.sin(u * 0.91)
                origin = (origin[0] + ox, origin[1] + oy)
            return k, origin
    return TKEYS[90][1]


def chart_cycles(im, boxes, u, font_path, P):
    """On/off step chart of compressor cycles with draw-on sweep."""
    c = (u - 60) / 15
    d = ImageDraw.Draw(im, "RGBA")
    x0, x1, yb, amp = 146, 902, 1440, 92
    d.rounded_rectangle((128, 1305, 920, 1490), 18, fill=(14, 38, 24, 205),
                        outline=(84, 133, 74, 230), width=2)
    bands = ((0, 0.3, "PRACA", P["mint"] + (40,)),
             (0.3, 0.5, "POSTÓJ", P["cool"] + (44,)),
             (0.5, 0.8, "PRACA", P["mint"] + (40,)),
             (0.8, 1, "POSTÓJ", P["cool"] + (44,)))

    def val(s):
        for a, b, _n, _c in bands:
            if a <= s < b or (s >= 1 and b == 1):
                return 1.0 if _n == "PRACA" else 0.15
        return 0.15

    for a, b, _n, col in bands:
        d.rectangle((x0 + (x1 - x0) * a, 1340, x0 + (x1 - x0) * b, yb + 4),
                    fill=col)
    pts = [(x0 + (x1 - x0) * s, yb - amp * val(s))
           for s in np.linspace(0, 1, 160)]
    shown = [pt for pt in pts if pt[0] <= x0 + (x1 - x0) * max(0.0, min(1.0, c))]
    if len(shown) > 1:
        d.line(shown, fill=P["mint"] + (255,), width=4, joint="curve")
    cx = x0 + (x1 - x0) * max(0.0, min(1.0, c))
    cy = yb - amp * val(max(0.0, min(1.0, c)))
    d.line((cx, 1342, cx, yb + 4), fill=(255, 255, 255, 200), width=2)
    d.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=(255, 255, 255, 255),
              outline=P["mint"] + (255,), width=3)
    text_render(im, boxes, "Cykle sprężarki — schemat", 144, 1316, font_path,
                20, P["muted"])
    for a, b, s, _c in bands:
        w = asset(s, 20, tuple(P["white"]), font_path).width
        text_render(im, boxes, s, x0 + (x1 - x0) * (a + b) / 2 - w, 1457,
                    font_path, 20, P["white"])


def _resolve_prop(label):
    """Registry lookup for showcase scenes: ``'<module>.<prop>'``.

    Raises ValueError with the offending label — manifests fail fast
    instead of rendering a wrong prop.
    """
    import importlib as _il
    try:
        module_name, name = str(label).split(".", 1)
    except ValueError:
        raise ValueError(
            f"prop showcase needs '<module>.<prop>', got {label!r}")
    try:
        module = _il.import_module(f"reels_maker.iso.{module_name}")
    except ImportError:
        raise ValueError(f"unknown prop module in showcase: {label!r}")
    spec = getattr(module, "PROPS", {}).get(name)
    if spec is None:
        raise ValueError(f"unknown showcase prop: {label!r}")
    return spec


def _prop_window(label, u, P, camera=None, stage="plinth"):
    """One gallery prop (or an ensemble) as a film world.

    ``label`` is ``'<module>.<prop>'`` or a list whose first entry is
    the hero (owns plinth + focus) and the rest are
    ``{"label", "dx", "dy"}`` sidekicks painted after it. Same painters
    the gallery gate verifies, reframed for 920x750. ``camera`` takes
    move in push/pull/pan-left/pan-right/still, amount, and an optional
    turntable ``spin`` in radians; all eased over 8 s.
    """
    if isinstance(label, str):
        items = [{"label": label, "dx": 0.0, "dy": 0.0}]
    else:
        items = [{"label": (it if isinstance(it, str) else it["label"]),
                  "dx": 0.0 if isinstance(it, str) else float(it.get("dx", 0.0)),
                  "dy": 0.0 if isinstance(it, str) else float(it.get("dy", 0.0))}
                 for it in label]
        if not items:
            raise ValueError("prop showcase needs at least one prop")
    specs = [(item, _resolve_prop(item["label"])) for item in items]
    spec = specs[0][1]
    ue = min(max(u, 0.0), 100 - 1e-3)
    k, origin = focus(spec["focus"], spec["k"])
    cam = dict(camera or {})
    move = str(cam.get("move") or "push")
    amount = float(cam.get("amount", 0.06))
    spin = float(cam.get("spin", 0.0) or 0.0)
    if move not in ("push", "pull", "pan-left", "pan-right", "still"):
        raise ValueError(f"unknown showcase camera move: {move!r}")
    if not -0.6 <= spin <= 0.6:
        raise ValueError(f"showcase spin out of range: {spin!r}")
    t = E(min(ue / 8.0, 1.0))
    q = Canvas(P["bg"], k, origin, spin=spin * t)
    if move == "push":
        q.push(spec["focus"], 1.0 + amount * t)
    elif move == "pull":
        q.push(spec["focus"], 1.0 + amount * (1.0 - t))
    elif move in ("pan-left", "pan-right"):
        sign = -1.0 if move == "pan-left" else 1.0
        q.push(spec["focus"], 1.0)
        px, py, s = q._stack[-1]
        q._stack[-1] = (px + sign * 760.0 * amount * t, py, s)
    _mute_shadow.on = True
    try:
        if stage == "slab":
            q.boxg((-1.3, -1.0, -0.14), (1.3, 1.0, -0.005), (233, 238, 215))
        for item, sub in specs:
            sub["fn"](q, item["dx"], 0.15 + item["dy"], P)
    finally:
        _mute_shadow.on = False
    return (q.im.resize((920, 750), Image.Resampling.LANCZOS).convert("RGB"),
            q)


def _world_window_taktowanie(u, P, font_path, snow=1.0):
    ue = min(max(u, 0.0), 100 - 1e-3)
    st = tstate(ue, P)
    # Shadowless film: the thread-local mute flag drops every builder
    # shadow while this zone paints; feet and floors ground each device.
    # Other threads (other films) are unaffected: no lock, no race.
    q = Canvas(P["bg"], *world_cam_takt(ue))
    _mute_shadow.on = True
    try:
        # One full-bleed ground slab under everything: infinite-lawn read,
        # zero ellipse edges, zero blobs. Painted first, devices overdraw.
        x0, y0, x1, y1 = TAKT_SLAB
        q.box((x0, y0, -0.15), (x1, y1, 0.0),
              (128, 164, 116), (110, 148, 100), (141, 179, 129))
        gx = x0
        while gx <= x1:
            q.line([(gx, y0, 0.002), (gx, y1, 0.002)], (126, 162, 114), 0.8)
            gx += 1.5
        gy = y0
        while gy <= y1:
            q.line([(x0, gy, 0.002), (x1, gy, 0.002)], (126, 162, 114), 0.8)
            gy += 1.5
        if ue < 30 or ue >= 90:
            house(q, P, True)
            pipes(q, P)
            pump(q, UX, UY, st, ue, P)
        elif ue < 45:
            compressor(q, TAKT_COMP[0], TAKT_COMP[1], P)
            ring(q, ue, 0.9 * st["cyc"], TAKT_COMP[0], TAKT_COMP[1], 0.55, P)
        elif ue < 60:
            boiler_room(_Shift(q, 6.0, 5.0), P)
        elif ue < 75:
            q.box((TAKT_CTRL[0] - 0.6, TAKT_CTRL[1] - 0.07, 0.0),
                  (TAKT_CTRL[0] + 0.6, TAKT_CTRL[1] + 0.03, 1.75),
                  (226, 232, 218), (200, 210, 194), (238, 242, 232))
            controller(q, TAKT_CTRL[0], TAKT_CTRL[1], P)
        else:
            buffer_tank(q, TAKT_BUF[0], TAKT_BUF[1], P)
            thermostat(q, TAKT_TH[0], TAKT_TH[1], P)
    finally:
        _mute_shadow.on = False
    base = q.im.resize((920, 750), Image.Resampling.LANCZOS).convert("RGBA")
    base = Image.alpha_composite(base, snow_layer(ue, 0.55 * snow, parallax=0.55))
    base = Image.alpha_composite(base, snow_layer(ue * 1.0 + 7.3, 0.8 * snow, parallax=1.25))
    base = Image.alpha_composite(base, vignette())
    return base.convert("RGB"), st


def _overlays_taktowanie(im, boxes, u, q_anchor_world, P, font_path):
    ue = u
    WHITE, MUTED, MINT, COOL, AMBER = (P["white"], P["muted"], P["mint"],
                                       P["cool"], P["amber"])

    def anchor(p):
        a = q_anchor_world.P(p)
        return (a[0] / 2 + 80, a[1] / 2 + 790)

    if 15 <= ue < 30:
        pill(im, boxes, "Jednostka zewnętrzna", 600, 1130, COOL,
             anchor((UX + UW * 0.5, UY + UD, 1.0)), ue, font_path)
    if 30 <= ue < 45:
        on = cyc(ue) > 0.5
        pill(im, boxes, "Sprężarka: START" if on else "Sprężarka: POSTÓJ",
             560, 1130, MINT if on else COOL,
             anchor((TAKT_COMP[0], TAKT_COMP[1], 0.75)), ue, font_path)
    if 45 <= ue < 60:
        pill(im, boxes, "Kotłownia", 600, 1130, MINT,
             anchor((5.2, 4.65, 1.65)), ue, font_path)
        text_render(im, boxes, "Bufor, naczynie, pompa obiegowa i sterownik.",
                    128, 715, font_path, 22, MUTED)
    if 60 <= ue < 75:
        chart_cycles(im, boxes, ue, font_path, P)
        pill(im, boxes, "Sterownik", 600, 1130, MINT,
             anchor((TAKT_CTRL[0], TAKT_CTRL[1], 1.6)), ue, font_path)
        text_render(im, boxes, "Starty, godziny pracy, wykres.",
                    128, 715, font_path, 22, MUTED)
    if 75 <= ue < 90:
        pill(im, boxes, "Bufor", 560, 1100, MINT,
             anchor((TAKT_BUF[0], TAKT_BUF[1], 1.6)), ue, font_path)
        pill(im, boxes, "Termostat", 600, 1350, COOL,
             anchor((TAKT_TH[0], TAKT_TH[1], 0.95)), ue, font_path)
        text_render(im, boxes, "Strefy i zład decydują o cyklach.",
                    128, 715, font_path, 22, MUTED)
    if 90 <= ue < 100:
        text_render(im, boxes, "Długie cykle, mało startów — tak ma pracować.",
                    128, 715, font_path, 22, MUTED)


TAKT_CARD = [
    (100, "Spokojna praca pompy.",
     ["Obserwuj cykle sprężarki w aplikacji,",
      "a w razie wątpliwości skonsultuj się",
      "z certyfikowanym serwisem ASTA Energy."]),
]


def _contact_card(u, P, font_path, logo, logo_path, snow=1.0,
                film="odszranianie", copy_override=None):
    """Ceremonial closing card (u >= 100): centered stack, watermark, no clutter."""
    from PIL import Image as _I

    im = Image.new("RGB", (W, H), P["bg"])
    boxes: list = []
    try:
        mark = _I.open(logo_path).convert("RGBA") if logo_path else None
    except Exception:
        mark = None
    if mark is not None:
        mark = mark.resize((1400, max(1, round(1400 * mark.height / mark.width))),
                           _I.Resampling.LANCZOS)
        mark.putalpha(mark.getchannel("A").point(lambda v: round(v * 0.10)))
        im.paste(mark, (round((W - mark.width) / 2), 1380), mark)
    layer = Image.alpha_composite(
        _I.new("RGBA", (920, 750), (0, 0, 0, 0)),
        snow_layer(u, 0.30 * snow, parallax=0.55))
    im.paste(layer.convert("RGB"), (80, 790), layer.getchannel("A"))
    full_vignette = vignette().resize((W, H), _I.Resampling.BILINEAR)
    im = Image.alpha_composite(im.convert("RGBA"), full_vignette).convert("RGB")
    if logo is not None:
        im.paste(logo, (128, 224), logo)
    if copy_override and (copy_override.get("title")
                         or copy_override.get("body")):
        beats = [(100.0, str(copy_override.get("title", "")),
                  [str(line) for line in
                   (copy_override.get("body") or [])])]
    else:
        beats = TAKT_CARD if film == "taktowanie" else COPY_BEATS
    idx = max(i for i, z in enumerate(beats) if u >= z[0])
    at, title, body = beats[idx]
    body = [str(s.get("text", "")) if isinstance(s, dict) else str(s)
            for s in body]
    DK = (23, 61, 36)
    light = film == "prop" and bool(title or any(body))
    d = ImageDraw.Draw(im, "RGBA")
    if light:
        # House light card (refs): white rounded box, caps header,
        # huge dark-green number, small mail line underneath.
        n_rest = max(0, len(body) - 1)
        y1 = 1000 + 26 * n_rest
        d.rounded_rectangle((118, 640, 962, y1), 28,
                            fill=(243, 245, 240, 255))
    a = E((u - at) / 0.26)
    if light:
        ahead_w = asset(title.upper(), 30, DK, font_path, True).width
        text_render(im, boxes, title.upper(), round((W - ahead_w) / 2),
                    690, font_path, 30, MAIN_GREEN, a, bold=True)
        if body:
            num_w = asset(body[0], 84, DK, font_path, True).width
            text_render(im, boxes, body[0], round((W - num_w) / 2),
                        791, font_path, 84, DK, a, bold=True)
        for j, s in enumerate(body[1:]):
            ns = 30 if j < 2 else 22
            sw = asset(s, ns, DK, font_path).width
            aj = E((u - at - 0.1 * (j + 1) - 0.12) / 0.3)
            text_render(im, boxes, s, round((W - sw) / 2),
                        920 + 40 * j, font_path, ns, DK, aj)
    else:
        text_render(im, boxes, title, 128, 340, font_path, 52, P["white"], a, 12 * (1 - a))
        for j, s in enumerate(body):
            aj = E((u - at - 0.1 * j - 0.12) / 0.3)
            text_render(im, boxes, s, 128, 440 + 46 * j, font_path, 32, P["white"], aj,
                        10 * (1 - aj))

    def centered(s, y, n, col, alpha):
        w = asset(s, n, tuple(col), font_path).width
        text_render(im, boxes, s, round((W - w) / 2), y, font_path, n, col, alpha)

    al = E((u - 100.2) / 0.5)
    if al > 0.003 and film == "taktowanie":
        # Minimalist end card: title, beats, phone, mail. Nothing else.
        centered("67 350 90 90", 880, 84, P["white"], al)
        centered("kontakt@asta-energy.pl", 1000, 30, P["white"], al)
    if al > 0.003 and film not in ("taktowanie", "prop"):
        d.line((128, 620, 420, 620), fill=(71, 160, 19, 255), width=5)
        d.rounded_rectangle((96, 680, 984, 1150), 24, fill=(14, 38, 24, int(228 * al)),
                            outline=P["mint"] + (int(170 * al),), width=3)
        centered("Masz wątpliwości? Zapytaj instalatora", 724, 30, P["white"], al)
        centered("lub certyfikowanego doradcę ASTA Energy.", 768, 30, P["white"], al)
        centered("67 350 90 90", 820, 84, P["white"], al)
        centered("kontakt@asta-energy.pl", 946, 30, P["white"], al)
        centered("Pn–pt 8:00–16:00 · serwis i doradztwo techniczne", 996, 24, P["muted"], al)
        centered("Ilustracja poglądowa. Szczegóły zależą od modelu — sprawdź instrukcję urządzenia.",
                 1064, 19, P["white"], al)
    text_render(im, boxes, "ASTA Energy · autoryzowany serwis i doradztwo",
                128, 1830, font_path, 20, P["muted"], 1.0)
    return im, boxes, u


def _photo_bg(photo_path, P):
    """Real photo as a full-bleed backdrop, muted toward the brand bg so
    the shared copy layout keeps its contrast. None when unavailable."""
    from PIL import Image as _I
    from PIL import ImageOps as _Ops
    if isinstance(photo_path, (list, tuple)):
        photo_path = photo_path[0] if photo_path else None
    try:
        im = _I.open(photo_path).convert("RGB")
    except Exception:
        return None
    im = _Ops.fit(im, (W, H), _I.Resampling.LANCZOS)
    return Image.blend(im, Image.new("RGB", (W, H), P["bg"]), 0.45)


def _full_frame(u, P, font_path, logo, logo_path, snow=1.0,
                film="odszranianie", photo_path=None, prop=None,
                copy=None, camera=None, zoom=None, stage="plinth",
                labels=None, scene_time=None, gfx_cy=None):
    """Full 1080x1920 frame (copy + world) at clamped film time ``u``."""
    if u >= 100:
        return _contact_card(u, P, font_path, logo, logo_path, snow,
                             film, copy)
    if film == "prop":
        # Showcase: one gallery prop (or a photo hook) as the world;
        # the manifest copy layout below stays byte-identical, no
        # topic overlays. Photos breathe (duotone ramps in, Ken Burns
        # drift); props push in and settle back over 8 s.
        ue = min(max(u, 0.0), 100 - 1e-3)
        im = Image.new("RGB", (W, H), P["bg"])
        boxes: list = []
        photo = _photo_bg(photo_path, P) if photo_path else None
        if photo is None:
            win, _q = _prop_window(prop, ue, P, camera, stage)
            im.paste(win, (80, 790), MASK)
            d = ImageDraw.Draw(im)
            for lb in (labels or []):
                at = lb.get("at") if isinstance(lb, dict) else None
                if (not isinstance(at, (list, tuple)) or len(at) != 3
                        or not all(isinstance(v, (int, float))
                                   for v in at)):
                    raise ValueError(f"bad label anchor: {lb!r}")
                ax, ay = _q.P(tuple(at))
                ax, ay = ax / 2 + 80, ay / 2 + 790
                tx, ty = int(ax + 26), int(ay - 64)
                d.line([ax, ay, tx + 6, ty + 12],
                       fill=(248, 249, 240, 230), width=2)
                text_render(im, boxes, str(lb.get("text", "")),
                            tx, ty, font_path, 22, P["white"], 1.0)
        else:
            zspec = dict(zoom or {})
            zamount = float(zspec.get("amount", 0.09))
            ztime = float(zspec.get("time", 8.0))
            zdirect = str(zspec.get("dir", "in"))
            if zdirect not in ("in", "out"):
                raise ValueError(
                    f"photo zoom dir must be in/out, got {zdirect!r}")
            fx, fy = zspec.get("focus", (0.5, 0.45))
            fx, fy = min(max(float(fx), 0.0), 1.0), min(max(float(fy), 0.0), 1.0)
            drift = zspec.get("pan", (0.0, 0.0))
            dx, dy = float(drift[0]), float(drift[1])
            te = E(min(ue / max(ztime, 0.1), 1.0))
            s = E(min(ue / 1.2, 1.0))
            if zspec.get("frame") == "lines" and photo_path:
                from PIL import Image as _I3
                _raw0 = _I3.open(photo_path)
                if "A" in _raw0.getbands():
                    _raw0 = _I3.alpha_composite(
                        _I3.new("RGBA", _raw0.size, (0, 0, 0, 255)),
                        _raw0.convert("RGBA"))
                raw = _raw0.convert("L")
                zt = float(zspec.get("time", 6.0))
                te = E(min(ue / max(zt, 0.1), 1.0))
                drift = zspec.get("pan", (0.0, 0.0))
                try:
                    dx = float(drift[0])
                except Exception:
                    dx = 0.0
                sc = 0.97 + 0.03 * E(min(ue / 1.2, 1.0))
                punch = 1.15 - 0.15 * E(min(max(ue, 0.0) / 0.8, 1.0))
                w = max(1, round(raw.width * sc * punch * 1.2))
                h = max(1, round(raw.height * sc * punch * 1.2))
                g = raw.resize((w, h), Image.Resampling.LANCZOS)
                import numpy as _np2
                mean_lum = float(_np2.asarray(g).mean())
                if mean_lum < 128:
                    alpha = g
                else:
                    # Outline-only extraction: near-black contours become
                    # solid white lines, fills and shading fall away.
                    alpha = g.point(
                        lambda v: max(0, min(255, round((110 - v) * 255 / 110))))
                layer = _I3.new("RGBA", (w, h), (255, 255, 255, 0))
                layer.paste((255, 255, 255, 255), (0, 0, w, h), alpha)
                xoff = round(160 * dx * (te - 0.5))
                _gcy = gfx_cy if gfx_cy is not None else 980.0
                im.paste(layer, (round((W - w) / 2) + xoff,
                                 round(_gcy - h / 2)), layer)
                if logo is not None:
                    im.paste(logo, (128, 224), logo)
                return im, boxes, ue
            if zspec.get("frame") == "fit" and photo_path:
                # Bottom-half full-bleed real photo(s), NO duotone, lightly
                # sharpened after the upscale; copy lives in the top half.
                # A list cycles photos every 2 s (realizations montage).
                from PIL import Image as _I2
                from PIL import ImageOps as _Ops2
                if isinstance(photo_path, (list, tuple)) and photo_path:
                    _lt = scene_time if scene_time is not None else ue
                    photo_path = photo_path[int(_lt / 1.0) % len(photo_path)]
                raw = _I2.open(photo_path).convert("RGB")
                punch = 1.12 - 0.12 * E(min(max(ue, 0.0) / 0.8, 1.0))
                zw, zh = max(1, round(W * punch)), max(1, round(960 * punch))
                big = _Ops2.fit(raw, (zw, zh), Image.Resampling.LANCZOS)
                big = big.filter(ImageFilter.UnsharpMask(radius=2, percent=70,
                                                         threshold=2))
                cx0, cy0 = (zw - W) / 2, (zh - 960) / 2
                shot = big.crop((round(cx0), round(cy0),
                                 round(cx0) + W, round(cy0) + 960))
                import numpy as _np3
                fade = (_np3.linspace(0, 1, 120) * 255).astype("uint8")
                mask = Image.new("L", (W, 960), 255)
                mask.paste(Image.fromarray(fade).resize((W, 120)), (0, 0))
                im.paste(shot, (0, 960), mask)
                if logo is not None:
                    im.paste(logo, (128, 224), logo)
                return im, boxes, ue
            photo = _duotone(photo, P, 0.55 * s)
            if zdirect == "in":
                z = 1.0 + zamount * te
            else:
                z = 1.0 + zamount * (1.0 - te)
            big = photo.resize((round(W * z), round(H * z)),
                               Image.Resampling.LANCZOS)
            cx = int(big.width * min(max(fx + dx * te, 0.0), 1.0))
            cy = int(big.height * min(max(fy + dy * te, 0.0), 1.0))
            ox = min(max(cx - W // 2, 0), big.width - W)
            oy = min(max(cy - H // 2, 0), big.height - H)
            frame = big.crop((ox, oy, ox + W, oy + H))
            im.paste(frame, (0, 0))
        if logo is not None:
            im.paste(logo, (128, 224), logo)
        return im, boxes, ue
    if film == "taktowanie":
        # Own world, cameras and overlays; shared tail below stays
        # byte-identical for the odszranianie path.
        ue = min(max(u, 0.0), 100 - 1e-3)
        im = Image.new("RGB", (W, H), P["bg"])
        boxes: list = []
        photo = _photo_bg(photo_path, P) if photo_path else None
        if photo is None:
            win, _st = _world_window_taktowanie(ue, P, font_path, snow)
            im.paste(win, (80, 790), MASK)
            q = Canvas(P["bg"], *world_cam_takt(ue))
            _overlays_taktowanie(im, boxes, ue, q, P, font_path)
        else:
            # Photo hook/evidence: identical copy layout, no world, no
            # pills — the photo carries the scene alone.
            im.paste(photo, (0, 0))
        if logo is not None:
            im.paste(logo, (128, 224), logo)
        return im, boxes, ue
    if 66 <= u < 90:
        ue = min(max(u, 66), 90 - 1e-3)
    else:
        ue = u
    win, _st = _world_window(ue, P, font_path, snow)
    im = Image.new("RGB", (W, H), P["bg"])
    im.paste(win, (80, 790), MASK)
    boxes: list = []
    # Anchor world for leader lines: same deterministic camera as the window.
    if not (66 <= ue < 90):
        q = Canvas(P["bg"], *world_cam(ue))
    else:
        q = Canvas(P["bg"], *tile_cam(ue))
    _overlays(im, boxes, ue, q, P, font_path)
    if logo is not None:
        im.paste(logo, (128, 224), logo)
    return im, boxes, ue


def frame_at(tv, P, font_path, logo, logo_path=None, snow=1.0,
             film="odszranianie", copy_override=None, scene_time=0.0,
             photo_path=None, prop=None, camera=None, zoom=None,
             title_size=None, stage="plinth", labels=None):
    """Full 1080x1920 frame at film time ``tv`` (seconds, includes OFFSET lead).

    ``film`` selects the topic world; ``copy_override`` (``{"title", "body"}``)
    replaces the beat copy with manifest-driven text so every clip carries
    its own words over shared visuals. Entrances then follow scene-local
    ``scene_time`` instead of the beat clock.
    """
    u = max(0, tv - OFFSET)
    # Vertically centered statement block: copy sits on the optical
    # center, the graphic hangs under it (manifest copy only).
    _co = copy_override or {}
    _tt = str(_co.get("title", "")) if isinstance(_co, dict) else ""
    _bd = list(_co.get("body", []) or []) if isinstance(_co, dict) else []
    _tz = title_size or TITLE_SIZE
    _ts = TITLE_LINE_STEP * _tz / TITLE_SIZE
    _ln0 = wrap_title(_tt, font_path, _tz, bold=True) if _tt else [""]
    from PIL import ImageFont as _FF
    _bkey = tuple((str(s.get("text", "")) if isinstance(s, dict) else str(s),
                   str(s.get("from", "")) if isinstance(s, dict) else "")
                  for s in _bd)
    _bsize, _bstep = _body_fit(_bkey, font_path)
    try:
        _rf = _FF.truetype(font_path or resolve_font(), _bsize * 2)
    except Exception:
        _rf = _FF.load_default()
    _nbd = len(wrap_body_lines([t for t, _s in _bkey], _rf)) if _bd else 0
    _bh = _ts * (len(_ln0) - 1) + _tz + 24 + max(_nbd - 1, 0) * _bstep + _bsize
    _vy0 = 620 - _bh / 2
    _vby0 = _vy0 + _ts * (len(_ln0) - 1) + _tz + 24
    _vgy = _vby0 + max(_nbd - 1, 0) * _bstep + _bsize + 200 + 230
    if _tt and _vgy + 230 > 1880:
        _sh = (_vgy + 230) - 1880
        _vy0 -= _sh
        _vby0 -= _sh
        _vgy -= _sh
    # Tile-strip dissolves exist only in the odszranianie film.
    windows = WINDOWS if film == "odszranianie" else []
    for a, b, _i in windows:
        if a <= u < b:
            x = E((u - a) / (b - a))
            A, _, _ = _full_frame(a, P, font_path, logo, logo_path, snow,
                                  film, prop=prop, copy=copy_override,
                                  camera=camera, zoom=zoom, stage=stage,
                                  labels=labels)
            B, _, _ = _full_frame(b, P, font_path, logo, logo_path, snow,
                                  film, prop=prop, copy=copy_override,
                                  camera=camera, zoom=zoom, stage=stage,
                                  labels=labels)
            # Eased cross-dissolve between the tile strip and the world view.
            im = Image.blend(A, B, x)
            boxes: list = []
            break
    else:
        im, boxes, u = _full_frame(u, P, font_path, logo, logo_path, snow,
                                   film, photo_path, prop, copy_override,
                                   camera, zoom, stage, labels,
                                   scene_time=scene_time, gfx_cy=_vgy)

    if u < 100:
        # The closing card (u >= 100) carries its own copy layout.
        if copy_override is not None:
            title = str(copy_override.get("title", ""))
            body = list(copy_override.get("body") or [])
            a = E(scene_time / 0.26)
            _y0, _by0 = _vy0, _vby0
            beats = [E((scene_time - 0.1 * j - 0.12) / 0.3)
                     for j in range(len(body))]
        else:
            idx = max(i for i, z in enumerate(COPY_BEATS) if u >= z[0])
            at, title, body = COPY_BEATS[idx]
            a = (1 if idx == 0 and u < 0.5 else E((u - at) / 0.26)
                 if idx else 1)
            # Beat zero carries full content from frame zero: no entrance.
            beats = ([1] * len(body) if idx == 0 else
                     [E((u - at - 0.1 * j - 0.12) / 0.3)
                      for j in range(len(body))])
        tsize = title_size or TITLE_SIZE
        tstep = TITLE_LINE_STEP * tsize / TITLE_SIZE
        lines = wrap_title(title, font_path, tsize, bold=True)
        shift = tstep * (len(lines) - 1)
        if copy_override is not None:
            # Typewriter: words pop one by one (clicks ride in the
            # manifest SFX), the headline punches in, then the full
            # scene settles. Schedule shared with the SFX generator:
            # title 0.15+i*0.22, body after +0.35 step 0.13.
            t = scene_time
            key = tuple((str(s.get("text", "")), str(s.get("from", "")))
                        if isinstance(s, dict) else (str(s), "")
                        for s in body)
            lay = _typed_layout(title, key, tsize, font_path, _y0, _by0)
            boxes.append((title, (128, round(_y0), 128 + TITLE_MAX_WIDTH,
                                  round(_y0) + shift + tsize)))
            _vj = 0
            for _txt, _side in key:
                for _vt in wrap_body_lines([_txt], _rf):
                    boxes.append((_vt, (128, round(_by0 + _bstep * _vj),
                                        128 + TITLE_MAX_WIDTH,
                                        round(_by0 + _bstep * _vj) + _bsize)))
                    _vj += 1
            _paste_typed_layer(im, lay, t, a)
        else:
            for k, line in enumerate(lines):
                text_render(im, boxes, line, 128, 340 + tstep * k,
                            font_path, tsize, P["white"], a,
                            12 * (1 - a), -36 * (1 - a), bold=True)
            for j, s in enumerate(body):
                txt = str(s)
                aj = beats[j] if j < len(beats) else 1
                slide = -26 * (1 - aj) if j % 2 == 0 else 26 * (1 - aj)
                text_render(im, boxes, txt, 128, 440 + shift + 46 * j,
                            font_path, 32, P["white"], aj, 10 * (1 - aj),
                            slide)

    # No fade-in: the opening beat carries full content from frame zero.
    f = 1.0
    if u > FILM_DURATION - OFFSET - 0.7:
        f = min(f, E((FILM_DURATION - OFFSET - u) / 0.7))
    out = Image.blend(Image.new("RGB", (W, H), P["bg"]), im, f) if f < 1 else im
    return out, boxes


@functools.lru_cache(maxsize=4)
def _logo(path, width):
    from PIL import Image as _I

    im = _I.open(path).convert("RGBA")
    r = width / im.width
    return im.resize((width, max(1, round(im.height * r))), _I.Resampling.LANCZOS)


def render_iso_frame(spec, width, height, time):
    """Entry point used by the Studio renderer for ``iso-world`` nodes."""
    spec = dict(spec or {})
    pal = dict(DEFAULT_PALETTE)
    pal.update(spec.get("palette") or {})
    font_path = spec.get("font") or resolve_font()
    logo = None
    logo_path = str(spec["logo"]) if spec.get("logo") else None
    if logo_path:
        try:
            logo = _logo(logo_path, 330)
        except Exception:
            logo = None
            logo_path = None
    film_t = float(spec.get("t0", 0.0)) + float(time)
    override = spec.get("copy")
    def _line(line):
        if isinstance(line, dict):
            return {"text": str(line.get("text", "")),
                    "from": str(line.get("from", ""))}
        return str(line)
    override = ({"title": str(override.get("title", "")),
                 "body": [_line(line) for line in
                          (override.get("body") or [])]}
                if isinstance(override, dict) else None)
    _ph = spec.get("photo")
    photo_path = list(_ph) if isinstance(_ph, (list, tuple)) else (str(_ph) if _ph else None)
    prop = spec.get("prop")
    if isinstance(prop, str):
        prop = prop or None
    tsize = spec.get("title_size")
    tsize = int(tsize) if tsize else None
    stage = str(spec.get("stage") or "plinth")
    labels = spec.get("labels")
    im, _boxes = frame_at(film_t + OFFSET, pal, font_path, logo, logo_path,
                          snow=float(spec.get("snow", 1.0)),
                          film=str(spec.get("film") or "odszranianie"),
                          copy_override=override, scene_time=float(time),
                          photo_path=photo_path, prop=prop,
                          camera=spec.get("camera"), zoom=spec.get("zoom"),
                          title_size=tsize, stage=stage, labels=labels)
    if (im.width, im.height) != (width, height):
        im = im.resize((width, height), Image.Resampling.LANCZOS)
    return im.convert("RGB")
