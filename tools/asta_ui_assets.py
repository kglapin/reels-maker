#!/usr/bin/env python3
"""Generate the ASTA Energy click-through UI assets (bill, button, cursor).

Outputs PNG overlays consumed by Studio ``overlays`` scenes. Brand rules:
primary green #47A013, Open Sans (DejaVu Sans fallback), restrained flat
editorial style — no gradients on the brand color, soft shadow only.

Usage: .venv/bin/python tools/asta_ui_assets.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "brands" / "asta-energy" / "assets" / "ui"

GREEN = (71, 160, 19)
GREEN_LIGHT = (92, 184, 31)
GREEN_DARK = (46, 110, 9)
INK = (26, 34, 28)
MUTED = (104, 116, 106)
FAINT = (160, 170, 160)
PAPER = (253, 253, 250)
LINE = (222, 228, 218)
ALARM = (198, 52, 36)
ALARM_DEEP = (150, 34, 24)

FONT_CANDIDATES = {
    "regular": [
        str(Path.home() / "Library/Fonts/OpenSans-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/OpenSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "bold": [
        str(Path.home() / "Library/Fonts/OpenSans-Bold.ttf"),
        "/System/Library/Fonts/Supplemental/OpenSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "extrabold": [
        str(Path.home() / "Library/Fonts/OpenSans-ExtraBold.ttf"),
        str(Path.home() / "Library/Fonts/OpenSans-Bold.ttf"),
        "/System/Library/Fonts/Supplemental/OpenSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
}


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    for candidate in FONT_CANDIDATES[weight]:
        path = Path(candidate)
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    raise SystemExit(f"No usable {weight} font found")


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def vgrad(size: tuple[int, int], top, bottom) -> Image.Image:
    """Vertical two-stop gradient as RGBA."""
    w, h = size
    grad = Image.new("RGB", (1, h))
    px = grad.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = tuple(int(round(lerp(top[i], bottom[i], t)))
                         for i in range(3))
    return grad.resize((w, h)).convert("RGBA")


def soft_shadow(size: tuple[int, int], radius: int, offset: int = 14,
                opacity: int = 110, blur: int = 26) -> Image.Image:
    shadow = Image.new("L", size, 0)
    draw = ImageDraw.Draw(shadow)
    draw.rounded_rectangle(
        [radius, radius + offset, size[0] - radius, size[1] - radius + offset],
        radius=radius, fill=opacity)
    return shadow.filter(ImageFilter.GaussianBlur(blur))


def paste_shadow(canvas: Image.Image, size: tuple[int, int], radius: int,
                 offset: int = 14, opacity: int = 110, blur: int = 26,
                 at=(0, 0)) -> None:
    shadow = soft_shadow(size, radius, offset, opacity, blur)
    canvas.alpha_composite(
        Image.merge("RGBA", (shadow, shadow, shadow,
                             shadow.point(lambda v: v))), at)


def make_bill() -> None:
    """Simplified utility bill: a tall sheet of paper with a real title
    ("Rachunek za prąd"), abstract placeholder rows and a large empty
    amount zone reserved for the animated counter overlay."""
    w, h = 1450, 1500
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    # Restrained alarm glow: soft radial bloom behind the paper.
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = w // 2, int(h * 0.44)
    for i in range(7):
        r = 230 + i * 66
        a = int(30 - i * 4)
        gd.ellipse([cx - r, cy - int(r * 0.82), cx + r, cy + int(r * 0.82)],
                   outline=(*ALARM, max(a, 0)), width=26)
    glow = glow.filter(ImageFilter.GaussianBlur(70))
    canvas.alpha_composite(glow)

    pw, ph = 1150, 1120

    # Paper with drop shadow, then the whole card tilted for editorial feel.
    card = Image.new("RGBA", (pw + 120, ph + 120), (0, 0, 0, 0))
    paste_shadow(card, (pw + 120, ph + 120), 30, offset=14, opacity=120,
                 blur=26, at=(0, 0))

    paper = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    pd = ImageDraw.Draw(paper)
    # Brighter, cleaner sheet — reads as paper, not a UI card.
    pd.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=14,
                         fill=(252, 252, 249, 255), outline=(228, 232, 224, 255),
                         width=2)

    m = 84
    bar = (214, 220, 210, 255)
    bar_soft = (228, 233, 224, 255)

    # The only real copy on the document: its title.
    pd.text((m, 84), "Rachunek za prąd", font=font("extrabold", 62),
            fill=INK)
    pd.rounded_rectangle([m, 182, m + 260, 200], radius=9, fill=bar_soft)
    pd.rounded_rectangle([pw - m - 220, 182, pw - m, 200], radius=9,
                         fill=bar_soft)
    pd.line([(m, 236), (pw - m, 236)], fill=(214, 220, 212, 255), width=2)

    # Line-item placeholders spread over the taller sheet.
    rows_y = [300, 396, 492, 588, 684]
    for ry in rows_y:
        pd.rounded_rectangle([m + 8, ry, m + 360 + (ry % 3) * 36, ry + 28],
                             radius=9, fill=bar_soft)
        pd.rounded_rectangle([pw - m - 220, ry, pw - m - 24, ry + 28],
                             radius=9, fill=bar_soft)

    pd.line([(m, 780), (pw - m, 780)], fill=(214, 220, 212, 255), width=2)
    # "Do zapłaty" caption; the large empty zone below stays blank — the
    # animated counter overlay draws the rising sum on the paper.
    pd.rounded_rectangle([m + 8, 816, m + 250, 848], radius=9, fill=bar)

    # Footer strip: due-date bar + abstract barcode squares.
    fy = ph - 78
    pd.line([(m, fy), (pw - m, fy)], fill=(214, 220, 212, 255), width=2)
    pd.rounded_rectangle([m, fy + 24, m + 300, fy + 50], radius=8,
                         fill=bar_soft)
    import random as _r
    rng = _r.Random(7)
    x = pw - m - 320
    while x < pw - m - 20:
        bw = rng.choice((3, 5, 8))
        if rng.random() > 0.35:
            pd.rectangle([x, fy + 14, x + bw, fy + 54],
                         fill=(60, 66, 58, 255))
        x += bw + rng.choice((3, 5, 8))

    card.alpha_composite(paper, (60, 60))

    # Tilt the whole card ~ -2.4 degrees for an editorial, unstaged feel.
    angle = -2.4
    rotated = card.rotate(angle, resample=Image.Resampling.BICUBIC,
                           expand=True)
    canvas.alpha_composite(rotated,
                           ((w - rotated.width) // 2,
                            (h - rotated.height) // 2))
    canvas.save(OUT / "bill.png")


# Site tokens (wp-content/themes/asta-blocks): action surface #367E18,
# hover #356A29, radius 12px (~22% of control height), weight 600.
ACTION = (54, 126, 24)
ACTION_HOVER = (53, 106, 41)
ACTION_TEXT = (255, 255, 255)


def _button_pill(hover: bool) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    w, h = 1160, 340
    radius = int(h * 0.22)
    base = ACTION_HOVER if hover else ACTION
    pill = Image.new("RGBA", (w, h), (*base, 255))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, w - 1, h - 1], radius=radius, fill=255)
    pill.putalpha(mask)
    # Faint top sheen only — the site button is flat, so keep it minimal.
    sheen = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sheen).rounded_rectangle(
        [0, 0, w - 1, int(h * 0.5)], radius=radius, fill=(255, 255, 255, 14))
    sheen.putalpha(Image.composite(sheen.split()[3],
                                   Image.new("L", (w, h), 0), mask))
    pill.alpha_composite(sheen)
    return pill, ImageDraw.Draw(pill)


def _draw_arrow(d: ImageDraw.ImageDraw, x: float, cy: float,
                size: float, color) -> None:
    """Site-style '→' drawn with vectors (font-independent)."""
    shaft_y = cy
    head = size * 0.42
    d.line([(x, shaft_y), (x + size * 1.5, shaft_y)],
           fill=color, width=max(4, int(size * 0.14)))
    d.line([(x + size * 0.95, shaft_y - head),
            (x + size * 1.5, shaft_y),
            (x + size * 0.95, shaft_y + head)],
           fill=color, width=max(4, int(size * 0.14)), joint="curve")


def make_button(hover: bool = False) -> None:
    """CTA matching asta-energy.pl: flat action green, soft shadow, and on
    the hover variant the signature '→' revealed after the label."""
    w, h = 1160, 340
    canvas = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0))
    paste_shadow(canvas, (w + 80, h + 80), 90, offset=14,
                 opacity=110, blur=26, at=(0, 0))

    pill, d = _button_pill(hover)
    label = "WŁASNA PRODUKCJA PRĄDU"
    f = font("bold", 68)
    tw = d.textlength(label, font=f)
    em = 68.0
    arrow_w = em * 1.5 + em * 0.48 if hover else 0.0
    x0 = (w - (tw + arrow_w)) / 2
    ty = (h - 92) / 2 - 4
    d.text((x0, ty), label, font=f, fill=ACTION_TEXT)
    if hover:
        _draw_arrow(d, x0 + tw + em * 0.48, ty + 46,
                    em, ACTION_TEXT)

    canvas.alpha_composite(pill, (40, 40))
    name = "button-hover.png" if hover else "button.png"
    canvas.save(OUT / name)


def make_cursor() -> None:
    """Crisp pointer arrow: soft drop shadow, dark outline, white face.
    Tip sits near (20, 8) of the 160px canvas."""
    s = 160
    canvas = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    pts = [(20, 8), (20, 116), (54, 92), (74, 134), (96, 124),
           (78, 94), (116, 90)]

    # Soft contact shadow, offset down-right like a real cursor.
    shadow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    sp = [(x + 7, y + 9) for x, y in pts]
    ImageDraw.Draw(shadow).polygon(sp, fill=(10, 16, 10, 120))
    shadow = shadow.filter(ImageFilter.GaussianBlur(7))
    canvas.alpha_composite(shadow)

    draw = ImageDraw.Draw(canvas)
    # Dark outline pass (stroke centred on the path, inner half covered by
    # the white fill below), then the bright face.
    draw.line(pts + [pts[0]], fill=(12, 18, 12, 255), width=13,
              joint="curve")
    draw.polygon(pts, fill=(255, 255, 255, 255))
    canvas.save(OUT / "cursor.png")


def main() -> None:
    make_bill()
    make_button()
    make_button(hover=True)
    make_cursor()
    for name in ("bill.png", "button.png", "button-hover.png",
                 "cursor.png"):
        path = OUT / name
        with Image.open(path) as probe:
            print(f"{path.relative_to(ROOT)}  {probe.size}  {probe.mode}")


if __name__ == "__main__":
    main()
